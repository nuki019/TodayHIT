"""测试搜索引擎：精确优先、AND/OR/REGEX、时间过滤、转发节点构建。"""
import pytest
from datetime import datetime
from plugins.today_scraper.models import db, Article, init_db
from plugins.today_scraper.search import parse_search_args, build_query, build_forward_nodes


@pytest.fixture(autouse=True)
def test_db():
    init_db(":memory:")
    for i, (title, dept, dt) in enumerate([
        ("机电学院2024年度奖学金评选通知", "机电工程学院", datetime(2024, 3, 15, 10, 0)),
        ("机电学院研究生招生简章", "机电工程学院", datetime(2024, 6, 1, 8, 0)),
        ("计算机学院2024年度奖学金评选通知", "计算机学院", datetime(2024, 3, 20, 9, 0)),
        ("关于评选优秀研究生的通知", "研究生院", datetime(2024, 5, 10, 14, 0)),
        ("2024年奖学金评审结果公示", "学生工作部", datetime(2024, 7, 1, 16, 0)),
        ("能源学院实验室安全培训", "能源学院", datetime(2024, 4, 5, 10, 0)),
        ("电气学院创新大赛报名通知", "电气学院", datetime(2023, 11, 20, 9, 0)),
        ("图书馆数据库使用培训", "图书馆", datetime(2024, 9, 1, 8, 0)),
        ("2023年度教职工体检通知", "校医院", datetime(2023, 10, 15, 10, 0)),
        ("数学学院学术报告", "数学学院", datetime(2024, 8, 20, 14, 0)),
    ], start=1):
        Article.create(
            id=i, title=title, url=f"https://today.hit.edu.cn/article/2024/01/01/{i}",
            source_dept=dept, published_at=dt,
        )
    yield
    db.close()


# ── parse_search_args 测试 ────────────────────────────

def test_parse_search_args_no_time():
    keyword, tr = parse_search_args("机电学院")
    assert keyword == "机电学院"
    assert tr is None


def test_parse_search_args_with_time():
    keyword, tr = parse_search_args("奖学金 时间 24.01.01~24.12.31")
    assert keyword == "奖学金"
    assert tr is not None
    start, end = tr
    assert start == datetime(2024, 1, 1, 0, 0, 0)
    assert end == datetime(2024, 12, 31, 23, 59, 59)


def test_parse_search_args_time_only():
    keyword, tr = parse_search_args("时间 23.10.01~24.06.30")
    assert keyword == ""
    assert tr is not None


# ── build_query 测试 ──────────────────────────────────

def test_build_query_no_keyword():
    results = build_query("", None)
    assert len(results) > 0
    for i in range(len(results) - 1):
        a1, a2 = results[i], results[i + 1]
        if a1.published_at and a2.published_at:
            assert a1.published_at >= a2.published_at


def test_build_query_exact_first():
    results = build_query("机电学院2024年度奖学金评选通知", None)
    assert len(results) >= 1
    assert results[0].title == "机电学院2024年度奖学金评选通知"


def test_build_query_single_keyword_fuzzy():
    results = build_query("奖学金", None)
    titles = [r.title for r in results]
    assert len(titles) >= 3
    assert all("奖学金" in t for t in titles)


def test_build_query_and_mode():
    results = build_query("机电 评选", None)
    assert len(results) >= 1
    for r in results:
        assert "机电" in r.title and "评选" in r.title


def test_build_query_or_mode():
    """竖线 / 分隔 = OR 模式。"""
    results = build_query("图书馆/数学", None)
    titles = [r.title for r in results]
    assert any("图书馆" in t for t in titles)
    assert any("数学" in t for t in titles)


def test_build_query_regex():
    """正则: 前缀 = 正则模式。"""
    results = build_query("正则:2024年.*评选", None)
    titles = [r.title for r in results]
    assert all("2024年" in t and "评选" in t for t in titles)


def test_build_query_time_filter():
    start = datetime(2024, 3, 1, 0, 0, 0)
    end = datetime(2024, 6, 30, 23, 59, 59)
    results = build_query("", (start, end))
    for r in results:
        assert r.published_at is not None
        assert start <= r.published_at <= end


def test_build_query_keyword_and_time():
    start = datetime(2024, 1, 1, 0, 0, 0)
    end = datetime(2024, 4, 30, 23, 59, 59)
    results = build_query("奖学金", (start, end))
    for r in results:
        assert "奖学金" in r.title
        assert r.published_at is not None
        assert start <= r.published_at <= end


def test_build_query_no_results():
    results = build_query("不存在的关键词XYZ", None)
    assert results == []


# ── build_forward_nodes 测试 ──────────────────────────

def test_build_forward_nodes():
    articles = list(Article.select().limit(3))
    nodes = build_forward_nodes(articles, bot_id=999)
    assert len(nodes) == 3
    for node in nodes:
        assert node["type"] == "node"
        assert node["data"]["user_id"] == "999"
        assert node["data"]["nickname"] == "缇安"
        content = node["data"]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        text = content[0]["data"]["text"]
        assert "📌" in text
        assert "📅" in text
        assert "🏫" in text
        assert "🔗" in text


def test_build_forward_nodes_empty():
    nodes = build_forward_nodes([], bot_id=999)
    assert nodes == []


def test_build_forward_nodes_max_50():
    results = build_query("", None)
    assert len(results) <= 50
    nodes = build_forward_nodes(results, bot_id=999)
    assert len(nodes) <= 50
