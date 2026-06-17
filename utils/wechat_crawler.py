"""
文章知识库导入工具

从公众号/新闻文章链接提取内容，转为 .txt 存入知识库。

提取引擎（自动降级）：
  1. requests + lxml（默认，适用于大多数网站）
  2. agent-browser（当 AGENT_BROWSER_EXECUTABLE_PATH 环境变量已设置，
     适用于 requests 被拦截或需要 JS 渲染的场景）

功能：
  url <link>       从文章链接提取内容并存入知识库
  search <query>   搜索文章并列出结果
  batch <file>     从文件读取多个URL批量导入

用法：
  python utils/wechat_crawler.py url <链接>
  python utils/wechat_crawler.py search "[公众号名称] 理论宣讲"
  python utils/wechat_crawler.py batch urls.txt

环境变量：
  AGENT_BROWSER_EXECUTABLE_PATH   指定 Chrome 路径以启用浏览器引擎
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests
from lxml import html as lxml_html

ROOT = Path(__file__).resolve().parent.parent
KB_ARCHIVE = ROOT / "knowledge-base" / "archive"
NOW = datetime.now()
CURRENT_YEAR = str(NOW.year)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/131.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
}

# agent-browser integration
AB_PATH = os.environ.get("AGENT_BROWSER_EXECUTABLE_PATH", "")
AB_AVAILABLE = bool(AB_PATH) and os.path.isfile(AB_PATH)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs, flush=True)


def _ab(*args, timeout=30):
    """Run agent-browser with the configured Chrome path."""
    env = os.environ.copy()
    env["AGENT_BROWSER_EXECUTABLE_PATH"] = AB_PATH
    try:
        r = subprocess.run(
            ["agent-browser", *args],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace", env=env
        )
        if r.returncode != 0 and r.stderr.strip():
            eprint(f"  [ab] {r.stderr.strip()[:100]}")
        return r.stdout
    except subprocess.TimeoutExpired:
        eprint("  [ab 超时]")
        return ""
    except FileNotFoundError:
        eprint("  [ab] agent-browser 未安装")
        return ""
    except Exception as e:
        eprint(f"  [ab] {e}")
        return ""


def fetch_via_browser(url):
    """Fetch page content via agent-browser browser engine."""
    eprint(f"  [浏览器引擎] {url[:70]}...")

    # Open URL (creates browser session automatically)
    out = _ab("open", url, timeout=25)
    if not out:
        eprint("  [浏览器引擎] 打开页面失败")
        return {"title": "", "account": "", "publishTime": "", "body": "", "url": url}

    time.sleep(3)

    js = r"""
    (() => {
        const title = (document.getElementById('activity-name') || document.querySelector('h1') || document.querySelector('title') || {}).textContent || '';
        const account = (document.getElementById('js_name') || document.querySelector('.rich_media_meta_nickname') || {}).textContent || '';
        const pubTime = (document.getElementById('publish_time') || {}).textContent || '';
        const c = document.getElementById('js_content') || document.querySelector('.rich_media_content') || document.querySelector('article') || document.body;
        let body = '';
        if (c) {
            const clone = c.cloneNode(true);
            clone.querySelectorAll('script,style,nav,footer,header,aside,iframe,svg,.related,.comment,.sidebar').forEach(e => e.remove());
            clone.querySelectorAll('br,p,div,section,li,h1,h2,h3,h4,h5,h6,tr').forEach(e => e.after('\n'));
            body = clone.textContent.replace(/\n{3,}/g,'\n\n').replace(/[ \t]+/g,' ').trim().slice(0,20000);
        }
        const pageTitle = document.title;
        return JSON.stringify({title: title || pageTitle, account, publishTime: pubTime, body, pageTitle});
    })()
    """
    raw = _ab("eval", js, timeout=10)
    data = {"title": "", "account": "", "publishTime": "", "body": "", "pageTitle": ""}
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                data = parsed
        except json.JSONDecodeError:
            pass

    data["url"] = url
    if not data.get("title"):
        data["title"] = data.get("pageTitle", "")

    eprint(f"  标题: {data.get('title', '')[:60]}")
    eprint(f"  来源: {data.get('account', '')}")
    eprint(f"  正文: {len(data.get('body', ''))} 字")
    return data


def fetch_html(url, timeout=15):
    """Fetch page HTML via requests."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        eprint(f"  HTTP {status}")
        if status == 403 and AB_AVAILABLE:
            eprint("  requests 被拦截，尝试浏览器引擎...")
            return None
        if status == 404:
            eprint("  页面不存在")
        return None
    except requests.exceptions.ConnectionError:
        eprint("  连接失败")
        return None
    except requests.exceptions.Timeout:
        eprint("  超时")
        return None
    except requests.exceptions.RequestException as e:
        eprint(f"  请求异常: {e}")
        return None


def extract_wechat_meta(html_text):
    """Extract metadata from WeChat article page embedded script."""
    data = {}
    # WeChat puts article info in a script with var ct = "..."
    m = re.search(r'var ct\s*=\s*"([^"]+)"', html_text)
    if m:
        data["publishTime"] = m.group(1)
    m = re.search(r'var nickname\s*=\s*"([^"]+)"', html_text)
    if m:
        data["account"] = m.group(1).replace("\\/", "/")
    m = re.search(r'var msg_title\s*=\s*"([^"]+)"', html_text)
    if m:
        data["title"] = m.group(1).replace("\\/", "/").replace("\\x3c", "<").replace("\\x3e", ">")
    m = re.search(r'var msg_cdn_url\s*=\s*"([^"]+)"', html_text)
    if m:
        data["coverUrl"] = m.group(1)
    # Try to get title from og:title meta as fallback
    if "title" not in data:
        m = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html_text)
        if m:
            data["title"] = m.group(1)
    return data


def extract_wechat_body(html_text):
    """Extract article body text from WeChat article HTML."""
    tree = lxml_html.fromstring(html_text)
    # Remove script, style, etc.
    for tag in tree.xpath("//script | //style | //svg"):
        p = tag.getparent()
        if p is not None:
            p.remove(tag)
    # Find the content div
    content = tree.xpath("//div[@id='js_content']")
    if not content:
        content = tree.xpath("//div[contains(@class, 'rich_media_content')]")
    if not content:
        return ""
    el = content[0]
    # Get all text with line breaks between block elements
    parts = []
    for node in el.iter():
        block_tags = ("br", "p", "div", "section", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr")
        if node.tag in block_tags:
            text = (node.text or "").strip()
            tail = (node.tail or "").strip()
            if text:
                parts.append(text)
            parts.append("\n")
            if tail:
                parts.append(tail)
        elif node.tag in ("span", "strong", "em", "a"):
            text = (node.text or "").strip()
            if text:
                parts.append(text)
    body = "".join(parts)
    body = re.sub(r'\n{3,}', '\n\n', body)
    body = re.sub(r'[ \t]{2,}', ' ', body)
    return body.strip()


def extract_generic_title(tree, html_text):
    """Extract title from generic article page."""
    selectors = [
        "//h1",
        "//article//h1",
        "//*[contains(@class, 'article-title')]",
        "//*[contains(@class, 'title')]//h1",
        "//*[contains(@class, 'title')]",
        "//*[contains(@class, 'post-title')]",
        "//*[@id='title']",
        "//*[@id='articleTitle']",
        "//title",
    ]
    for sel in selectors:
        nodes = tree.xpath(sel)
        if nodes:
            t = nodes[0].text_content().strip()
            if t and len(t) > 5:
                return t
    # Try meta tags
    m = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html_text)
    if m:
        return m.group(1)
    m = re.search(r'<title>([^<]+)</title>', html_text)
    if m:
        return m.group(1).replace("\n", " ").strip()
    return ""


def extract_generic_body(tree):
    """Extract body text from generic article page."""
    selectors = [
        "//article",
        "//*[contains(@class, 'article-content')]",
        "//*[contains(@class, 'post-content')]",
        "//*[contains(@class, 'content')]",
        "//*[@id='content']",
        "//*[@id='articleContent']",
        "//main",
        "//*[contains(@class, 'main')]",
    ]
    for sel in selectors:
        nodes = tree.xpath(sel)
        if nodes:
            # Try to find the largest content block
            candidates = []
            for i, n in enumerate(nodes):
                text = n.text_content().strip()
                if len(text) > 200:
                    candidates.append((len(text), i, n))
            if candidates:
                candidates.sort(reverse=True)
                el = candidates[0][2]
                # Remove unwanted elements
                remove_xpath = (".//script | .//style | .//nav | .//footer | .//header | .//aside "
                                "| .//*[contains(@class, 'sidebar')] | .//*[contains(@class, 'related')] "
                                "| .//*[contains(@class, 'comment')]")
                for tag in el.xpath(remove_xpath):
                    try:
                        tag.getparent().remove(tag)
                    except Exception:
                        pass
                # Extract text with block-level separators
                parts = []
                for node in el.iter():
                    tag = node.tag if isinstance(node.tag, str) else ""
                    block_tags = ("br", "p", "div", "section", "li", "h1", "h2",
                                  "h3", "h4", "h5", "h6", "tr", "td")
                    if tag in block_tags:
                        text = (node.text or "").strip()
                        if text:
                            parts.append(text)
                        parts.append("\n")
                    elif tag in ("span", "strong", "em", "a", "b", "i", "u"):
                        text = (node.text or "").strip()
                        if text:
                            parts.append(text)
                body = "".join(parts)
                body = re.sub(r'\n{3,}', '\n\n', body)
                body = re.sub(r'[ \t]{2,}', ' ', body)
                if len(body) > 100:
                    return body.strip()
    return ""


def is_wechat_url(url):
    return "mp.weixin.qq.com" in url


def extract_from_url(url):
    """Extract article content from a URL.

    Uses requests+lxml first, falls back to agent-browser when available.
    Returns dict with title, account, publishTime, body, url.
    """
    eprint(f"  获取: {url[:80]}...")
    html = fetch_html(url)

    # Fallback: requests failed (403) + browser available
    if html is None and AB_AVAILABLE:
        data = fetch_via_browser(url)
        data["error"] = ""
        eprint(f"  标题: {data.get('title', '')[:50]}")
        eprint(f"  来源: {data.get('account', '')}")
        eprint(f"  正文: {len(data.get('body', ''))} 字")
        return data

    if html is None:
        return {"title": "", "account": "", "publishTime": "", "body": "", "url": url,
                "error": "无法获取页面"}

    data = {"url": url, "error": ""}

    if "mp.weixin.qq.com" in url:
        data.update(extract_wechat_meta(html))
        data["body"] = extract_wechat_body(html)
        eprint(f"  标题: {data.get('title', '')[:50]}")
        eprint(f"  来源: {data.get('account', '')}")
        eprint(f"  正文: {len(data.get('body', ''))} 字")
    else:
        tree = lxml_html.fromstring(html)
        data["title"] = extract_generic_title(tree, html)
        data["body"] = extract_generic_body(tree)
        eprint(f"  标题: {data['title'][:50]}")
        eprint(f"  正文: {len(data['body'])} 字")

    if not data.get("title"):
        data["title"] = (re.sub(r'<title>([^<]+)</title>', r'\1', html[:2000])
                         if html else "")
    data.setdefault("account", "")
    data.setdefault("publishTime", "")

    return data


def clean_text(text):
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\u200b\ufeff]', '', text)
    text = re.sub(r' {3,}', '  ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def build_kb_path(account, title, pub_date):
    year = CURRENT_YEAR
    cat = "0000——个人"
    folder = "公众号文章"
    account_slug = re.sub(r'[^\u4e00-\u9fff\w]+', '_', account).strip('_') or "来源"
    title_slug = re.sub(r'[^\u4e00-\u9fff\w]+', '_', title).strip('_') or "文章"
    title_slug = title_slug[:50]

    date_prefix = NOW.strftime("%Y%m%d")
    if pub_date:
        m = re.search(r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})', pub_date)
        if m:
            date_prefix = f"{m.group(1)}{m.group(2).zfill(2)}{m.group(3).zfill(2)}"

    fname = f"{date_prefix}_{account_slug}_{title_slug}.txt"
    return KB_ARCHIVE / year / cat / folder / account_slug / fname


def save_to_kb(data, url):
    title = (data.get("title") or "无标题").strip()
    account = (data.get("account") or "公众号").strip()
    pub_time = (data.get("publishTime") or "").strip()
    body = (data.get("body") or "").strip()

    if not body or len(body) < 20:
        eprint("  ⚠ 正文为空或过短，跳过保存")
        return None

    body = clean_text(body)

    out = build_kb_path(account, title, pub_time)
    out.parent.mkdir(parents=True, exist_ok=True)

    content = (
        f"标题：{title}\n"
        f"来源：{account}\n"
        f"发布时间：{pub_time}\n"
        f"来源URL：{url}\n"
        f"入库时间：{NOW.strftime('%Y-%m-%d %H:%M')}\n"
        f"{'=' * 60}\n\n"
        f"{body}\n"
    )

    out.write_text(content, encoding="utf-8")
    eprint(f"  ✅ 保存: {out}")

    # Rebuild RAG archive index so new article is immediately searchable
    try:
        from utils.rag_engine import RAGEngine
        rag = RAGEngine()
        r = rag.add_file(str(out), 'archive')
        eprint(f"  ✅ RAG archive 索引已刷新: {r} chunks")
    except Exception as e:
        eprint(f"  ⚠ RAG 索引刷新失败: {e}（不影响文件保存）")

    return str(out)


def cmd_url(args):
    url = args.url
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    data = extract_from_url(url)

    error = data.get("error", "")
    if error:
        eprint(f"  ✗ {error}")
        return

    if args.no_save:
        body = data.get("body", "")
        if body:
            eprint(f"\n{body[:600]}...")
        return

    if len(data.get("body", "")) < 20:
        eprint("  正文过短，请检查链接是否有效")
        return

    path = save_to_kb(data, url)
    if path:
        print(path)


def cmd_search(args):
    query = args.query
    eprint(f"搜索: {query}")

    url = f"https://cn.bing.com/search?q={urllib.parse.quote(query)}"
    html = fetch_html(url)
    if html is None:
        return

    tree = lxml_html.fromstring(html)
    results = []
    for item in tree.xpath("//li[contains(@class, 'b_algo')]"):
        a = item.xpath(".//h2/a")
        if not a:
            continue
        href = a[0].get("href", "")
        title = a[0].text_content().strip()
        snippet = item.xpath(".//p[contains(@class, 'b_lineclamp')]")
        snippet_text = snippet[0].text_content().strip() if snippet else ""
        results.append({"title": title, "url": href, "snippet": snippet_text})

    if not results:
        eprint("未找到结果")
        return

    eprint(f"\n找到 {len(results)} 条结果:\n")
    for i, r in enumerate(results[:args.max], 1):
        eprint(f"  [{i}] {r['title'][:70]}")
        eprint(f"      {r['url'][:80]}")
        if r.get('snippet'):
            eprint(f"      {r['snippet'][:70]}")
        eprint()

    wx = [r for r in results if 'mp.weixin.qq.com' in r['url']]
    if wx:
        eprint(f"其中 {len(wx)} 篇公众号文章:")
        for r in wx:
            eprint(f"  {r['title'][:60]}")
            eprint(f"  {r['url']}\n")

    if wx and args.import_all:
        eprint("导入公众号文章...")
        for r in wx:
            d = extract_from_url(r["url"])
            if len(d.get("body", "")) > 20:
                save_to_kb(d, r["url"])


def cmd_batch(args):
    fp = args.file
    if not os.path.exists(fp):
        eprint(f"文件不存在: {fp}")
        return

    with open(fp, encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    eprint(f"共 {len(urls)} 个链接")
    ok = 0
    for i, url in enumerate(urls, 1):
        eprint(f"\n[{i}/{len(urls)}]")
        d = extract_from_url(url)
        if len(d.get("body", "")) > 20 and not d.get("error"):
            save_to_kb(d, url)
            ok += 1
        else:
            eprint(f"  ⚠ 跳过 ({d.get('error', '正文为空')})")
    eprint(f"\n结果: {ok}/{len(urls)}")


def main():
    p = argparse.ArgumentParser(
        description="文章知识库导入工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    u = sub.add_parser("url", help="从文章链接提取内容")
    u.add_argument("url", help="文章URL")
    u.add_argument("--no-save", action="store_true", help="仅预览不保存")

    s = sub.add_parser("search", help="搜索文章")
    s.add_argument("query", help="搜索词，如 [公众号名称] 理论宣讲")
    s.add_argument("--max", type=int, default=10, help="最大结果数")
    s.add_argument("--import-all", action="store_true", help="自动导入公众号文章")

    b = sub.add_parser("batch", help="批量导入URL文件")
    b.add_argument("file", help="URL列表文件（每行一个链接）")

    args = p.parse_args()
    if args.cmd == "url":
        cmd_url(args)
    elif args.cmd == "search":
        cmd_search(args)
    elif args.cmd == "batch":
        cmd_batch(args)


if __name__ == "__main__":
    main()
