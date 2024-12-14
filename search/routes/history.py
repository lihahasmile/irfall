from flask import Blueprint, request, jsonify, make_response, session
history_bp = Blueprint('history', __name__)
import json
import os

# 最大记录数
MAX_HISTORY = 10
# 用户历史记录文件路径
HISTORY_DATA_FILE = 'history.json'
# 读取用户信息
USER_DATA_FILE = 'users.json'
def load_users():
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as file:
                # 尝试加载文件内容
                users_data = json.load(file)
        except json.JSONDecodeError:
            # 如果文件格式不正确，则返回空字典
            users_data = {}
    else:
        # 如果文件不存在，则返回空字典
        users_data = {}
    return users_data


# 获取历史记录，返回该用户的历史记录
def load_user_history(username):
    if os.path.exists(HISTORY_DATA_FILE):
        try:
            with open(HISTORY_DATA_FILE, 'r', encoding='utf-8') as file:
                history_data = json.load(file)
                # 返回指定用户的历史记录，如果用户没有历史记录则返回空列表
                return history_data.get(username, {}).get('history', [])
        except json.JSONDecodeError:
            return []  # 返回空列表，防止程序崩溃
    return []  # 如果文件不存在，返回空列表

# 保存用户历史记录
def save_user_history(username, history,college,major):
    history_data = {}
    # 检查文件是否存在并且不为空
    if os.path.exists(HISTORY_DATA_FILE) and os.path.getsize(HISTORY_DATA_FILE) > 0:
        try:
            with open(HISTORY_DATA_FILE, 'r', encoding='utf-8') as file:
                history_data = json.load(file)  # 尝试加载现有的历史记录
        except json.JSONDecodeError:
            print("JSON Decode Error: The file is empty or invalid. Starting fresh.")
            history_data = {}  # 如果文件格式有问题，则重新初始化为空字典
    
    # 更新该用户的历史记录
    history_data[username] = {
        'username': username,
        'college': college,
        'major': major,
        'history': history
    }

    with open(HISTORY_DATA_FILE, 'w', encoding='utf-8') as file:
        json.dump(history_data, file,ensure_ascii=False, indent=4)

# 获取当前用户的历史记录
def get_user_history():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 403
    username = session['username']
    history = load_user_history(username)
    return history

@history_bp.route('/get_history', methods=['GET'])
def get_history():
    """返回历史记录"""
    history = get_user_history()
    if isinstance(history, tuple):  # 如果是错误返回（例如用户未登录），直接返回
        return history
    # query = request.args.get('q', '').lower()
    # # 根据输入内容筛选匹配记录（可选）
    # filtered_history = [item for item in history if query in item.lower()]
    return jsonify({'history': history})

@history_bp.route('/save_history', methods=['POST'])
def save_history():
    """保存新的历史记录"""
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 403
    
    query = request.json.get('query')
    if not query:
        return jsonify({'error': 'Invalid query'}), 400

    username = session['username']
    users_db = load_users()
    user_info = users_db.get(username, {})
    college = user_info.get('college')
    major = user_info.get('major')

    history = load_user_history(username)

    if query not in history:
        history.insert(0, query)  # 插入到最前面
    history = history[:MAX_HISTORY]  # 限制记录数量

    save_user_history(username, history, college, major)
    return jsonify({'success': True})

@history_bp.route('/delete_history', methods=['POST'])
def delete_history():
    """删除指定历史记录"""
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 403

    query = request.json.get('query')  # 获取要删除的查询内容
    if not query:
        return jsonify({'error': 'Invalid query'}), 400

    username = session['username']
    # 从 users.json 获取用户信息
    users_db = load_users()
    user_info = users_db.get(username, {})
    college = user_info.get('college')
    major = user_info.get('major')

    history = load_user_history(username)

    if query in history:
        history.remove(query)  # 删除该项
        save_user_history(username, history, college, major)
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Query not found in history'}), 404