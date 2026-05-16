"""搜索引擎：精确优先、AND/OR/REGEX、时间过滤、转发节点构建。

纯逻辑模块，不依赖 nonebot，可独立测试。
"""
import operator
import re
from datetime import datetime
from functools import reduce
from typing import Any

from .models import Article
from .scraper import _source_label

MAX_RESULTS = 50

_TIME_RE = re.compile(
    r"时间\s+(\d{2})\.(\d{2})\.(\d{2})~(\d{2})\.(\d{2})\.(\d{2})"
)


def _format_time(dt: datetime | None) -> str:
    if not dt:
        return "未知"
    return dt.strftime("%Y-%m-%d %H:%M")


def parse_search_args(arg_text: str) -> tuple[str, tuple[datetime, datetime] | None]:
    """解析搜索参数，返回 (keyword_raw, time_range_or_None)。"""
    time_range = None
    m = _TIME_RE.search(arg_text)
    if m:
        y1, mo1, d1, y2, mo2, d2 = (int(x) for x in m.groups())
        start = datetime(2000 + y1, mo1, d1, 0, 0, 0)
        end = datetime(2000 + y2, mo2, d2, 23, 59, 59)
        time_range = (start, end)
        arg_text = arg_text[: m.start()] + arg_text[m.end() :]
    return arg_text.strip(), time_range


def build_query(
    keyword: str,
    time_range: tuple[datetime, datetime] | None,
    limit: int = MAX_RESULTS,
) -> list:
    """构建搜索查询，精确优先 + 高级语法。

    Returns:
        list[Article] 查询结果列表
    """
    if not keyword:
        query = (
            Article.select()
            .where(Article.published_at.is_null(False))
            .order_by(Article.published_at.desc())
            .limit(limit)
        )
        if time_range:
            start, end = time_range
            query = query.where(Article.published_at.between(start, end))
        return list(query)

    if keyword.startswith("正则:"):
        pattern = keyword[3:].strip()
        query = (
            Article.select()
            .where(Article.title.regexp(pattern))
            .order_by(Article.published_at.desc(nulls="LAST"), Article.id.desc())
            .limit(limit)
        )
    elif "/" in keyword and not keyword.startswith("正则:"):
        terms = [t.strip() for t in keyword.split("/") if t.strip()]
        if len(terms) == 1:
            cond = Article.title.contains(terms[0])
        else:
            cond = reduce(operator.or_, [Article.title.contains(t) for t in terms])
        query = (
            Article.select()
            .where(cond)
            .order_by(Article.published_at.desc(nulls="LAST"), Article.id.desc())
            .limit(limit)
        )
    else:
        terms = keyword.split()
        if len(terms) == 1:
            # 单关键词：精确匹配优先，不够再模糊补
            exact = list(
                Article.select()
                .where(Article.title == keyword)
                .order_by(Article.published_at.desc(nulls="LAST"), Article.id.desc())
                .limit(limit)
            )
            if len(exact) >= limit:
                return exact
            exact_ids = {a.id for a in exact}
            fuzzy = list(
                Article.select()
                .where(
                    Article.title.contains(keyword),
                    Article.id.not_in(exact_ids) if exact_ids else True,
                )
                .order_by(Article.published_at.desc(nulls="LAST"), Article.id.desc())
                .limit(limit - len(exact))
            )
            combined = exact + fuzzy
            if time_range:
                start, end = time_range
                combined = [
                    a for a in combined
                    if a.published_at and start <= a.published_at <= end
                ]
            return combined[:limit]
        else:
            cond = reduce(operator.and_, [Article.title.contains(t) for t in terms])
            query = (
                Article.select()
                .where(cond)
                .order_by(Article.published_at.desc(nulls="LAST"), Article.id.desc())
                .limit(limit)
            )

    if time_range:
        start, end = time_range
        query = query.where(Article.published_at.between(start, end))

    return list(query)


def build_forward_nodes(articles: list[Any], bot_id: int) -> list[dict]:
    """将文章列表构建为合并转发消息节点。"""
    nodes = []
    for a in articles:
        dept = a.source_dept or "未知"
        time_str = _format_time(a.published_at)
        source = _source_label(getattr(a, "source", None) or "todayhit")
        text = f"{a.title}\n时间: {time_str}\n部门: {dept}\n来源: {source}\n链接: {a.url}"
        nodes.append({
            "type": "node",
            "data": {
                "user_id": str(bot_id),
                "nickname": "缇安",
                "content": [{"type": "text", "data": {"text": text}}],
            },
        })
    return nodes
