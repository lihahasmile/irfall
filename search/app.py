from flask import Flask, render_template, request, jsonify, make_response, redirect, url_for, session
from elasticsearch import Elasticsearch
from datetime import datetime, timedelta
import json
from routes.history import history_bp
from routes.search import search_bp
from routes.personal import personal_bp
import os

app = Flask(__name__)

# 设置数据库配置
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = timedelta(days=30)  # 设置会话过期时间
# 假设用户数据库是一个字典，实际应用中请使用数据库
USER_DATA_FILE = 'users.json'

# # 创建 Elasticsearch 客户端连接
# es = Elasticsearch("http://localhost:9200")

# 读取用户信息
def load_users():
    users = {}
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as file:
            try:
                users = json.load(file)  # 读取并返回用户数据字典
            except json.JSONDecodeError:
                users = {}  # 如果文件为空或格式错误，返回空字典
    return users

# 保存用户信息
def save_user(username, password, college, major):
    user_info = {
        'username': username,
        'password': password,
        'college': college,
        'major': major
    }

    users_db = load_users()  # 加载现有用户数据

    # 如果用户已存在，更新用户信息；如果用户不存在，添加新用户
    users_db[username] = user_info

    # 保存更新后的用户数据到文件
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as file:
        json.dump(users_db, file, ensure_ascii=False, indent=4)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    college = data.get('college')
    major = data.get('major')
    users_db = load_users()
    if username in users_db:
        return jsonify({'success': False, 'message': '用户已存在'})
    
    save_user(username, password, college, major)  # 保存用户
    return jsonify({'success': True, 'message': '注册成功'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    users_db = load_users()

    if username in users_db and users_db[username]['password'] == password:
        session['username'] = username  # 存储会话
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': '用户名或密码错误'})

@app.route('/logout')
def logout():
    session.pop('username', None)  # 清除会话
    return redirect(url_for('index'))

@app.route('/search')
def search():
    if 'username' not in session:
        return redirect(url_for('index'))  # 未登录时跳转到登录页面
    # 在此处实现搜索功能
    return render_template('index.html')  # 返回搜索页面

@app.route('/')
def index():
    """渲染前端页面"""
    if 'username' in session:
        return redirect(url_for('search'))  # 如果已经登录，跳转到搜索页面
    return render_template('log.html')  # 否则显示登录/注册页面

# 注册蓝图并设置 URL 前缀
app.register_blueprint(history_bp, url_prefix='/history')
app.register_blueprint(search_bp, url_prefix='/search')

app.register_blueprint(personal_bp, url_prefix='/personal')

if __name__ == '__main__':
    app.run(debug=True)
