from __future__ import annotations

import time
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from app.schemas import (
    SalesBrandOption,
    SalesFilterOption,
    SalesFilterOptions,
    SalesPeriod,
    SalesPeriodsResponse,
    VehicleSalesRankItem,
    VehicleSalesRanking,
)


RANK_DATA_URL = "https://www.dongchedi.com/motor/pc/car/rank_data"
PUBLIC_SALES_URL = "https://www.dongchedi.com/sales/sale-x-x-x-x-x-x"
MAX_RANKING_PAGES = 20

VEHICLE_TYPE_CODES = {
    "sedan": set(range(0, 6)),
    "suv": set(range(9, 15)),
    "mpv": set(range(20, 30)),
}

LEVEL_CODES = {
    "sedan": {
        "micro": 0,
        "small": 1,
        "compact": 2,
        "medium": 3,
        "medium-large": 4,
        "large": 5,
    },
    "suv": {
        "micro": 9,
        "small": 10,
        "compact": 11,
        "medium": 12,
        "medium-large": 13,
        "large": 14,
    },
}


class DongchediServiceError(RuntimeError):
    pass


class DongchediEmptyResultError(DongchediServiceError):
    pass


class DongchediUpstreamError(DongchediServiceError):
    pass


class DongchediService:
    def __init__(self, cache_ttl_seconds: int = 30 * 60) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[
            str,
            tuple[float, VehicleSalesRanking],
        ] = {}

    def clear_cache(self) -> None:
        self._cache.clear()

    @staticmethod
    def _params(year: int, month: int) -> dict[str, Any]:
        return {
            "aid": 1839,
            "app_name": "auto_web_pc",
            "city_name": "全国",
            "count": 100,
            "offset": 0,
            "month": f"{year:04d}{month:02d}",
            "new_energy_type": "",
            "rank_data_type": 11,
            "brand_id": "",
            "price": "",
            "manufacturer": "",
            "series_type": "",
            "nation": 0,
        }

    @staticmethod
    def _period_params() -> dict[str, Any]:
        params = DongchediService._params(2020, 1)
        params["count"] = 1
        params["month"] = ""
        return params

    def _fetch_json(self, params: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "accept": "application/json, text/plain, */*",
            "referer": PUBLIC_SALES_URL,
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/130 Safari/537.36"
            ),
        }
        with httpx.Client(
            timeout=15.0,
            follow_redirects=True,
            headers=headers,
        ) as client:
            response = client.get(RANK_DATA_URL, params=params)
            response.raise_for_status()
            return response.json()

    def _fetch_all_rows(
        self,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        page_params = dict(params)
        for _ in range(MAX_RANKING_PAGES):
            payload = self._fetch_json(page_params)
            if payload.get("status") != 0:
                raise DongchediUpstreamError(
                    "懂车帝公开销量数据返回异常"
                )
            page_rows = payload["data"]["list"]
            if not isinstance(page_rows, list):
                raise TypeError("ranking list is not an array")
            rows.extend(page_rows)

            paging = payload["data"].get("paging") or {}
            if not page_rows or not paging.get("has_more"):
                return rows

            current_offset = int(page_params.get("offset") or 0)
            next_offset = int(
                paging.get("offset", current_offset)
            ) + len(page_rows)
            if next_offset <= current_offset:
                raise DongchediUpstreamError(
                    "懂车帝公开销量分页返回异常"
                )
            page_params["offset"] = next_offset

        raise DongchediUpstreamError("懂车帝公开销量分页超出限制")

    @staticmethod
    def _normalize_item(item: dict[str, Any]) -> VehicleSalesRankItem:
        previous_rank = int(item.get("last_rank", -1))
        return VehicleSalesRankItem(
            rank=int(item["rank"]),
            series_id=int(item["series_id"]),
            series_name=str(item["series_name"]),
            brand_name=str(item.get("brand_name") or ""),
            manufacturer=str(item.get("sub_brand_name") or ""),
            sales=int(item["count"]),
            previous_rank=previous_rank if previous_rank > 0 else None,
            image=str(item.get("image") or ""),
            price=str(item.get("price") or ""),
        )

    def get_sales_ranking(
        self,
        *,
        year: int,
        month: int,
        vehicle_type: str = "all",
        level: str = "",
        energy_type: str = "",
        manufacturer: str = "",
        brand_id: Optional[int] = None,
    ) -> VehicleSalesRanking:
        period = f"{year:04d}-{month:02d}"
        cache_key = ":".join(
            [
                period,
                vehicle_type,
                level,
                energy_type,
                manufacturer,
                str(brand_id or ""),
            ]
        )
        cached = self._cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < self.cache_ttl_seconds:
            return cached[1]

        params = self._params(year, month)
        params["new_energy_type"] = (
            energy_type
            or ("1,2,3" if vehicle_type == "new-energy" else "")
        )
        params["manufacturer"] = manufacturer
        params["brand_id"] = brand_id or ""
        try:
            rows = self._fetch_all_rows(params)
            filtered_rows = self._filter_rows(
                rows,
                vehicle_type=vehicle_type,
                level=level,
            )
            items = []
            for rank, item in enumerate(filtered_rows, start=1):
                normalized = self._normalize_item(item)
                items.append(normalized.model_copy(update={"rank": rank}))
        except DongchediUpstreamError:
            raise
        except (
            httpx.HTTPError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise DongchediUpstreamError(
                "懂车帝公开销量数据暂不可用"
            ) from exc

        if not items:
            raise DongchediEmptyResultError("该月份暂无公开销量数据")

        source_query = urlencode(
            {
                "month": params["month"],
                "rank_data_type": params["rank_data_type"],
                "vehicle_type": vehicle_type,
                "level": level,
                "energy_type": energy_type,
                "manufacturer": manufacturer,
                "brand_id": brand_id or "",
            }
        )
        result = VehicleSalesRanking(
            year=year,
            month=month,
            period=period,
            source_name="懂车帝",
            source_url=f"{PUBLIC_SALES_URL}?{source_query}",
            source_note="数据源于行业综合销量，每月10号左右更新",
            filters={
                "vehicle_type": vehicle_type,
                "level": level,
                "energy_type": energy_type,
                "manufacturer": manufacturer,
                "brand_id": str(brand_id or ""),
            },
            items=items,
        )
        self._cache[cache_key] = (time.monotonic(), result)
        return result

    @staticmethod
    def _filter_rows(
        rows: list[dict[str, Any]],
        *,
        vehicle_type: str,
        level: str,
    ) -> list[dict[str, Any]]:
        codes = VEHICLE_TYPE_CODES.get(vehicle_type)
        level_code = LEVEL_CODES.get(vehicle_type, {}).get(level)
        result = []
        for row in rows:
            detail_type = int(row.get("outter_detail_type", -1))
            if codes is not None and detail_type not in codes:
                continue
            if level and detail_type != level_code:
                continue
            result.append(row)
        return result

    def get_filter_options(
        self,
        *,
        year: int,
        month: int,
    ) -> SalesFilterOptions:
        params = self._params(year, month)
        try:
            rows = self._fetch_all_rows(params)
            brands_by_id: dict[int, str] = {}
            for row in rows:
                brand_id = int(row["brand_id"])
                brand_name = str(row.get("brand_name") or "").strip()
                if brand_name:
                    brands_by_id[brand_id] = brand_name
        except (
            httpx.HTTPError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise DongchediUpstreamError(
                "懂车帝公开销量数据暂不可用"
            ) from exc

        return SalesFilterOptions(
            vehicle_types=[
                SalesFilterOption(value="all", label="全部"),
                SalesFilterOption(value="sedan", label="轿车"),
                SalesFilterOption(value="suv", label="SUV"),
                SalesFilterOption(value="mpv", label="MPV"),
                SalesFilterOption(value="new-energy", label="新能源"),
            ],
            energy_types=[
                SalesFilterOption(value="", label="全部能源"),
                SalesFilterOption(value="1", label="纯电"),
                SalesFilterOption(value="2", label="插混"),
                SalesFilterOption(value="3", label="增程"),
            ],
            manufacturers=[
                SalesFilterOption(value="", label="全部厂商"),
                SalesFilterOption(value="自主", label="自主"),
                SalesFilterOption(value="合资", label="合资"),
                SalesFilterOption(value="进口", label="进口"),
            ],
            brands=[
                SalesBrandOption(id=brand_id, name=name)
                for brand_id, name in sorted(
                    brands_by_id.items(),
                    key=lambda item: item[1],
                )
            ],
        )

    def get_available_periods(self) -> SalesPeriodsResponse:
        try:
            payload = self._fetch_json(self._period_params())
            raw_periods = payload["data"]["sells_rank_month"]
            periods: list[SalesPeriod] = []
            for item in raw_periods:
                value = int(item["month"])
                if value < 202001:
                    continue
                year, month = divmod(value, 100)
                if not 1 <= month <= 12:
                    continue
                periods.append(
                    SalesPeriod(
                        year=year,
                        month=month,
                        period=f"{year:04d}-{month:02d}",
                        label=str(item.get("text") or f"{year}年{month:02d}月"),
                    )
                )
        except (
            httpx.HTTPError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise DongchediUpstreamError(
                "懂车帝公开销量数据暂不可用"
            ) from exc

        if not periods:
            raise DongchediEmptyResultError("暂无可用的公开销量月份")
        return SalesPeriodsResponse(
            source_name="懂车帝",
            periods=periods,
        )


dongchedi_service = DongchediService()
