from flask import Blueprint, request, jsonify, make_response,render_template, session
from elasticsearch import Elasticsearch
import json
import os
search_bp = Blueprint('search', __name__)

# 创建 Elasticsearch 客户端连接
es = Elasticsearch("http://localhost:9200")

#普通查询
def site_search(query):
    response = es.search(index="web_pages", body={
        "query": {
            "bool": {  # 使用 bool 查询
                "should": [
                    {"match": {"title": query}},    # 标题字段匹配
                    {"match": {"content": query}},  # 内容字段匹配
                    {"match": {"url": query}},      # URL 字段匹配
                    {"match": {"editor": query}}    # 编辑者字段匹配
                ]
            }
        },
        "highlight": {
            "pre_tags": ["<strong>"],
            "post_tags": ["</strong>"],
            "fields": {
                "title": {},
                "content": {}, 
                "url": {},
                "editor": {} 
            }
        }
    })
    return response['hits']['hits']

# 站内查询
def site_search(query):
    response = es.search(index="web_pages", body={
        "size": 1000,
        "query": {
            "wildcard": {
                "url": {
                    "value": f"*{query}*"  # 使用通配符模糊匹配 URL
                }
            }
        },
        "highlight": {
            "pre_tags": ["<strong>"],
            "post_tags": ["</strong>"],
            "fields": {
                "url": {}  # 为编辑字段启用高亮
            }
        }
    })
    
    return response['hits']['hits']

# 短语查询
def one_phrase_search(query):
    response = es.search(index="web_pages", body={
        "size": 1000,
        "query": {
            "bool": {
                "should": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "title",
                                "content",
                                "editor",
                            ],
                        }
                    },
                    {
                        "bool": {
                            "should": [
                                {"match_phrase": {"title": query}},
                                {"match_phrase": {"content": query}},
                                {"match_phrase": {"editor": query}},
                            ]
                        }
                    }
                ]
            }
        },
        "highlight": {
            "pre_tags": ["<strong>"],
            "post_tags": ["</strong>"],
            "fields": {
                "title": {},
                "content": {},
                "editor": {}  # 为编辑字段启用高亮
            }
        }
    })
    return response['hits']['hits']


def multi_phrase_search(query):
    # 将查询分割为多个短语
    phrases = query.split()
    # 构建 `must` 查询（与条件，所有短语必须匹配）
    must_clauses = [{"match_phrase": {"content": phrase}} for phrase in phrases]
    # 构建 `should` 查询（或条件，至少一个短语匹配）
    should_clauses = [{"match_phrase": {"content": phrase}} for phrase in phrases]
    # 构建 bool 查询
    bool_query = {
        "should": should_clauses,
        "must": must_clauses,
        "minimum_should_match": 1  # 至少匹配一个 should
    }
    # 添加 boost 给 `must` 查询，使得 “与” 查询优先
    boosted_query = {
        "query": {
            "bool": {
                "must": must_clauses, 
                "should": should_clauses,
                "minimum_should_match": 1
            }
        },
        # 添加高亮选项
        "highlight" : {
            "pre_tags": ["<strong>"],  # 高亮开始标签
            "post_tags": ["</strong>"],  # 高亮结束标签
            "fields": {
                "content": {}  # 高亮字段，针对 `content` 字段
            }
        }
    }
    
    # 为整个查询添加 boost（`boost` 放在 query 层级，而不是字段层级）
    boosted_query["query"]["bool"]["boost"] = 2.0  # 增加整个查询的 boost
    # 执行查询
    response = es.search(index="web_pages", body=boosted_query)

    
    return response['hits']['hits']

# 通配符查询
def wildcard_search(query):
    response = es.search(index="tp", body={
        "query": {
            "bool": {
                "should": [
                    {"wildcard": {"title": {"value": query}}},
                    {"wildcard": {"content": {"value": query}}},
                    {"wildcard": {"editor": {"value": query}}},
                    {"wildcard": {"url": {"value": query}}}
                ]
            }
        },
        "highlight": {
            "pre_tags": ["<strong>"],
            "post_tags": ["</strong>"],
            "fields": {
                "title": {},   # 高亮标题
                "content": {}, # 高亮内容
                "editor": {},  # 高亮编辑
                "url": {}      # 高亮URL
            }
        },
        "sort": [
            {"_score": {"order": "desc"}}  # 根据得分排序
        ]
    })
    return response['hits']['hits']

# 文档查询
@search_bp.route('/documents',methods=['GET'])
def search_documents():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400
    s = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["title", "content"]
            }
        }
    }
    results = es.search(index="documents", body=s)
    documents = []
    for hit in results['hits']['hits']:
        document = {
            "title": hit["_source"]["title"],
            "url": hit["_source"]["url"],
            "content": hit["_source"]["content"][:150] + "..."  # 提取前150字符作为摘要
        }
        documents.append(document)
    # print(document[url])
    return documents

# 网页快照
@search_bp.route('/snapshot')
def _snapshot():
    # 从请求中获取标题
    title = request.args.get('title')
    if not title:
        return "不合法的参数"
    # 构建 HTML 文件路径
    title = title.replace("?","_").replace("”", "_").replace(":", "_").replace("/", "_").replace("“", "_").replace(" ","")
    # print(title)
    html_file_path = f'./routes/html/{title}.html'
    # print(f"生成的文件路径: {html_file_path}")
    # 检查文件是否存在
    if not os.path.exists(html_file_path):
        return "网页快照文件不存在"
    # 读取 HTML 文件内容
    with open(html_file_path, 'r', encoding='utf-8') as f:
        snapshot = f.read()
    # 返回网页快照
    return render_template('snapshot.html', snapshot=snapshot)

# 读取信息
HISTORY = 'history.json'
def load_users():
    if os.path.exists(HISTORY):
        try:
            with open(HISTORY, 'r', encoding='utf-8') as file:
                users_data = json.load(file)
        except json.JSONDecodeError:
            users_data = {}
    else:
        users_data = {}
    return users_data
    
def reorder_results(results, user_info):
    # 根据用户的个人信息（如学院、专业、历史记录等）重新排序查询结果
    if not user_info:
        return results
    user_history = user_info.get('history', [])
    user_college = user_info.get('college', '').lower()
    
    # 给每个结果计算分数
    results_with_scores = []
    for doc in results:
        score = 0
        title = doc['_source'].get('title', '').lower()
        content = doc['_source'].get('content', '').lower()  # 假设是内容
        # print(title)
        # 根据用户历史记录给文档打分
        for term in user_history:
            if term.lower() in title:
                score += 1
            if term.lower() in content:
                score += 5
        # 根据用户的学院给文档加分
        if user_college and user_college in title:
            score += 2
        # 为当前文档添加分数并加入到结果列表
        results_with_scores.append({**doc, 'score': score})
    # 根据分数降序排序，分数高的排在前面
    results_with_scores.sort(key=lambda x: x['score'], reverse=True)
    # 返回重新排序后的结果
    return results_with_scores[:10]

@search_bp.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    search_type = request.args.get('type')

    if search_type == 'site_search':
        results = site_search(query)
    elif search_type == 'one_phrase_search':
        results = one_phrase_search(query)
    elif search_type == 'multi_phrase_search':
        results = multi_phrase_search(query)
    elif search_type == 'wildcard_search':
        results = wildcard_search(query)
    elif search_type == 'log_search':
        results = log_search(query)
    elif search_type == 'snapshot_search':
        results = snapshot_search(query)
    else:
        results = simple_search(query)
    # print(results)  # 调试输出
    # 获取当前登录用户的信息
    if 'username' not in session:
        return None  # 用户未登录，返回空
    username = session['username']
    users_db = load_users()
    user_info = users_db.get(username, None)  # 返回当前用户信息
    # 重排查询结果
    reordered_results = reorder_results(results, user_info)

    #return results
    return reordered_results