#!/usr/bin/env python3
"""
ArXiv文献自动总结系统 - 简易GUI后端
提供API接口供前端调用
"""

import os
import sys
import json
import yaml
import subprocess
import socket
from pathlib import Path
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 获取GUI目录
GUI_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = GUI_DIR.parent

app = Flask(__name__, static_folder=str(GUI_DIR), static_url_path='')
CORS(app)

# 禁用debug模式
app.debug = False

# 配置路径
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"
PAPERS_DIR = BASE_DIR / "papers"

# 全局状态变量
current_process = None
is_processing = False


def check_single_instance(port=5000):
    """检查是否只有一个实例在运行"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        sock.bind(('127.0.0.1', port))
        sock.close()
        return True
    except socket.error:
        return False


@app.route('/')
def index():
    """主页 - 返回index.html"""
    return app.send_static_file('index.html')


@app.route('/api/run', methods=['POST'])
def run_main():
    """执行main.py命令"""
    global current_process, is_processing
    
    # 检查是否已有进程在运行
    if is_processing:
        return jsonify({'error': '处理任务已在运行中，请等待完成后再启动新任务'}), 400
    
    data = request.json
    args = data.get('args', [])
    
    try:
        # 构建命令
        cmd = [sys.executable, str(BASE_DIR / "main.py")] + args
        
        # 设置环境变量，确保UTF-8编码
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['LANG'] = 'en_US.UTF-8'
        env['LC_ALL'] = 'en_US.UTF-8'
        
        # 标记为处理中
        is_processing = True
        
        # 启动进程
        current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=str(BASE_DIR),
            env=env,
            bufsize=0  # 禁用缓冲，确保实时输出
        )
        
        def generate():
            global is_processing, current_process
            try:
                for line in current_process.stdout:
                    yield line
                current_process.wait()
            finally:
                # 处理完成，重置状态
                is_processing = False
                current_process = None
        
        return Response(generate(), mimetype='text/plain')
    
    except Exception as e:
        # 发生错误，重置状态
        is_processing = False
        current_process = None
        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    """读取或保存配置"""
    if request.method == 'GET':
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return jsonify(config)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    else:  # POST
        try:
            config = request.json
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, sort_keys=False)
            return jsonify({'status': 'ok'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/api/config/ai', methods=['GET', 'POST'])
def handle_ai_config():
    """AI配置管理（包含提示词和章节定义）"""
    if request.method == 'GET':
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return jsonify(config.get('ai', {}))
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    else:  # POST
        try:
            ai_config = request.json
            
            # 读取现有配置
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            # 更新AI配置
            config['ai'] = ai_config
            
            # 保存配置
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, sort_keys=False)
            
            return jsonify({'status': 'ok'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/api/config/ai/sections', methods=['GET', 'POST'])
def handle_summary_sections():
    """章节定义管理"""
    if request.method == 'GET':
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return jsonify(config.get('ai', {}).get('summary_sections', []))
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    else:  # POST
        try:
            # 直接获取请求体作为章节数组
            sections = request.json
            
            # 读取现有配置
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            # 确保ai配置存在
            if 'ai' not in config:
                config['ai'] = {}
            
            # 更新章节定义
            config['ai']['summary_sections'] = sections
            
            # 保存配置
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, sort_keys=False)
            
            return jsonify({'status': 'ok'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/api/papers', methods=['GET'])
def get_papers():
    """获取所有论文列表"""
    try:
        papers = []
        
        if not PAPERS_DIR.exists():
            return jsonify(papers)
        
        for folder in PAPERS_DIR.iterdir():
            if folder.is_dir():
                brief_file = folder / "brief.json"
                if brief_file.exists():
                    try:
                        with open(brief_file, 'r', encoding='utf-8') as f:
                            brief = json.load(f)
                            for arxiv_id, paper_info in brief.get('papers', {}).items():
                                paper_info['arxiv_id'] = arxiv_id
                                paper_info['folder'] = folder.name
                                papers.append(paper_info)
                    except Exception as e:
                        print(f"读取 {brief_file} 失败: {e}")
        
        # 按日期排序（最新的在前）
        papers.sort(key=lambda x: x.get('published_date', ''), reverse=True)
        
        return jsonify(papers)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取系统统计信息"""
    try:
        papers = []
        
        if PAPERS_DIR.exists():
            for folder in PAPERS_DIR.iterdir():
                if folder.is_dir():
                    brief_file = folder / "brief.json"
                    if brief_file.exists():
                        try:
                            with open(brief_file, 'r', encoding='utf-8') as f:
                                brief = json.load(f)
                                papers.extend(brief.get('papers', {}).values())
                        except Exception as e:
                            print(f"读取 {brief_file} 失败: {e}")
        
        total = len(papers)
        published = sum(1 for p in papers if p.get('zhihu_published') and p.get('zhihu_article_url'))
        unpublished = total - published
        
        # 按分类统计
        by_category = {}
        for p in papers:
            cat = p.get('primary_category', 'unknown')
            by_category[cat] = by_category.get(cat, 0) + 1
        
        return jsonify({
            'total': total,
            'published': published,
            'unpublished': unpublished,
            'by_category': by_category
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/check-zhihu', methods=['GET'])
def check_zhihu():
    """检查知乎登录状态"""
    try:
        cmd = [sys.executable, str(BASE_DIR / "main.py"), '--check-zhihu']
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(BASE_DIR),
            timeout=30
        )
        
        # 根据返回码判断登录状态
        is_logged_in = result.returncode == 0
        
        return jsonify({
            'logged_in': is_logged_in,
            'output': result.stdout + result.stderr
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """获取处理状态"""
    global is_processing, current_process
    return jsonify({
        'is_processing': is_processing,
        'has_process': current_process is not None
    })


@app.route('/api/stop', methods=['POST'])
def stop_process():
    """停止当前处理进程"""
    global current_process, is_processing
    
    if not current_process:
        return jsonify({'error': '没有正在运行的处理进程'}), 400
    
    try:
        # 发送终止信号
        current_process.terminate()
        # 等待进程结束
        current_process.wait(timeout=10)
        # 重置状态
        is_processing = False
        current_process = None
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config/output', methods=['GET', 'POST'])
def handle_output_config():
    """输出配置管理"""
    if request.method == 'GET':
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return jsonify(config.get('output', {}))
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    else:  # POST
        try:
            output_config = request.json
            
            # 读取现有配置
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            # 更新输出配置
            config['output'] = output_config
            
            # 保存配置
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, sort_keys=False)
            
            return jsonify({'status': 'ok'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("启动ArXiv文献自动总结系统GUI服务器...")
    print(f"基础目录：{BASE_DIR}")
    print(f"配置路径：{CONFIG_PATH}")
    print(f"论文目录：{PAPERS_DIR}")
    print(f"调试模式：{app.debug}")
    print(f"端口设置：5000")
    print("\n访问GUI界面：http://localhost:5000")
    print("按Ctrl+C停止服务器\n")
    
    # 检查单实例
    if not check_single_instance(port=5000):
        print("错误：GUI服务器已经在运行（端口5000被占用）")
        print("请关闭已运行的实例后再启动")
        sys.exit(1)
    
    # 明确禁用debug模式并设置端口为5000
    print("正在启动服务器...")
    app.run(debug=False, host='0.0.0.0', port=5000)
