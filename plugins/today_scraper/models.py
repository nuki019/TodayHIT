from datetime import datetime

from peewee import (
    AutoField,
    DateTimeField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)

db = SqliteDatabase(None)


class BaseModel(Model):
    class Meta:
        database = db


class Article(BaseModel):
    id = IntegerField(primary_key=True)
    title = TextField(null=False)
    url = TextField(null=False)
    source = TextField(default="todayhit")
    source_id = TextField(null=True)
    source_dept = TextField(null=True)
    category = TextField(null=True)
    published_at = DateTimeField(null=True)
    scraped_at = DateTimeField(default=datetime.now)
    summary = TextField(null=True)

    class Meta:
        table_name = "articles"
        # 索引在 init_db 中手动创建（需要先迁移旧数据）


class Subscription(BaseModel):
    id = AutoField()
    target_type = TextField(null=False)
    target_id = TextField(null=False)
    sub_type = TextField(null=False)
    sub_value = TextField(null=False)
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "subscriptions"
        indexes = ((("target_type", "target_id", "sub_type", "sub_value"), True),)


class PushRecord(BaseModel):
    id = AutoField()
    article_id = IntegerField(null=False)
    target_type = TextField(null=False)
    target_id = TextField(null=False)
    pushed_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "push_records"
        indexes = ((("article_id", "target_type", "target_id"), True),)


class GroupMessage(BaseModel):
    """群消息计数，用于「找群友」加权随机。"""
    id = AutoField()
    group_id = TextField(null=False)
    user_id = TextField(null=False)
    message_count = IntegerField(default=0)
    last_nickname = TextField(null=True)

    class Meta:
        table_name = "group_messages"
        indexes = ((("group_id", "user_id"), True),)

    @classmethod
    def increment(cls, group_id: str, user_id: str, nickname: str = "") -> None:
        """消息计数 +1，同时更新昵称缓存。"""
        cls.insert(
            group_id=group_id,
            user_id=user_id,
            message_count=1,
            last_nickname=nickname or None,
        ).on_conflict(
            conflict_target=[cls.group_id, cls.user_id],
            update={
                cls.message_count: cls.message_count + 1,
                cls.last_nickname: nickname or cls.last_nickname,
            },
        ).execute()


class ScraperState(BaseModel):
    key = TextField(primary_key=True)
    value = TextField(null=True)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "scraper_state"

    @classmethod
    def get_value(cls, key: str, default: str = "") -> str:
        try:
            return cls.get_by_id(key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key: str, value: str) -> None:
        cls.insert(key=key, value=value, updated_at=datetime.now()).on_conflict(
            conflict_target=[cls.key],
            update={cls.value: value, cls.updated_at: datetime.now()},
        ).execute()


def init_db(db_path: str) -> None:
    db.init(db_path)
    db.connect(reuse_if_open=True)
    db.create_tables([Article, Subscription, PushRecord, GroupMessage, ScraperState])
    # 迁移旧数据：为缺少 source/source_id 的表补充列和默认值
    _migrate_article_source()
    # 注册 REGEXP 函数供 SQLite 正则查询使用
    db.register_function(_regexp, "REGEXP")


def _migrate_article_source() -> None:
    """迁移：给 articles 表添加 source/source_id 列并填充默认值。"""
    cursor = db.execute_sql("PRAGMA table_info(articles)")
    columns = {row[1] for row in cursor.fetchall()}
    if "source" not in columns:
        db.execute_sql("ALTER TABLE articles ADD COLUMN source TEXT DEFAULT 'todayhit'")
    if "source_id" not in columns:
        db.execute_sql("ALTER TABLE articles ADD COLUMN source_id TEXT")
    db.execute_sql(
        "UPDATE articles SET source='todayhit', source_id=CAST(id AS TEXT) "
        "WHERE source IS NULL OR source_id IS NULL"
    )
    db.execute_sql(
        'CREATE UNIQUE INDEX IF NOT EXISTS "article_source_source_id" '
        'ON "articles" ("source", "source_id")'
    )


def _regexp(pattern: str, value: str) -> bool:
    """SQLite REGEXP 用户自定义函数。"""
    import re

    try:
        return bool(re.search(pattern, value or ""))
    except re.error:
        return False
