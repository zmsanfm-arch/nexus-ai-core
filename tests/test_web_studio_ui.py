from pathlib import Path

from starlette.routing import Mount

from app.main import app


def test_web_studio_is_mounted_and_static_bundle_is_packaged():
    mounts = [route for route in app.routes if isinstance(route, Mount)]
    studio = next(route for route in mounts if route.path == "/studio")
    assert studio.name == "web-studio"
    root = Path(__file__).resolve().parents[1] / "web_studio"
    assert (root / "index.html").is_file()
    assert (root / "studio.css").is_file()
    assert (root / "studio.js").is_file()
