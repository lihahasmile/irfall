from elasticsearch import Elasticsearch
import json
from datetime import datetime

# 初始化 Elasticsearch 客户端
es = Elasticsearch("http://localhost:9200")  # 根据你的实际地址调整

# 定义索引名称
index_name = "tp"

# 加载数据文件
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 定义一个函数来格式化日期字符串
def format_publish_time(publish_time_str):
    try:
        # 将日期字符串转换为 datetime 对象
        publish_time = datetime.strptime(publish_time_str, "%Y-%m-%d %H:%M")
        # 将 datetime 对象格式化为 Elasticsearch 支持的格式
        return publish_time.strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None  # 如果格式不匹配，返回 None 或处理其他情况

# 创建索引（如果索引不存在）
if not es.indices.exists(index=index_name):
    doc = {
        'settings': {
            'analysis': {
                'analyzer': 'ik_max_word',
                "search_analyzer": 'ik_max_word'
            }
        },
        'mappings': {
            'properties': {
                'url': {
                    'type': 'text',  # 使用 text 类型进行全文搜索，支持通配符查询
                    'fields': {
                        'keyword': {  # 使用 multi-field，允许 keyword 精确匹配
                            'type': 'keyword'
                        }
                    }
                },
                'title': {
                    'type': 'text',
                    'analyzer': 'ik_max_word',  # 使用 ik_max_word 分词器
                    'search_analyzer': 'ik_max_word'  # 搜索时也使用同样的分词器
                },
                'source': {
                    'type': 'text'
                },
                'publish_time': {
                    'type': 'date'  # 将时间作为 date 类型
                },
                'content': {
                    'type': 'text',  # 使用 text 类型进行全文搜索，支持通配符查询
                    'analyzer': 'ik_max_word',  # 使用 ik_max_word 分词器
                    'search_analyzer': 'ik_max_word'
                },
                'links': {
                    'type': 'keyword'  # 链接字段使用 keyword 类型，不进行分析
                },
                'pagerank': {
                    'type': 'float'  # pagerank 字段使用 float 类型
                },
            }
        }
    }
    es.indices.create(index=index_name, body=doc)

# 构建文档并索引
for item in data:
    # 格式化 publish_time 字段
    item["publish_time"] = format_publish_time(item["publish_time"])
    es.index(index=index_name, id=item["url"], body=item)
   
# 刷新索引以使更改生效
es.indices.refresh(index=index_name)

print("索引构建完成")

# 查询索引中的所有文档
response = es.count(index='tp')
print(response)
