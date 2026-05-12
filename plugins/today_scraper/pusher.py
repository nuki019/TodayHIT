from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import Article, PushRecord, Subscription


def _format_time(dt: datetime | None) -> str:
    if not dt:
        return "未知"
    return dt.strftime("%Y-%m-%d %H:%M")


def match_subscriptions(article: Article) -> list[tuple[str, str]]:
    """匹配文章对应的订阅目标，返回 [(target_type, target_id), ...]。"""
    targets: set[tuple[str, str]] = set()

    # 分类订阅匹配
    if article.category:
        for sub in Subscription.select().where(
            Subscription.sub_type == "category",
            Subscription.sub_value == article.category,
        ):
            targets.add((sub.target_type, sub.target_id))

    # 关键词订阅匹配
    for sub in Subscription.select().where(Subscription.sub_type == "keyword"):
        if sub.sub_value in article.title:
            targets.add((sub.target_type, sub.target_id))

    return list(targets)


def get_unpushed_articles(limit: int = 10) -> list[Article]:
    """获取尚未推送过的文章。"""
    pushed_ids = set(
        r.article_id for r in PushRecord.select(PushRecord.article_id).distinct()
    )
    query = Article.select().order_by(Article.published_at.desc()).limit(limit)
    if pushed_ids:
        query = query.where(Article.id.not_in(pushed_ids))
    return list(query)


def mark_pushed(article_id: int, target_type: str, target_id: str) -> None:
    """记录已推送。"""
    PushRecord.insert(
        article_id=article_id,
        target_type=target_type,
        target_id=target_id,
    ).on_conflict_ignore().execute()


def build_push_nodes(articles: list[dict[str, Any]], bot_id: int) -> list[dict]:
    """构建推送转发消息节点列表。"""
    if not articles:
        return []

    nodes = []
    for a in articles:
        dept = a.get("source_dept") or "未知"
        time_str = _format_time(a.get("published_at"))
        text = f"📌 {a['title']}\n📅 {time_str}\n🏫 {dept}\n🔗 {a['url']}"
        nodes.append({
            "type": "node",
            "data": {
                "user_id": str(bot_id),
                "nickname": "缇安",
                "content": [{"type": "text", "data": {"text": text}}],
            },
        })
    return nodes


def build_search_message(
    keyword: str, results: list[dict[str, Any]], page: int, total: int
) -> str:
    """构建搜索结果消息文本。"""
    if not results:
        return f'🔍 搜索"{keyword}" - 无结果'

    lines = [f'🔍 搜索"{keyword}" - 第 {page + 1} 页（共 {total} 条）', "━" * 18]
    for i, r in enumerate(results, 1):
        dept = r.get("source_dept") or ""
        date_str = r.get("date") or ""
        meta = " · ".join(filter(None, [dept, date_str]))
        lines.append(f"{i}. {r['title']}")
        if meta:
            lines.append(f"   {meta}")
        lines.append(f"   {r['url']}")
        if i < len(results):
            lines.append("")
    lines.append("━" * 18)
    lines.append(f"/today search {keyword} {page + 2} → 下一页")
    return "\n".join(lines)
