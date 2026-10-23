from __future__ import annotations

from datetime import date
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from app.config import Settings


class DriverRepositoryError(RuntimeError):
    pass


class DriverNotFoundError(DriverRepositoryError):
    pass


class DriverVinConflictError(DriverRepositoryError):
    pass


class DriverRepository:
    """Persist TSP driver records in the configured RDS instance."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _connect(self) -> pymysql.Connection:
        if not self.settings.rds_configured:
            raise DriverRepositoryError("RDS 配置不完整")
        if self.settings.rds_engine not in {"mysql", "mariadb"}:
            raise DriverRepositoryError("当前仅支持 MySQL 兼容的 RDS 实例")

        ssl_mode = self.settings.volcengine_rds_ssl_mode.strip().lower()
        ssl = (
            None
            if ssl_mode in {"", "disable", "disabled"}
            else {"check_hostname": False}
        )
        try:
            return pymysql.connect(
                host=self.settings.volcengine_rds_host,
                port=int(self.settings.volcengine_rds_port),
                user=self.settings.volcengine_rds_username,
                password=self.settings.volcengine_rds_password,
                database=self.settings.volcengine_rds_database,
                charset="utf8mb4",
                cursorclass=DictCursor,
                connect_timeout=self.settings.volcengine_rds_connect_timeout,
                read_timeout=10,
                write_timeout=10,
                ssl=ssl,
            )
        except (ValueError, pymysql.MySQLError) as exc:
            raise DriverRepositoryError("无法连接车主数据 RDS 数据库") from exc

    def list_drivers(
        self,
        *,
        page: int,
        page_size: int,
        keyword: str,
    ) -> tuple[list[dict[str, Any]], int]:
        connection = self._connect()
        try:
            offset = (page - 1) * page_size
            where_sql = ""
            params: tuple[Any, ...] = ()
            if keyword:
                where_sql = """
                    WHERE `name` LIKE %s
                       OR `phone` LIKE %s
                       OR `vin` LIKE %s
                       OR `vehicle_model` LIKE %s
                       OR `registration_city` LIKE %s
                """
                pattern = f"%{keyword}%"
                params = (pattern, pattern, pattern, pattern, pattern)

            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT COUNT(*) AS total FROM `tsp_drivers` {where_sql}",
                    params,
                )
                total = int(cursor.fetchone()["total"])
                cursor.execute(
                    f"""
                        SELECT
                            `id`,
                            `name`,
                            `phone`,
                            `vin`,
                            `vehicle_model`,
                            `address`,
                            `registration_city`,
                            `registration_date`,
                            `create_time`,
                            `update_time`
                        FROM `tsp_drivers`
                        {where_sql}
                        ORDER BY `id` DESC
                        LIMIT %s OFFSET %s
                    """,
                    (*params, page_size, offset),
                )
                rows = list(cursor.fetchall())
        except pymysql.MySQLError as exc:
            raise DriverRepositoryError("读取车主数据失败") from exc
        finally:
            connection.close()
        return rows, total

    def list_driver_options(
        self,
        *,
        keyword: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            where_sql = ""
            params: tuple[Any, ...] = ()
            if keyword:
                where_sql = "WHERE `name` LIKE %s OR `vin` LIKE %s"
                pattern = f"%{keyword}%"
                params = (pattern, pattern)

            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                        SELECT `id`, `name`, `vin`, `vehicle_model`
                        FROM `tsp_drivers`
                        {where_sql}
                        ORDER BY `id` DESC
                        LIMIT %s
                    """,
                    (*params, limit),
                )
                rows = list(cursor.fetchall())
        except pymysql.MySQLError as exc:
            raise DriverRepositoryError("读取车主选项失败") from exc
        finally:
            connection.close()
        return rows

    def create_driver(
        self,
        *,
        name: str,
        phone: str,
        vin: str,
        vehicle_model: str,
        address: str,
        registration_city: str,
        registration_date: date,
    ) -> int:
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                        INSERT INTO `tsp_drivers` (
                            `name`,
                            `phone`,
                            `vin`,
                            `vehicle_model`,
                            `address`,
                            `registration_city`,
                            `registration_date`
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        name,
                        phone,
                        vin,
                        vehicle_model,
                        address,
                        registration_city,
                        registration_date,
                    ),
                )
                driver_id = int(cursor.lastrowid)
            connection.commit()
        except pymysql.IntegrityError as exc:
            connection.rollback()
            if exc.args and exc.args[0] == 1062:
                raise DriverVinConflictError("VIN 码已存在") from exc
            raise DriverRepositoryError("创建车主失败") from exc
        except pymysql.MySQLError as exc:
            connection.rollback()
            raise DriverRepositoryError("创建车主失败") from exc
        finally:
            connection.close()
        return driver_id

    def update_driver(
        self,
        driver_id: int,
        *,
        name: str,
        phone: str,
        vin: str,
        vehicle_model: str,
        address: str,
        registration_city: str,
        registration_date: date,
    ) -> None:
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                        UPDATE `tsp_drivers`
                        SET
                            `name` = %s,
                            `phone` = %s,
                            `vin` = %s,
                            `vehicle_model` = %s,
                            `address` = %s,
                            `registration_city` = %s,
                            `registration_date` = %s
                        WHERE `id` = %s
                    """,
                    (
                        name,
                        phone,
                        vin,
                        vehicle_model,
                        address,
                        registration_city,
                        registration_date,
                        driver_id,
                    ),
                )
                if cursor.rowcount == 0:
                    cursor.execute(
                        "SELECT `id` FROM `tsp_drivers` WHERE `id` = %s",
                        (driver_id,),
                    )
                    if cursor.fetchone() is None:
                        raise DriverNotFoundError("车主不存在")
            connection.commit()
        except DriverNotFoundError:
            connection.rollback()
            raise
        except pymysql.IntegrityError as exc:
            connection.rollback()
            if exc.args and exc.args[0] == 1062:
                raise DriverVinConflictError("VIN 码已存在") from exc
            raise DriverRepositoryError("更新车主失败") from exc
        except pymysql.MySQLError as exc:
            connection.rollback()
            raise DriverRepositoryError("更新车主失败") from exc
        finally:
            connection.close()

    def delete_driver(self, driver_id: int) -> None:
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM `tsp_drivers` WHERE `id` = %s",
                    (driver_id,),
                )
                if cursor.rowcount == 0:
                    raise DriverNotFoundError("车主不存在")
            connection.commit()
        except DriverNotFoundError:
            connection.rollback()
            raise
        except pymysql.MySQLError as exc:
            connection.rollback()
            raise DriverRepositoryError("删除车主失败") from exc
        finally:
            connection.close()
