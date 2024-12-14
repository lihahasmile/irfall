#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import asyncio
import aiofiles
import pandas as pd
import httpx
from parsel import Selector
from urllib.parse import urljoin  # 导入urljoin
# 假设分页 URL 采用 doc_id=(i) 的格式
url_list = [f'https://news.nankai.edu.cn/ywsd/system/count//0003000/000000000000/000/000/c0003000000000000000_000000638.shtml{i}' for i in range(3, 702)]
url_list.append('https://news.nankai.edu.cn/ywsd/index.shtml') 

sem = asyncio.Semaphore(10)  # 设置协程数，爬虫协程限制较低，减少被爬服务器的压力
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # 解决windows下的RuntimeError

result_dict = {}

# 创建new_data，用于存储title和url，以便后续使用，索引是title，列是url
new_data = pd.DataFrame(columns=['url'])
new_data.index.name = 'title'


async def parse_catalogs_page(url):
    async with sem:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            selector = Selector(response.text)
            # 解析页面中的所有链接，获取 href 和 文本
            links = zip(selector.css('a::attr(href)').getall(), selector.css('a::text').getall())
            for link, text in links:
                # 将相对路径转换为绝对路径
                full_url = urljoin(url, link)
                result_dict[full_url] = text


async def parse_page(url):
    async with sem:
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10,
                                         headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}) as client:
                if url.startswith('http') or url.startswith('https'):
                    response = await client.get(url)
                    selector = Selector(response.text)
                    title = selector.css('title::text').get()

                    # 处理文件名中的非法字符
                    if title:
                        title = title.replace("?","_").replace("”", "_").replace(":", "_").replace("/", "_").replace("“", "_")
                        async with aiofiles.open(f'./html/{title}.html', mode='w', encoding='utf-8') as f:
                            await f.write(response.text)

                        # 存储标题和URL的映射
                        new_data.loc[title] = url
        except Exception as e:
            print(f'Error parsing {url}: {e}')


async def main():
    # 检查 html 文件夹是否存在，不存在则创建
    if not os.path.exists('./html'):
        os.mkdir('./html')

    # 解析目录页面，抓取所有文章链接
    tasks = [asyncio.create_task(parse_catalogs_page(url)) for url in url_list]
    await asyncio.gather(*tasks)

    # 根据链接抓取文章内容
    tasks = [asyncio.create_task(parse_page(url)) for url in result_dict.keys()]
    await asyncio.gather(*tasks)

    # 将标题与URL的映射关系保存到 CSV 文件
    new_data.to_csv("./html.csv")


if __name__ == '__main__':
    asyncio.run(main())
