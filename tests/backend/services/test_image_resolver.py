from backend.services.image_resolver import (
    resolve_fighter_image,
    resolve_fighter_image_cropped,
)


def test_resolve_fighter_image_strips_loopback_origin() -> None:
    url = "http://localhost:8000/images/fighters/sample-id.jpg"
    assert (
        resolve_fighter_image("sample-id", url) == "images/fighters/sample-id.jpg"
    )


def test_resolve_fighter_image_preserves_external_urls() -> None:
    url = "https://cdn.example.com/assets/sample-id.jpg"
    assert resolve_fighter_image("sample-id", url) == url


def test_resolve_fighter_image_cropped_normalizes_loopback_origin() -> None:
    cropped_url = "http://127.0.0.1:8000/images/fighters/cropped/sample-id.jpg"
    assert (
        resolve_fighter_image_cropped("sample-id", None, cropped_url)
        == "images/fighters/cropped/sample-id.jpg"
    )
