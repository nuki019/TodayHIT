import re
from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}


def parse_rss(xml_text: str) -> list[dict[str, Any]]:
    """解析 RSS XML，返回文章列表。"""
    soup = BeautifulSoup(xml_text, "lxml-xml")
    items: list[dict[str, Any]] = []
    for item in soup.find_all("item"):
        guid = item.guid.text.strip() if item.guid else ""
        match = re.search(r"(\d+)", guid)
        if not match:
            continue
        article_id = int(match.group(1))
        title = item.title.text.strip() if item.title else ""
        link = item.link.text.strip() if item.link else ""
        pub_date_str = item.pubDate.text.strip() if item.pubDate else ""
        try:
            pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z")
        except ValueError:
            pub_date = None
        items.append(
            {
                "id": article_id,
                "title": title,
                "url": link,
                "published_at": pub_date,
                "source_dept": None,
                "category": None,
            }
        )
    return items


def parse_category_page(html: str, base_url: str) -> list[dict[str, Any]]:
    """解析分类列表页，提取文章链接和部门信息。"""
    soup = BeautifulSoup(html, "lxml")
    articles: list[dict[str, Any]] = []
    for row in soup.select(".views-row"):
        link_tag = row.select_one('a[href*="/article/"]')
        if not link_tag:
            continue
        href = link_tag.get("href", "")
        match = re.search(r"/article/(\d{4})/(\d{2})/(\d{2})/(\d+)", href)
        if not match:
            continue
        article_id = int(match.group(4))
        try:
            published_at = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            published_at = None
        title = link_tag.get_text(strip=True)
        dept_tag = row.select_one(
            ".field--name-field-department, .views-field-field-department"
        )
        source_dept = dept_tag.get_text(strip=True) if dept_tag else None
        url = base_url + href if href.startswith("/") else href
        articles.append(
            {
                "id": article_id,
                "title": title,
                "url": url,
                "source_dept": source_dept,
                "category": None,
                "published_at": published_at,
            }
        )
    return articles


def parse_search_page(html: str, base_url: str) -> list[dict[str, Any]]:
    """解析搜索结果页，提取标题、链接和摘要。"""
    soup = BeautifulSoup(html, "lxml")
    results: list[dict[str, Any]] = []
    for item in soup.select(
        ".search-result, .search-results-item, li.search-result"
    ):
        link_tag = item.select_one("a[href]")
        if not link_tag:
            continue
        title = link_tag.get_text(strip=True)
        href = link_tag.get("href", "")
        url = base_url + href if href.startswith("/") else href
        snippet_tag = item.select_one(".search-snippet, p, .snippet")
        snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
        results.append({"title": title, "url": url, "summary": snippet})
    return results


async def fetch_rss(base_url: str) -> str:
    """异步拉取 RSS 源。"""
    async with httpx.AsyncClient(
        headers=HEADERS, follow_redirects=True, timeout=15
    ) as client:
        resp = await client.get(f"{base_url}/rss.xml")
        resp.raise_for_status()
        return resp.text


async def fetch_category_page(base_url: str, category_id: int, page: int = 0) -> str:
    """异步拉取分类列表页。"""
    url = f"{base_url}/category/{category_id}"
    if page > 0:
        url += f"?page={page}"
    async with httpx.AsyncClient(
        headers=HEADERS, follow_redirects=True, timeout=15
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


async def fetch_search_page(
    base_url: str, keyword: str, page: int = 0
) -> str:
    """异步拉取搜索结果页。"""
    url = f"{base_url}/search"
    params: dict[str, str] = {"keyword": keyword}
    if page > 0:
        params["page"] = str(page)
    async with httpx.AsyncClient(
        headers=HEADERS, follow_redirects=True, timeout=15
    ) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.text
