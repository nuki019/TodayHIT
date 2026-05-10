import pytest
from plugins.today_scraper.models import db, Article, Subscription, PushRecord, ScraperState, init_db


@pytest.fixture(autouse=True)
def test_db():
    """每个测试使用内存数据库。"""
    init_db(":memory:")
    yield
    db.close()


def test_article_create_and_get():
    article = Article.create(
        id=129723,
        title="测试公告标题",
        url="https://today.hit.edu.cn/article/2026/05/10/129723",
        source_dept="能源学院",
        category="公告公示",
    )
    assert article.id == 129723
    assert article.title == "测试公告标题"
    got = Article.get_by_id(129723)
    assert got.url == "https://today.hit.edu.cn/article/2026/05/10/129723"


def test_article_idempotent_insert():
    Article.create(id=1, title="a", url="https://example.com/1")
    Article.insert(id=1, title="b", url="https://example.com/1b").on_conflict_ignore().execute()
    assert Article.select().count() == 1


def test_subscription_create_and_unique():
    Subscription.create(
        target_type="group", target_id="123456",
        sub_type="keyword", sub_value="招聘",
    )
    with pytest.raises(Exception):
        Subscription.create(
            target_type="group", target_id="123456",
            sub_type="keyword", sub_value="招聘",
        )


def test_subscription_query_by_target():
    Subscription.create(target_type="group", target_id="111", sub_type="category", sub_value="公告公示")
    Subscription.create(target_type="group", target_id="111", sub_type="keyword", sub_value="创新")
    Subscription.create(target_type="private", target_id="222", sub_type="keyword", sub_value="招聘")

    subs = list(Subscription.select().where(
        Subscription.target_type == "group",
        Subscription.target_id == "111",
    ))
    assert len(subs) == 2


def test_push_record_unique():
    Article.create(id=1, title="a", url="https://example.com/1")
    PushRecord.create(article_id=1, target_type="group", target_id="111")
    with pytest.raises(Exception):
        PushRecord.create(article_id=1, target_type="group", target_id="111")


def test_scraper_state_get_set():
    ScraperState.set("last_rss_id", "129700")
    assert ScraperState.get_value("last_rss_id") == "129700"
    assert ScraperState.get_value("nonexistent", "default") == "default"
