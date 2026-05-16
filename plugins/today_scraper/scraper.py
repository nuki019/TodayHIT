import hashlib
import re
from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}


def _url_hash(url: str) -> str:
    """URL 的 MD5 前 8 位十六进制，转为正整数用作 Article.id。"""
    return int(hashlib.md5(url.encode()).hexdigest()[:8], 16)


def _source_label(source: str) -> str:
    """来源代码 → 中文标签。"""
    return {
        "todayhit": "今日哈工大",
        "hit_main": "工大官网",
        "hit_inst": "工大机构",
        "hitcs": "课程资料",
        "hoa_blog": "HOA博客",
    }.get(source, source)


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


# ── 多源爬取 ─────────────────────────────────────────────


async def scrape_hit_main() -> list[dict[str, Any]]:
    """爬取 hit.edu.cn 主站首页「工大要闻」新闻。"""
    async with httpx.AsyncClient(
        headers=HEADERS, follow_redirects=True, timeout=20
    ) as client:
        resp = await client.get("https://www.hit.edu.cn/")
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "lxml")
    articles: list[dict[str, Any]] = []

    # 找「工大要闻」区域
    heading = soup.find(string=re.compile(r"工大要闻"))
    if not heading:
        return articles

    container = heading.find_parent()
    if not container:
        return articles
    # 向上找包含链接列表的容器
    for _ in range(5):
        container = container.find_parent()
        if not container:
            break
        links = container.find_all("a", href=True)
        if len(links) >= 3:
            break
    else:
        return articles

    for link in links:
        href = link.get("href", "")
        title = link.get_text(strip=True)
        if not title or len(title) < 4:
            continue
        # 只保留 news.hit.edu.cn 的链接
        if "news.hit.edu.cn" not in href and "/news/" not in href:
            continue
        url = href if href.startswith("http") else "https://www.hit.edu.cn" + href

        # 从 URL 提取日期：/2026/0515/...
        pub_date = None
        date_match = re.search(r"/(\d{4})/(\d{4})/", href)
        if date_match:
            year = int(date_match.group(1))
            month = int(date_match.group(2)[:2])
            day = int(date_match.group(2)[2:])
            try:
                pub_date = datetime(year, month, day)
            except ValueError:
                pass

        articles.append({
            "id": _url_hash(url),
            "title": title,
            "url": url,
            "source": "hit_main",
            "source_id": hashlib.md5(url.encode()).hexdigest()[:16],
            "source_dept": None,
            "category": "工大要闻",
            "published_at": pub_date,
        })

    return articles


async def scrape_hit_institutional() -> list[dict[str, Any]]:
    """爬取 hit.edu.cn/11589/list.htm 教学与科研机构列表。"""
    async with httpx.AsyncClient(
        headers=HEADERS, follow_redirects=True, timeout=20
    ) as client:
        resp = await client.get("https://www.hit.edu.cn/11589/list.htm")
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "lxml")
    articles: list[dict[str, Any]] = []

    # 找页面主体区域的机构链接
    # 学院名称通常在链接中，包含"学院"或"学部"
    keywords = {"学院", "学部", "体育部", "空天学院"}
    for link in soup.find_all("a", href=True):
        name = link.get_text(strip=True)
        if not name:
            continue
        if any(kw in name for kw in keywords):
            href = link.get("href", "")
            url = href if href.startswith("http") else "https://www.hit.edu.cn" + href
            articles.append({
                "id": _url_hash(url),
                "title": name,
                "url": url,
                "source": "hit_inst",
                "source_id": hashlib.md5(url.encode()).hexdigest()[:16],
                "source_dept": name,
                "category": "教学与科研机构",
                "published_at": None,
            })

    return articles


async def scrape_hitcs() -> list[dict[str, Any]]:
    """爬取 HITCS GitHub 仓库最新提交。"""
    api_url = "https://api.github.com/repos/HITLittleZheng/HITCS/commits"
    async with httpx.AsyncClient(
        headers={**HEADERS, "Accept": "application/vnd.github.v3+json"},
        follow_redirects=True,
        timeout=20,
    ) as client:
        resp = await client.get(api_url, params={"per_page": 15})
        resp.raise_for_status()
        commits = resp.json()

    articles: list[dict[str, Any]] = []
    for commit in commits:
        sha = commit["sha"]
        message = commit["commit"]["message"].split("\n")[0].strip()
        if not message:
            continue
        url = commit["html_url"]
        date_str = commit["commit"]["committer"]["date"]
        try:
            pub_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, KeyError):
            pub_date = None

        # 提取文件路径作为部门信息
        file_path = ""
        if commit.get("files"):
            file_path = commit["files"][0].get("filename", "")

        articles.append({
            "id": _url_hash(url),
            "title": f"[HITCS] {message}",
            "url": url,
            "source": "hitcs",
            "source_id": sha[:16],
            "source_dept": file_path or None,
            "category": "课程资料",
            "published_at": pub_date,
        })

    return articles


_HOA_DATE_RE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")


async def scrape_hoa_blog() -> list[dict[str, Any]]:
    """爬取 hoa.moe 博客文章列表（HTML 解析）。"""
    async with httpx.AsyncClient(
        headers=HEADERS, follow_redirects=True, timeout=20
    ) as client:
        resp = await client.get("https://hoa.moe/blog")
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "lxml")
    articles: list[dict[str, Any]] = []

    # hoa.moe 是 Next.js 站点，博客列表用 <a href="/blog/xxx"> 结构
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if not href.startswith("/blog/") or href == "/blog":
            continue

        # 提取子元素：<p> 标题, <p> 摘要, <p> 日期
        paragraphs = link.find_all("p")
        if len(paragraphs) < 2:
            continue

        title = paragraphs[0].get_text(strip=True)
        # 日期通常在最后一个 <p>
        date_text = paragraphs[-1].get_text(strip=True)

        pub_date = None
        date_m = _HOA_DATE_RE.search(date_text)
        if date_m:
            try:
                pub_date = datetime(
                    int(date_m.group(1)), int(date_m.group(2)), int(date_m.group(3))
                )
            except ValueError:
                pass

        if not title or len(title) < 2:
            continue

        url = "https://hoa.moe" + href
        url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
        articles.append({
            "id": _url_hash(url),
            "title": title,
            "url": url,
            "source": "hoa_blog",
            "source_id": url_hash,
            "source_dept": "HITSZ",
            "category": "学习经验",
            "published_at": pub_date,
        })

    return articles
