"""端到端验证：连接真实网站测试爬虫。"""
import asyncio
from plugins.today_scraper.scraper import fetch_rss, parse_rss
from plugins.today_scraper.models import init_db, Article


async def test_rss():
    xml = await fetch_rss("https://today.hit.edu.cn")
    items = parse_rss(xml)
    print(f"RSS items: {len(items)}")
    for i in items[:3]:
        print(f"  - [{i['id']}] {i['title']}")
    return items


def test_db():
    init_db(":memory:")
    print(f"DB init OK, Articles: {Article.select().count()}")


if __name__ == "__main__":
    test_db()
    asyncio.run(test_rss())
    print("\nAll verification passed!")
