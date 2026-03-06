#!/usr/bin/env python3
"""
简单的GUI服务器启动脚本
"""

import os
import sys
import socket
from flask import Flask, request, jsonify

# 创建Flask应用
app = Flask(__name__)

# 禁用调试模式
app.debug = False

# 测试路由
@app.route('/')
def index():
    return "GUI服务器测试页面"

@app.route('/api/test')
def test():
    return jsonify({'message': '测试成功'})

# 检查端口是否被占用
def check_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        sock.bind(('127.0.0.1', port))
        sock.close()
        return True
    except socket.error:
        return False

if __name__ == '__main__':
    port = 5006
    
    if check_port(port):
        print(f"启动服务器在端口 {port}...")
        print(f"访问地址：http://localhost:{port}")
        app.run(debug=False, host='0.0.0.0', port=port)
    else:
        print(f"端口 {port} 已被占用")
        sys.exit(1)
