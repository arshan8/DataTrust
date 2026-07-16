import re
import requests
from requests.auth import HTTPBasicAuth
from app.core.config import settings


def _auth():
    return HTTPBasicAuth(settings.CONFLUENCE_EMAIL, settings.CONFLUENCE_API_TOKEN)


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def list_pages(space_key: str = "BC", limit: int = 50) -> list[dict]:
    pages = []
    start = 0

    while True:
        url = f"{settings.CONFLUENCE_BASE_URL}/rest/api/content"
        res = requests.get(
            url,
            auth=_auth(),
            headers={"Accept": "application/json"},
            params={
                "spaceKey": space_key,
                "type": "page",
                "limit": limit,
                "start": start,
            },
            timeout=30,
        )
        res.raise_for_status()
        data = res.json()

        batch = data.get("results", [])
        pages.extend(batch)

        if len(batch) < limit:
            break

        start += limit

    return pages


def get_page_with_body(page_id: str) -> dict:
    url = f"{settings.CONFLUENCE_BASE_URL}/rest/api/content/{page_id}"
    res = requests.get(
        url,
        auth=_auth(),
        headers={"Accept": "application/json"},
        params={"expand": "body.storage,version,ancestors"},
        timeout=30,
    )
    res.raise_for_status()
    data = res.json()

    html = data.get("body", {}).get("storage", {}).get("value", "")
    text = _strip_html(html)

    return {
        "id": data["id"],
        "title": data["title"],
        "content_text": text,
        "resource_path": f"confluence://BC/page/{data['id']}/{data['title']}",
        "source_url": f"{settings.CONFLUENCE_BASE_URL}{data.get('_links', {}).get('webui', '')}",
        "version": data.get("version", {}).get("number"),
    }