"""Quick test for web search module"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from gui.web_search import _search_bing, search_combined, rerank, extract_keywords

print('=== Bing 搜索测试 ===')
results = _search_bing('安全生产检查 通知', max_results=3)
print(f'搜索结果: {len(results)} 条')
for r in results:
    print(f'  [{r["source"]}] {r["title"][:60]}')
    print(f'    摘要: {r["snippet"][:80]}')

print()
print('=== 百度搜索测试 ===')
try:
    from gui.web_search import _search_baidu
    baidu_results = _search_baidu('安全生产检查 通知', max_results=3)
    print(f'搜索结果: {len(baidu_results)} 条')
    for r in baidu_results:
        print(f'  [{r["source"]}] {r["title"][:60]}')
except Exception as e:
    print(f'百度搜索异常: {e}')

print()
print('=== 双引擎合并 ===')
combined = search_combined('安全生产检查 通知', max_results=5)
print(f'合并结果: {len(combined)} 条')

print()
print('=== 重排序 ===')
ranked = rerank('安全生产检查通知范文', combined)
print(f'重排序后: {len(ranked)} 条')
for r in ranked:
    print(f'  [{r["source"]}] (相关性) {r["title"][:60]}')

print()
print('=== 关键词提取 ===')
kw = extract_keywords('写一份关于安全生产的通知')
print(f'关键词: {kw}')
