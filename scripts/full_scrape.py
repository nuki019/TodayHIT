"""全量爬取今日哈工大历史数据。"""
import asyncio
import re
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from bs4 import BeautifulSoup
from plugins.today_scraper.models import init_db, Article, ScraperState

BASE_URL = "https://today.hit.edu.cn"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}
# 分类 ID -> 分类名
CATEGORIES = {10: "公告公示", 11: "新闻快讯"}


def parse_list_page(html: str, category: str) -> list[dict]:
    """解析分类列表页。"""
    soup = BeautifulSoup(html, "lxml")
    articles = []
    for item in soup.select("ul.paragraph li"):
        link = item.select_one('a[href*="/article/"]')
        if not link:
            continue
        href = link.get("href", "")
        match = re.search(r"/article/(\d{4})/(\d{2})/(\d{2})/(\d+)", href)
        if not match:
            continue
        article_id = int(match.group(4))
        try:
            published_at = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            published_at = None
        title = link.get_text(strip=True)
        url = BASE_URL + href if href.startswith("/") else href

        # 提取部门：li 的直接文本中，通常第一个文本节点是部门
        dept = None
        text_parts = list(item.stripped_strings)
        if text_parts:
            first = text_parts[0]
            # 部门名通常较短且不含"/article"
            if len(first) < 20 and "/article/" not in first:
                dept = first

        articles.append({
            "id": article_id,
            "title": title,
            "url": url,
            "source_dept": dept,
            "category": category,
            "published_at": published_at,
        })
    return articles


def get_max_page(html: str) -> int:
    """获取分页最大页码。"""
    soup = BeautifulSoup(html, "lxml")
    pages = soup.select(".pager__item a")
    max_page = 0
    for p in pages:
        href = p.get("href", "")
        m = re.search(r"page=(\d+)", href)
        if m:
            max_page = max(max_page, int(m.group(1)))
    return max_page


async def scrape_category(client: httpx.AsyncClient, cat_id: int, cat_name: str) -> int:
    """爬取单个分类的所有页面。"""
    # 第一页
    url = f"{BASE_URL}/category/{cat_id}"
    resp = await client.get(url)
    resp.raise_for_status()
    html = resp.text

    max_page = get_max_page(html)
    print(f"  [{cat_name}] 共 {max_page + 1} 页")

    total_new = 0
    # 爬取每一页
    for page in range(max_page + 1):
        if page > 0:
            await asyncio.sleep(2)
            resp = await client.get(f"{url}?page={page}")
            resp.raise_for_status()
            html = resp.text

        articles = parse_list_page(html, cat_name)
        new_count = 0
        for a in articles:
            try:
                Article.insert(
                    id=a["id"],
                    title=a["title"],
                    url=a["url"],
                    source_dept=a.get("source_dept"),
                    category=a["category"],
                    published_at=a.get("published_at"),
                ).on_conflict(
                    conflict_target=[Article.id],
                    update={
                        Article.source_dept: a.get("source_dept") or Article.source_dept,
                        Article.category: a["category"],
                        Article.published_at: a.get("published_at") or Article.published_at,
                    },
                ).execute()
                new_count += 1
            except Exception:
                pass

        total_new += new_count
        if page % 10 == 0:
            print(f"    page {page}: +{new_count} (累计 {total_new})")

    return total_new


async def main():
    init_db("./data/todayhit.db")
    before = Article.select().count()
    print(f"数据库已有 {before} 条记录")

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30) as client:
        for cat_id, cat_name in CATEGORIES.items():
            print(f"\n开始爬取 [{cat_name}] ...")
            count = await scrape_category(client, cat_id, cat_name)
            print(f"  [{cat_name}] 完成，新增/更新 {count} 条")

    after = Article.select().count()
    print(f"\n总计: {before} -> {after} 条记录")

    # 显示统计
    for cat in ["公告公示", "新闻快讯"]:
        cnt = Article.select().where(Article.category == cat).count()
        print(f"  {cat}: {cnt} 条")
    no_cat = Article.select().where(Article.category.is_null()).count()
    print(f"  无分类: {no_cat} 条")


if __name__ == "__main__":
    asyncio.run(main())
