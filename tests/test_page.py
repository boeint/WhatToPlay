"""The web page itself: served, and never used from a stale browser cache after an update."""
import pytest


@pytest.mark.parametrize("path", ["/", "/app.js", "/panel.js", "/picker.js", "/styles.css", "/icon.png"])
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
