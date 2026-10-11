"""The web page itself: served, and never used from a stale browser cache after an update."""
import pytest


@pytest.mark.parametrize("path", ["/", "/app.js", "/panel.js", "/picker.js", "/stats.js", "/styles.css", "/icon.png"])
def test_page_files_are_served_and_revalidated(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache"


def test_unchanged_files_cost_only_a_not_modified(client):
    first = client.get("/app.js")
    again = client.get("/app.js", headers={"If-None-Match": first.headers["etag"]})
    assert again.status_code == 304


def test_api_answers_are_left_alone(client):
    assert "cache-control" not in client.get("/api/platforms").headers


def test_installable_on_a_phone(client):
    """The manifest (name, full-screen, icons) is linked from the page and every icon it names exists."""
    page = client.get("/").text
    assert '<link rel="manifest" href="manifest.webmanifest">' in page
    response = client.get("/manifest.webmanifest")
    assert response.headers["content-type"].startswith("application/manifest+json")
    manifest = response.json()
    assert manifest["display"] == "standalone" and manifest["start_url"] == "/"
    sizes = {icon["sizes"] for icon in manifest["icons"]}
    assert {"192x192", "512x512"} <= sizes
    for icon in manifest["icons"] + [{"src": "apple-touch-icon.png"}]:
        assert client.get("/" + icon["src"]).headers["content-type"] == "image/png"
