from elasticsearch import Elasticsearch
import os
import json
import time
from urllib.parse import urljoin
import pandas as pd
import fitz
from docx import Document 

# 初始化Elasticsearch
es = Elasticsearch("http://localhost:9200")

# 定义索引名称
INDEX_NAME = "documents"

# 检查并创建索引
def create_index():
    if not es.indices.exists(index=INDEX_NAME):
        es.indices.create(index=INDEX_NAME, body={
            "mappings": {
                "properties": {
                    "title": {"type": "text"},
                    "content": {"type": "text"},
                    "url": {"type": "keyword"}
                }
            }
        })

# 上传并索引文档
def index_document(title, content, url):
    doc = {
        "title": title,
        "content": content,
        "url": url
    }
    es.index(index=INDEX_NAME, body=doc)

# 提取 PDF 内容
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text")
    return text

# 提取 DOCX 内容
def extract_text_from_docx(docx_path):
    doc = Document(docx_path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

# 从 CSV 文件读取 document_name 和 document_link
def load_document_links(csv_path):
    return pd.read_csv(csv_path)

# 上传文档
def upload_documents():
    # 假设文档存储在 "documents" 文件夹中
    documents_folder = './下载文档'
    if not os.path.exists(documents_folder):
        print(f"{documents_folder} folder does not exist.")
        return

    document_links_df = load_document_links('./文档_links.csv')

    for filename in os.listdir(documents_folder):
        file_path = os.path.join(documents_folder, filename)
        if os.path.isfile(file_path):
            title = filename.replace(".pdf", "").replace(".docx", "").replace(".xls", "")
            
            content = ""
            document_url = ""

            try:
                # 判断文件类型并解析
                if filename.endswith(".pdf"):
                    content = extract_text_from_pdf(file_path)
                elif filename.endswith(".docx"):
                    content = extract_text_from_docx(file_path)
                elif filename.endswith(".txt"):
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                # 查找对应的 document_url
                matching_row = document_links_df[document_links_df['document_name'] == filename]
                if not matching_row.empty:
                    document_url = matching_row['document_link'].values[0]
                print(document_url)

                # 索引到 Elasticsearch
                index_document(title, content, document_url)
                print(f"Document {title} indexed successfully.")

            except Exception as e:
                print(f"Error processing file {filename}: {e}")

# 执行索引创建和上传文档
if __name__ == "__main__":
    create_index()
    upload_documents()

# 查询索引中的所有文档
response = es.count(index='documents')
print(response)

# # 删除索引
# index_name = "documents"  # 替换为你要删除的索引名称
# response = es.indices.delete(index=index_name)

# print(response)