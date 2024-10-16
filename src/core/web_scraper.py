import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

import logging

logging.basicConfig(level=logging.INFO)

def scrape_webpage(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 尝试获取标题
        title = soup.title.string if soup.title else "无标题"
        title = title.strip() if title else "无标题"
        
        # 尝试获取主要内容
        main_content = ""
        for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            text = tag.get_text(strip=True)
            if text:
                main_content += text + "\n"
        
        # 获取域名
        domain = urlparse(url).netloc
        
        return {
            'title': title,
            'content': main_content.strip(),
            'url': url,
            'domain': domain
        }
    except Exception as e:
        print(f"抓取网页时出错: {e}")
        return None
