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
        "dept": "部门站点",
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


# ── SUDY WP 通用爬虫（哈工大各子站点） ──────────────────

# 文章 URL 模式：/YYYY/MMDD/c{col}a{id}/page.htm
_SUDY_ARTICLE_RE = re.compile(r"/(\d{4})/(\d{4})/c(\d+)a(\d+)/page\.htm")

# 各站点配置：(base_url, display_name)
SUDY_SITES: list[tuple[str, str]] = [
    # 职能部处
    ("http://office.hit.edu.cn", "学校办公室"),
    ("http://zzb.hit.edu.cn", "党委组织部"),
    ("http://tzb.hit.edu.cn", "党委统战部"),
    ("http://qingfeng.hit.edu.cn", "纪委办公室"),
    ("http://xg.hit.edu.cn", "学生工作处"),
    ("http://bwc.hit.edu.cn", "保卫部"),
    ("http://gh.hit.edu.cn", "工会"),
    ("http://bmc.hit.edu.cn", "保密部"),
    ("http://hituc.hit.edu.cn", "本科生院"),
    ("http://zsjyc.hit.edu.cn", "终身教育处"),
    ("https://zsb.hit.edu.cn", "招生办"),
    ("http://hitgs.hit.edu.cn", "研究生院"),
    ("http://keyan.hit.edu.cn", "科研院"),
    ("https://xgb.hit.edu.cn", "学工处"),
    ("http://rsc.hit.edu.cn", "人事处"),
    ("http://international.hit.edu.cn", "国际合作部"),
    ("http://cwc.hit.edu.cn", "财务处"),
    ("http://sj.hit.edu.cn", "审计处"),
    ("https://gs.hit.edu.cn", "国资处"),
    ("http://hqjt.hit.edu.cn", "后勤"),
    ("http://cco.hit.edu.cn", "基建处"),
    ("http://ltxc.hit.edu.cn", "离退休处"),
    ("http://ca.hit.edu.cn", "网络信息办"),
    ("http://gnc.hit.edu.cn", "国内合作处"),
    # 直属单位
    ("http://lib.hit.edu.cn", "图书馆"),
    ("http://dag.hit.edu.cn", "档案馆"),
    ("http://alumni.hit.edu.cn", "校友办"),
    ("http://hitef.hit.edu.cn", "基金会"),
    ("http://jc.hit.edu.cn", "期刊中心"),
    ("http://sce.hit.edu.cn", "继续教育"),
    ("http://ees.hit.edu.cn", "未来工学院"),
    ("http://cie.hit.edu.cn", "国际教育"),
    ("http://sesri.hit.edu.cn", "空间研究院"),
    ("http://hitcam.hit.edu.cn", "分析测试"),
    ("http://hityy.hit.edu.cn", "校医院"),
    ("http://aim.hit.edu.cn", "资产公司"),
    ("http://hitpress.hit.edu.cn", "出版社"),
    ("http://xyy.hit.edu.cn", "先研院"),
    # 教学学院
    ("http://sa.hit.edu.cn", "航天学院"),
    ("http://seie.hit.edu.cn", "电信学院"),
    ("http://sme.hit.edu.cn", "机电学院"),
    ("http://mse.hit.edu.cn", "材料学院"),
    ("http://power.hit.edu.cn", "能源学院"),
    ("http://hitee.hit.edu.cn", "电气学院"),
    ("http://ise.hit.edu.cn", "仪器学院"),
    ("http://math.hit.edu.cn", "数学学院"),
    ("http://physics.hit.edu.cn", "物理学院"),
    ("http://som.hit.edu.cn", "经管学院"),
    ("http://hbs.hit.edu.cn", "商学院"),
    ("http://rwskxb.hit.edu.cn", "人文社科"),
    ("http://marx.hit.edu.cn", "马克思主义"),
    ("http://civil.hit.edu.cn", "土木学院"),
    ("http://env.hit.edu.cn", "环境学院"),
    ("http://arch.hit.edu.cn", "建筑学院"),
    ("http://jtxy.hit.edu.cn", "交通学院"),
    ("http://cs.hit.edu.cn", "计算学部"),
    ("http://sai.hit.edu.cn", "人工智能"),
    ("http://software.hit.edu.cn", "软件学院"),
    ("http://cys.hit.edu.cn", "网安学院"),
    ("http://chemeng.hit.edu.cn", "化工学院"),
    ("http://med.hit.edu.cn", "医学学院"),
    ("http://life.hit.edu.cn", "生命学院"),
    ("http://future.hit.edu.cn", "未来技术"),
    ("http://tyb.hit.edu.cn", "体育部"),
    ("http://sisd.hit.edu.cn", "深圳设计"),
    # 校属研究机构
    ("http://im.hit.edu.cn", "数学研究院"),
    ("http://bioinformatics.hit.edu.cn", "生物信息"),
    ("http://hcls.hit.edu.cn", "生命科学中心"),
    ("http://aero.hit.edu.cn", "航空研究院"),
    ("http://ai.hit.edu.cn", "人工智能研究院"),
    # 地方研究院
    ("http://cri.hit.edu.cn", "重庆研究院"),
    ("http://zri.hit.edu.cn", "郑州研究院"),
    ("http://sri.hit.edu.cn", "苏州研究院"),
    # 分校区
    ("http://www.hitwh.edu.cn", "哈工大威海"),
    ("http://www.hitsz.edu.cn", "哈工大深圳"),
]


async def scrape_sudy_site(base_url: str, dept_name: str) -> list[dict[str, Any]]:
    """爬取单个 SUDY WP 站点首页的文章链接。"""
    async with httpx.AsyncClient(
        headers=HEADERS, follow_redirects=True, timeout=12
    ) as client:
        resp = await client.get(base_url)
        if resp.status_code != 200:
            return []
        html = resp.text

    soup = BeautifulSoup(html, "lxml")
    articles: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        title = link.get_text(strip=True)
        if not title or len(title) < 5:
            continue

        m = _SUDY_ARTICLE_RE.search(href)
        if not m:
            continue

        url = href if href.startswith("http") else base_url.rstrip("/") + href
        if url in seen_urls:
            continue
        seen_urls.add(url)

        year, md = int(m.group(1)), m.group(2)
        try:
            pub_date = datetime(year, int(md[:2]), int(md[2:]))
        except ValueError:
            pub_date = None

        title = re.sub(r"^\d{4}[-/]\d{2}[-/]\d{2}\s*", "", title)

        articles.append({
            "id": _url_hash(url),
            "title": title,
            "url": url,
            "source": "dept",
            "source_id": hashlib.md5(url.encode()).hexdigest()[:16],
            "source_dept": dept_name,
            "category": "部门通知",
            "published_at": pub_date,
        })

    return articles


async def scrape_all_departments() -> list[dict[str, Any]]:
    """爬取所有 SUDY WP 子站点。"""
    all_articles: list[dict[str, Any]] = []
    for base_url, dept_name in SUDY_SITES:
        try:
            items = await scrape_sudy_site(base_url, dept_name)
            all_articles.extend(items)
        except Exception:
            pass
    return all_articles
