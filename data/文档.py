#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import os
import asyncio
import aiofiles
import pandas as pd
import httpx
from parsel import Selector
from urllib.parse import urljoin
from urllib.parse import urlsplit

# 假设分页 URL 采用 doc_id=(i) 的格式
url_list = [f'https://jwc.nankai.edu.cn/tzgg/list{i}.htm' for i in range(2, 13)]
url_list.append('https://jwc.nankai.edu.cn/tzgg/list.htm')

# 控制并发量
sem = asyncio.Semaphore(10)
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 存储爬取结果
new_data = pd.DataFrame(columns=['title', 'url', 'content', 'document_links', 'document_names'])
document_links_data = pd.DataFrame(columns=['document_name', 'document_link']) 
result_dict = {}

async def parse_catalogs_page(url):
    """
    解析目录页面，提取符合条件的链接和标题
    """
    async with sem:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            selector = Selector(response.text)

            # 解析页面中的符合条件的链接和标题
            items = selector.css('div.item')
            for item in items:
                link = item.css('.t a::attr(href)').get()  # 提取链接
                title = item.css('.t a::text').get()  # 提取标题

                if link and title:
                    full_url = urljoin(url, link)
                    result_dict[full_url] = title


async def parse_page(url, title):
    async with sem:
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10,
                                         headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}) as client:
                if url.startswith('http') or url.startswith('https'):
                    response = await client.get(url)
                    selector = Selector(response.text)

                    # 提取正文内容
                    content = " ".join(selector.css('p::text, div::text').getall()).strip()
                    content = content.replace(' ', '').replace('　', '').replace('\r', '').replace('\n', '').replace('\t', '').replace('|', '')

                    # 提取文档链接和文件名
                    document_links = selector.css('a::attr(href)').getall()
                    document_titles = selector.css('a::attr(sudyfile-attr)').getall()  # 获取文件的标题信息
                    document_links = [urljoin(url, link) for link in document_links if link.endswith(('.pdf', '.docx'))]

                    document_names = []  # 用于存储文档的名称
                    # 下载文档到本地
                    for i, doc_link in enumerate(document_links):
                        # 从 sudyfile-attr 获取文件名（如果存在）
                        if document_titles:
                            # 使用获取的文件名，确保扩展名不变
                            file_name = document_titles[i].strip().replace('{','').replace(' ', '').replace("'","").replace('附件','').replace('}','').replace('：', '').replace(':', '').replace('title', '').replace(' ', '')
                        else:
                            # 从链接提取文件名并确保扩展名不变
                            file_name = os.path.basename(doc_link)
                        
                        # 获取文件的扩展名，确保不改变文件类别
                        file_extension = os.path.splitext(file_name)[1]
                        if not file_name.endswith(file_extension):  # 确保文件扩展名正确
                            file_name += file_extension

                        document_names.append(file_name)  # 添加文件名到列表中
                        # 将文档的名称和链接保存到新的 DataFrame
                        document_links_data.loc[len(document_links_data)] = [file_name, doc_link]
                        
                        async with client.stream("GET", doc_link) as stream:
                            if stream.status_code == 200:
                                doc_path = os.path.join('./文档/下载文档', file_name)
                                async with aiofiles.open(doc_path, mode='wb') as f:
                                    async for chunk in stream.aiter_bytes():
                                        await f.write(chunk)

                    # 保存页面源代码
                    safe_title = title.replace("?", "_").replace(":", "_").replace("/", "_").replace("\\", "_")
                    async with aiofiles.open(f'./文档/{safe_title}.html', mode='w', encoding='utf-8') as f:
                        await f.write(response.text)

                    # 存储标题、URL、正文内容、文档链接和文档名称
                    new_data.loc[len(new_data)] = [title, url, content, document_links, document_names]
        except Exception as e:
            print(f'Error parsing {url}: {e}')


async def main():
    if not os.path.exists('./文档'):
        os.mkdir('./文档')
    if not os.path.exists('./文档/下载文档'):
        os.mkdir('./文档/下载文档')

    # 解析目录页面，抓取符合条件的文章链接和标题
    tasks = [asyncio.create_task(parse_catalogs_page(url)) for url in url_list]
    await asyncio.gather(*tasks)

    # 根据链接抓取文章内容
    tasks = [asyncio.create_task(parse_page(url, title)) for url, title in result_dict.items()]
    await asyncio.gather(*tasks)

    # 将标题、URL、正文内容、文档链接和文档名称保存到 CSV 文件
    new_data.to_csv("./文档.csv", index=False)
    # 将文档名称和链接保存到新的 CSV 文件
    document_links_data.to_csv("./文档_links.csv", index=False)


if __name__ == '__main__':
    asyncio.run(main())
