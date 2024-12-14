from flask import Blueprint, request, jsonify, make_response, session
from Levenshtein import distance as lev_distance
import numpy as np
import json
import os
import re
import requests
personal_bp = Blueprint('personal', __name__)
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

def get_history_suggestions(user_info, query):
    user_history = user_info.get('history', [])
    suggestions = [term for term in user_history if term.lower().startswith(query.lower())]
    return suggestions

def get_baidu_suggestions(user_info, query):
    user_history = user_info.get('history', [])
    try:
        url = f"http://suggestion.baidu.com/su?wd={query}&json=1&p=3"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()  # 检查 HTTP 状态码
        raw_data = response.text
        match = re.search(r'window.baidu.sug\((.*)\)', raw_data)
        if match:
            data = json.loads(match.group(1))
            return data.get("s", [])
    except Exception as e:
        print(f"Error fetching Baidu suggestions: {e}")
    return []
def calculate_levenshtein_similarity(term, query):
    # Levenshtein 距离越小表示两个字符串越相似
    distance = lev_distance(term.lower(), query.lower())
    # 计算相似度，最小距离为0，相似度越高越好
    similarity = 1 / (1 + distance)  # 距离越小，相似度越高
    return similarity

@personal_bp.route('/get_suggestions', methods=['GET'])
def get_suggestions():
    query = request.args.get('q')
    if not query:
        return jsonify([])  # 如果没有查询参数，返回空建议

    username = session['username']
    users_db = load_users()
    user_info = users_db.get(username, None)  # 获取当前用户信息
    
    history_suggestions = get_history_suggestions(user_info, query)
    baidu_suggestions = get_baidu_suggestions(user_info, query)
    scored_suggestions = []
    for suggestion in baidu_suggestions:
        score = 0
        # 累加该建议与历史记录中的每个词的相似度
        for history_term in history_suggestions:
            score += calculate_levenshtein_similarity(suggestion, history_term)
        # 将计算得出的评分和建议一起存储
        scored_suggestions.append((suggestion, score))
    
    # 按照得分从高到低排序
    sorted_suggestions = [suggestion for suggestion, _ in sorted(scored_suggestions, key=lambda x: x[1], reverse=True)]

    all_suggestions = history_suggestions + sorted_suggestions
    # 对联想结果按相似度排序
    
    return jsonify(list(all_suggestions))