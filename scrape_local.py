"""本地爬取脚本：爬取各数据源并保存到 JSON 文件。

用法: python scrape_local.py
"""
import asyncio
import json
import sys
from datetime import datetime

# 添加项目路径
sys.path.insert(0, ".")

from plugins.today_scraper.scraper import (
    scrape_hit_main,
    scrape_hit_institutional,
    scrape_hitcs,
    scrape_hoa_blog,
)


def dt_to_str(dt):
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M")


async def main():
    results = {}

    print("=" * 50)
    print("开始爬取各数据源...")
    print("=" * 50)

    # 1. hit.edu.cn 主站新闻
    print("\n[1/4] 爬取 hit.edu.cn 工大要闻...")
    try:
        items = await scrape_hit_main()
        results["hit_main"] = items
        print(f"  获取 {len(items)} 条工大要闻")
        for item in items[:3]:
            print(f"    - {item['title'][:50]}")
            print(f"      {item['url']}")
    except Exception as e:
        print(f"  失败: {e}")
        results["hit_main"] = []

    # 2. hit.edu.cn 教学与科研机构
    print("\n[2/4] 爬取 hit.edu.cn 教学与科研机构...")
    try:
        items = await scrape_hit_institutional()
        results["hit_inst"] = items
        print(f"  获取 {len(items)} 个机构")
        for item in items[:5]:
            print(f"    - {item['title']}")
        if len(items) > 5:
            print(f"    ... 共 {len(items)} 个")
    except Exception as e:
        print(f"  失败: {e}")
        results["hit_inst"] = []

    # 3. HITCS GitHub
    print("\n[3/4] 爬取 HITCS GitHub 提交...")
    try:
        items = await scrape_hitcs()
        results["hitcs"] = items
        print(f"  获取 {len(items)} 条提交")
        for item in items[:3]:
            print(f"    - {item['title'][:60]}")
    except Exception as e:
        print(f"  失败: {e}")
        results["hitcs"] = []

    # 4. hoa.moe 博客
    print("\n[4/4] 爬取 hoa.moe 博客...")
    try:
        items = await scrape_hoa_blog()
        results["hoa_blog"] = items
        print(f"  获取 {len(items)} 篇博客")
        for item in items[:3]:
            print(f"    - {item['title'][:50]}")
            print(f"      {item['url']}")
    except Exception as e:
        print(f"  失败: {e}")
        results["hoa_blog"] = []

    # 序列化 datetime
    for source, items in results.items():
        for item in items:
            item["published_at"] = dt_to_str(item.get("published_at"))

    # 保存到文件
    output_file = "scraped_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 汇总
    print("\n" + "=" * 50)
    print("爬取完成汇总:")
    print("=" * 50)
    total = 0
    for source, items in results.items():
        count = len(items)
        total += count
        print(f"  {source}: {count} 条")
    print(f"  总计: {total} 条")
    print(f"\n数据已保存到: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
