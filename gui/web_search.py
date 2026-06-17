"""网络搜索模块 —— 百度 + 通用搜索引擎"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


_BAIDU_SESSION = None


def _get_baidu_session():
    """获取带 Cookie 的百度会话"""
    global _BAIDU_SESSION
    if _BAIDU_SESSION is not None:
        return _BAIDU_SESSION
    import requests
    session = requests.Session()
    session.headers.update({
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/125.0.0.0 Safari/537.36'
        ),
    })
    try:
        session.get('https://www.baidu.com', timeout=5)
    except Exception:
        pass
    _BAIDU_SESSION = session
    return session


def _search_baidu(query: str, max_results: int = 5) -> list[dict]:
    """百度自然搜索"""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning('beautifulsoup4 未安装，跳过百度搜索')
        return []
    try:
        session = _get_baidu_session()
        resp = session.get(
            'https://www.baidu.com/s',
            params={'wd': query, 'rn': min(max_results, 10)},
            timeout=10,
        )
        resp.encoding = 'utf-8'
        if len(resp.text) < 5000:
            logger.warning('百度反爬拦截，搜索失败')
            return []
        soup = BeautifulSoup(resp.text, 'lxml')
        results = []
        for tag in soup.select('.result, .c-container'):
            title_el = tag.select_one('h3 a')
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            href = title_el.get('href', '')
            snippet_el = tag.select_one('.c-abstract, .content-right_8Zs40, .c-span-last')
            snippet = snippet_el.get_text(strip=True) if snippet_el else ''
            if title:
                results.append({
                    'title': title, 'snippet': snippet,
                    'url': href, 'source': 'baidu',
                })
        return results[:max_results]
    except Exception as e:
        logger.warning('百度搜索失败: %s', e)
        return []


def _search_bing(query: str, max_results: int = 5) -> list[dict]:
    """Bing 搜索（国内可访问，HTML 结构稳定）"""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return []
    try:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/125.0.0.0 Safari/537.36'
            ),
        }
        resp = requests.get(
            'https://cn.bing.com/search',
            params={'q': query, 'count': max_results},
            headers=headers, timeout=10,
        )
        soup = BeautifulSoup(resp.text, 'lxml')
        results = []
        for tag in soup.select('#b_results > li.b_algo'):
            title_el = tag.select_one('h2 a')
            snippet_el = tag.select_one('.b_caption p')
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            href = title_el.get('href', '')
            snippet = snippet_el.get_text(strip=True) if snippet_el else ''
            if title:
                results.append({
                    'title': title, 'snippet': snippet,
                    'url': href, 'source': 'bing',
                })
        return results[:max_results]
    except Exception as e:
        logger.warning('Bing 搜索失败: %s', e)
        return []


def search_combined(query: str, max_results: int = 5) -> list[dict]:
    """双引擎搜索（百度 + Bing），合并去重后返回"""
    from concurrent.futures import ThreadPoolExecutor

    results = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        baidu_future = pool.submit(_search_baidu, query, max_results)
        bing_future = pool.submit(_search_bing, query, max_results)
        for future in (baidu_future, bing_future):
            try:
                results.extend(future.result(timeout=15))
            except Exception:
                pass

    seen = set()
    deduped = []
    for r in results:
        url = r.get('url', '')
        if url and url not in seen:
            seen.add(url)
            deduped.append(r)
    return deduped[:max_results]


def rerank(query: str, results: list[dict]) -> list[dict]:
    """用 TF-IDF 对搜索结果按相关性重排序"""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        return results
    if not results:
        return results
    texts = [f"{r['title']} {r.get('snippet', '')}" for r in results]
    try:
        vec = TfidfVectorizer(max_features=512, ngram_range=(1, 2),
                              analyzer='char_wb')
        matrix = vec.fit_transform(texts + [query])
        scores = cosine_similarity(matrix[-1:], matrix[:-1])[0]
        indexed = list(enumerate(scores))
        indexed.sort(key=lambda x: -x[1])
        return [results[i] for i, _ in indexed]
    except Exception:
        return results


def extract_keywords(query: str, api_key: Optional[str] = None) -> list[str]:
    """用 DeepSeek 提取搜索关键词；无 API Key 时直接用原始需求搜索"""
    if api_key:
        try:
            from utils.api_client import DeepSeekClient
            client = DeepSeekClient(api_key=api_key)
            prompt = (
                '你是一个公文写作助手。根据用户的需求，提取 2-3 组搜索关键词，'
                '每组 2-4 个词，空格分隔，每行一组。只输出关键词，不要额外说明。\n\n'
                f'用户需求：{query}'
            )
            result = client.chat(prompt)
            if result.success and result.content:
                groups = [g.strip() for g in result.content.strip().split('\n') if g.strip()]
                if groups:
                    return groups
        except Exception as e:
            logger.warning('关键词提取失败: %s', e)

    return [query]
