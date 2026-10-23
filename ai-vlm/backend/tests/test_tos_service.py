from types import SimpleNamespace

import pytest

from app.config import Settings
from app.services.tos_service import (
    TosSigningService,
    TosUrlError,
    parse_tos_url,
)


def test_parse_virtual_host_tos_url() -> None:
    bucket, object_key = parse_tos_url(
        "https://video-bucket.tos-cn-beijing.volces.com/videos/%E5%8F%98%E9%81%93.mp4"
    )

    assert bucket == "video-bucket"
    assert object_key == "videos/变道.mp4"


def test_parse_path_style_tos_url() -> None:
    bucket, object_key = parse_tos_url(
        "https://tos-cn-beijing.volces.com/video-bucket/path/to/object.mp4"
    )

    assert bucket == "video-bucket"
    assert object_key == "path/to/object.mp4"


@pytest.mark.parametrize(
    "url",
    [
        "http://video-bucket.tos-cn-beijing.volces.com/video.mp4",
        "https://video-bucket.tos-cn-shanghai.volces.com/video.mp4",
        "https://video-bucket.tos-cn-beijing.volces.com/",
        "https://example.com/video.mp4",
    ],
)
def test_parse_tos_url_rejects_unsupported_address(url: str) -> None:
    with pytest.raises(TosUrlError):
        parse_tos_url(url)


def test_generate_private_signed_url_uses_private_endpoint(monkeypatch) -> None:
    calls = {}

    class FakeClient:
        def __init__(self, ak, sk, *, endpoint, region):
            calls["client"] = (ak, sk, endpoint, region)

        def pre_signed_url(self, method, bucket, key, *, expires):
            calls["sign"] = (method, bucket, key, expires)
            return SimpleNamespace(
                signed_url=(
                    "https://video-bucket.tos-cn-beijing.ivolces.com/"
                    "video.mp4?X-Tos-Signature=test"
                )
            )

    monkeypatch.setattr("app.services.tos_service.tos.TosClientV2", FakeClient)
    settings = Settings(
        _env_file=None,
        tos_access_key="test-ak",
        tos_secret_key="test-sk",
    )
    service = TosSigningService(settings)

    result = service.generate_private_signed_url(
        "https://video-bucket.tos-cn-beijing.volces.com/video.mp4"
    )

    assert calls["client"] == (
        "test-ak",
        "test-sk",
        "tos-cn-beijing.ivolces.com",
        "cn-beijing",
    )
    assert calls["sign"][1:] == ("video-bucket", "video.mp4", 3600)
    assert "tos-cn-beijing.ivolces.com" in result
