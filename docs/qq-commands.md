# TodayHIT QQ 命令参考

所有查询结果以**合并转发消息卡片**输出，每条包含标题、时间、部门、链接，单次最多 50 条。

---

## 基础查询

### /today — 最新公告

```
输入: /today
```

输出（合并转发卡片，每条为一个节点）：
```
📌 关于2024年五一劳动节放假安排的通知
📅 2024-04-28 10:30
🏫 校长办公室
🔗 https://today.hit.edu.cn/article/2024/04/28/129800

📌 关于开展2024年度教职工体检工作的通知
📅 2024-04-27 14:00
🏫 校医院
🔗 https://today.hit.edu.cn/article/2024/04/27/129799
```

### /today --time yy.mm.dd~yy.mm.dd — 按时间筛选

```
输入: /today --time 24.04.01~24.04.30
```

输出 2024 年 4 月的所有公告（转发卡片）。

---

## 搜索

### /today search <关键词> — 精确优先搜索

```
输入: /today search 奖学金
```

搜索策略：
1. 先精确匹配标题 == "奖学金"
2. 不够再模糊匹配标题包含 "奖学金"
3. 按时间降序，最多 50 条

### /today search <词1> <词2> — AND 搜索（空格分隔）

```
输入: /today search 机电 学院
```

标题必须同时包含"机电"和"学院"。

### /today search <词1>|<词2> — OR 搜索（竖线分隔）

```
输入: /today search 奖学金|评优
```

标题包含"奖学金"或"评优"之一。

### /today search re:<正则> — 正则搜索

```
输入: /today search re:2024年.*评选
```

使用正则表达式匹配标题。支持 Python re 语法。

### 搜索 + 时间过滤

```
输入: /today search 奖学金 --time 24.01.01~24.12.31
```

在 2024 年内搜索包含"奖学金"的公告。

```
输入: /today search 机电|电气 --time 24.03.01~24.06.01
```

2024 年 3-6 月内，标题含"机电"或"电气"的公告。

---

## 部门筛选

### /today dept — 查看部门列表

```
输入: /today dept
```

输出（纯文本）：
```
📋 部门列表（部分）
━━━━━━━━━━━━━━━
  机电工程学院 (1234)
  计算机学院 (987)
  能源学院 (756)
  ... 共 85 个部门
━━━━━━━━━━━━━━━
/today dept <部门名> 查看该部门公告
```

### /today dept <部门名> — 按部门筛选

```
输入: /today dept 机电学院
```

输出该部门最新公告（转发卡片）。

```
输入: /today dept 机电学院 --time 24.01.01~24.06.01
```

筛选特定时间段内该部门的公告。

---

## 订阅管理

### /today sub category <分类> — 订阅分类

```
输入: /today sub category 公告公示
```

输出：`已订阅分类: 公告公示`

可选分类：`公告公示`、`新闻快讯`

### /today sub keyword <关键词> — 订阅关键词

```
输入: /today sub keyword 招聘
```

输出：`已订阅关键词: 招聘`

当新公告标题包含"招聘"时自动推送。

### /today list — 查看我的订阅

```
输入: /today list
```

输出：
```
📋 我的订阅列表
━━━━━━━━━━━━━━━
  1. [分类] 公告公示
  2. [关键词] 招聘
  3. [关键词] 奖学金
━━━━━━━━━━━━━━━
/today unsub <序号> 取消订阅
```

### /today unsub <序号> — 取消订阅

```
输入: /today unsub 2
```

输出：`已取消订阅 #2: [关键词] 招聘`

---

## 工具命令

### /today stat — 数据库统计

```
输入: /today stat
```

输出：
```
📊 数据库统计
━━━━━━━━━━━━━━━
总文章数: 48551
有部门信息: 48200
有分类信息: 48500
有时间信息: 48551
━━━━━━━━━━━━━━━
```

### /today scrape — 手动爬取

```
输入: /today scrape
```

输出：
```
开始爬取最新文章...
爬取完成！数据库共 48561 条文章。
```

### /today help — 帮助信息

```
输入: /today help
```

输出完整命令列表。

---

## 语法速查表

| 语法 | 说明 | 示例 |
|------|------|------|
| `/today` | 最新公告 | |
| `/today search X` | 单关键词精确优先搜索 | `/today search 奖学金` |
| `/today search A B` | AND 搜索（空格） | `/today search 机电 学院` |
| `/today search A\|B` | OR 搜索（竖线） | `/today search 奖学金\|评优` |
| `/today search re:X` | 正则搜索 | `/today search re:2024年.*通知` |
| `--time yy.mm.dd~yy.mm.dd` | 时间范围过滤（可附加到任何查询） | `--time 24.01.01~24.12.31` |
| `/today dept` | 部门列表 | |
| `/today dept X` | 按部门筛选 | `/today dept 计算机学院` |
| `/today scrape` | 手动爬取 | |
| `/today stat` | 统计信息 | |
| `/today sub category X` | 订阅分类 | `/today sub category 公告公示` |
| `/today sub keyword X` | 订阅关键词 | `/today sub keyword 招聘` |
| `/today list` | 我的订阅 | |
| `/today unsub N` | 取消订阅 | `/today unsub 1` |
| `/today help` | 帮助 | |
