import json
import re
import os
import asyncio
import aiofiles
import pandas as pd
import networkx as nx
from bs4 import BeautifulSoup  # 导入 BeautifulSoup

output_df = pd.read_csv("./output.csv", index_col=0)
index_data = [] 
url_url_list_dict = {} 
skipped_urls = set()
missing_title_df = pd.DataFrame(columns=['url', 'file'])
sem = asyncio.Semaphore(150)  # 设置协程数，这边都是本地IO，所以可以设置较高的协程数

def is_valid_link(link):
    """ 检查链接是否符合 http://news.nankai.edu.cn/... 格式，并以数字.shtml结尾 """
    return bool(re.match(r"^http://news\.nankai\.edu\.cn/.+\d+\.shtml$", link))

async def create_index(file):
    async with sem:
        async with aiofiles.open(file, mode='r', encoding='utf-8') as f:
            text = await f.read()
            soup = BeautifulSoup(text, 'html.parser')  # 使用 BeautifulSoup 解析 HTML

            title = soup.title.string if soup.title else ""  # 获取 title

            _title = title.replace("?", "_").replace("”", "_").replace(":", "_").replace("/", "_").replace("“", "_")
            # 从 CSV 中获取对应的 URL
            if _title not in output_df.index:
                print(f"Skipping {file}.")
                missing_title_df.loc[len(missing_title_df)] = [_title, file]
                skipped_urls.add(_title)  # 将跳过的标题添加到跳过列表
                return  # 如果在 CSV 中没有找到对应的 title，则跳过该文件处理

            url = output_df.loc[_title, 'url']
            if isinstance(url, pd.Series):  # 如果是 Series 类型，取出其唯一的值
                url = url.iloc[0]

            # 提取来源
            source = soup.find('span', style="margin-right:10px;")  # 根据 style 来定位
            source = source.get_text(strip=True).replace("来源：", "") if source else ""

            # 提取发稿时间
            publish_time = ""
            publish_time_tag = soup.find('span', string=re.compile(r'发稿时间：(\d{4}-\d{2}-\d{2} \d{2}:\d{2})'))
            if publish_time_tag:
                publish_time = publish_time_tag.get_text().split("：")[-1].strip()

            # 获取正文内容（更灵活的方式）
            content_p = [p.get_text() for p in soup.find_all('p')]  # 获取所有 <p> 标签的文本
            content_div = [div.get_text() for div in soup.find_all('div', {'id': 'text_content'})]  # 获取 <div id="text_content"> 的文本
            content_c = soup.find('div', class_='content')  # 假设正文在 <div class='content'> 中

            # 合并多个结果
            _content = content_p + content_div
            if content_c:
                _content.append(content_c.get_text())
            
            # 获取编辑者的名字（根据提供的 HTML 结构）
            editor_name = ""
            if _content and "编辑" in "".join(_content[-1]):
                editor_name = "".join(_content[-1]).replace("编辑：", "").replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')

            if _content and "编辑" in "".join(_content[-1]):
                content = "".join(_content[:-1]) 
                content=content.replace(' ', ' ').replace('　', '').replace('\r', '').replace('\n', '').replace('\t', '')
            else:
                content = "".join(_content) 
                content=content.replace(' ', ' ').replace('　', '').replace('\r', '').replace('\n', '').replace('\t', '')

            # title 处理
            title = str(title)
            title=title.replace('-南开大学','').replace(' ', ' ').replace('　', '').replace('-多彩校园','').replace('-广播','').replace('-南开要闻','').replace('-综合新闻','').replace('-南开故事','').replace('-媒体南开','').replace('-南开之声','')

            # 获取期次和阅读数（根据提供的 HTML 结构）
            period_text = ""
            period_tag = soup.find('span', string=re.compile(r'期次：(\S+)'))
            if period_tag:
                period_text = period_tag.get_text(strip=True).replace('期次：', '')

            read_count_text = ""
            read_count_tag = soup.find('span', string=re.compile(r'阅读：(\d+)'))
            if read_count_tag:
                read_count_text = read_count_tag.get_text(strip=True).replace('阅读：', '')

            # 提取并筛选页面中的链接
            links = [a['href'] for a in soup.find_all('a', href=True)]  # 提取所有 <a> 标签的 href 属性
            filtered_links = [link for link in links if is_valid_link(link)]  # 过滤符合条件的链接

            # 构建 URL 对应的字典
            page_info = {
                "url": url,
                "title": title,
                "source": source,
                "publish_time": publish_time,
                "editor": editor_name,
                "period": period_text, 
                "readcount": read_count_text,
                "content": content,
                "links": filtered_links  # 仅保留符合条件的链接
            }

            index_data.append(page_info)

            # 提取页面中的url
            url_list = []
            url_list.extend(filtered_links)
            url_url_list_dict[url] = url_list

async def compute_pagerank():
    """ 使用 NetworkX 计算 PageRank """
    G = nx.DiGraph()
    # 将页面及其连接关系构建成图
    for item in index_data:
        main_url = item["url"]
        related_links = item["links"]
        G.add_node(main_url)
        for link in related_links:
            G.add_edge(main_url, link)

    # 计算 PageRank
    pageranks = nx.pagerank(G)

    # 将计算的 pagerank 添加到每个页面信息中
    for item in index_data:
        url = item["url"]
        item["pagerank"] = pageranks.get(url, 0)  # 如果没有 pagerank，则默认给 0

async def main():
    files = os.listdir('./html')  # 获取html文件夹下所有文件名
    tasks = [asyncio.create_task(create_index(f'./html/{file}')) for file in files]
    await asyncio.gather(*tasks)

    # 计算并添加 PageRank
    await compute_pagerank()

    # 将数据保存为 JSON 文件
    with open('./data.json', 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=4)

    # 将数据保存为 CSV 文件
    index_df = pd.DataFrame(index_data)
    index_df.to_csv('./data.csv', index=False, encoding='utf-8-sig')

    # 将没有找到 title 的文件和 URL 存储到 CSV
    if not missing_title_df.empty:
        missing_title_df.to_csv("./miss.csv", encoding='utf-8-sig')
        print(f"Missing titles saved to './miss.csv'.")

if __name__ == '__main__':
    asyncio.run(main())
