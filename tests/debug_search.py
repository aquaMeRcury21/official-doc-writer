"""Debug search response"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bs4 import BeautifulSoup
import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36',
}

resp = requests.get('https://www.baidu.com/s', params={'wd': '安全生产检查 通知'}, headers=headers, timeout=10)
print(f'Status: {resp.status_code}')
print(f'Length: {len(resp.text)}')
print()

soup = BeautifulSoup(resp.text, 'lxml')
containers = soup.select('.result, .c-container')
print(f'Found {len(containers)} containers')
if containers:
    for tag in containers[:3]:
        title = tag.select_one('h3 a')
        print(f'  Title: {title.get_text(strip=True) if title else "NONE"}')
else:
    # Check for common patterns
    print('Has .result:', bool(soup.select('.result')))
    print('Has .c-container:', bool(soup.select('.c-container')))
    for keyword in ['百度安全验证', '百度搜索', 'result', '结果']:
        print(f'  Has "{keyword}": {keyword in resp.text}')
