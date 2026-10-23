from __future__ import annotations

import re
from urllib.parse import unquote, urlsplit

import tos
from tos.enum import HttpMethodType

from app.config import Settings, get_settings


PUBLIC_ENDPOINT = "tos-cn-beijing.volces.com"
PRIVATE_ENDPOINT = "tos-cn-beijing.ivolces.com"
REGION = "cn-beijing"
SIGNED_URL_EXPIRES = 3600
BUCKET_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")


class TosSigningError(RuntimeError):
    pass


class TosConfigurationError(TosSigningError):
    pass


class TosUrlError(TosSigningError):
    pass


def parse_tos_url(original_url: str) -> tuple[str, str]:
    value = original_url.strip()
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise TosUrlError("TOS 文件原始地址格式无效") from exc

    if (
        parsed.scheme.lower() != "https"
        or parsed.username
        or parsed.password
        or port is not None
    ):
        raise TosUrlError("请输入北京 Region 的 TOS 公网 HTTPS 地址")

    host = (parsed.hostname or "").lower()
    path = parsed.path.lstrip("/")
    if host == PUBLIC_ENDPOINT:
        parts = path.split("/", 1)
        if len(parts) != 2:
            raise TosUrlError("TOS 地址中缺少桶名或对象 Key")
        bucket, encoded_key = parts
    else:
        suffix = f".{PUBLIC_ENDPOINT}"
        if not host.endswith(suffix):
            raise TosUrlError("仅支持北京 Region 的 TOS 公网地址")
        bucket = host[: -len(suffix)]
        encoded_key = path

    object_key = unquote(encoded_key)
    if not BUCKET_PATTERN.fullmatch(bucket):
        raise TosUrlError("TOS 地址中的桶名无效")
    if not object_key or "\x00" in object_key:
        raise TosUrlError("TOS 地址中缺少有效的对象 Key")

    return bucket, object_key


class TosSigningService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_private_signed_url(self, original_url: str) -> str:
        bucket, object_key = parse_tos_url(original_url)
        if not self.settings.tos_configured:
            raise TosConfigurationError("TOS 访问凭证未配置")

        try:
            client = tos.TosClientV2(
                self.settings.tos_access_key,
                self.settings.tos_secret_key,
                endpoint=PRIVATE_ENDPOINT,
                region=REGION,
            )
            output = client.pre_signed_url(
                HttpMethodType.Http_Method_Get,
                bucket,
                object_key,
                expires=SIGNED_URL_EXPIRES,
            )
        except (tos.exceptions.TosClientError, tos.exceptions.TosServerError) as exc:
            raise TosSigningError("生成 TOS 私有签名失败") from exc

        return output.signed_url


tos_signing_service = TosSigningService(get_settings())
