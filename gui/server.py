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
import atexit
import signal
import time
import platform
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

# 服务器实例ID（用于前端检测服务器重启）
SERVER_ID = str(time.time())

# PID文件路径
PID_FILE_PATH = BASE_DIR / "gui_server.pid"


class SingleInstanceManager:
    """单实例管理器 - 使用socket绑定+PID文件确保只有一个服务器实例运行"""
    
    def __init__(self, pid_file):
        self.pid_file = Path(pid_file)
        self.lock_socket = None
        self.locked = False
        
    def _try_bind_socket(self, lock_port):
        """尝试绑定socket端口用于单实例检查（使用单独的锁端口，不影响Flask）"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1)
            sock.bind(('127.0.0.1', lock_port))
            sock.listen(1)
            print(f"  成功绑定单实例锁端口 {lock_port}")
            return sock
        except socket.error as e:
            print(f"  绑定单实例锁端口 {lock_port} 失败: {e}")
            return None
    
    def _release_socket(self):
        """释放socket"""
        if self.lock_socket:
            try:
                self.lock_socket.close()
            except:
                pass
            self.lock_socket = None
    
    def _read_pid_file(self):
        """读取PID文件内容"""
        try:
            if self.pid_file.exists():
                with open(self.pid_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        parts = content.split(',')
                        if len(parts) >= 2:
                            return {
                                'pid': int(parts[0]),
                                'start_time': float(parts[1]),
                                'port': int(parts[2]) if len(parts) > 2 else 5000
                            }
        except Exception as e:
            print(f"读取PID文件时出错: {e}")
        return None
    
    def _write_pid_file(self, port=5000):
        """写入PID文件"""
        try:
            with open(self.pid_file, 'w', encoding='utf-8') as f:
                f.write(f"{os.getpid()},{time.time()},{port}")
        except Exception as e:
            print(f"写入PID文件时出错: {e}")
    
    def _is_process_running(self, pid):
        """检查进程是否仍在运行"""
        try:
            if platform.system() == 'Windows':
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(1, False, pid)
                if handle:
                    kernel32.CloseHandle(handle)
                    return True
                return False
            else:
                # Unix/Linux
                os.kill(pid, 0)
                return True
        except (OSError, ProcessLookupError):
            return False
    
    def _find_existing_server(self):
        """通过进程列表查找已运行的服务器实例"""
        try:
            import psutil
            current_pid = os.getpid()
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['pid'] == current_pid:
                        continue
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('gui/server.py' in str(arg) for arg in cmdline):
                        return {
                            'pid': proc.info['pid'],
                            'start_time': '未知',
                            'port': 5000,
                            'cmdline': ' '.join(str(arg) for arg in cmdline)
                        }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return None
        except ImportError:
            # psutil未安装，使用备用方法
            try:
                if platform.system() == 'Windows':
                    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'], 
                                          capture_output=True, text=True)
                    # 简单检查是否有其他python进程
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 2:  # 标题行 + 当前进程 + 其他进程
                        return {'pid': '未知', 'start_time': '未知', 'port': 5000}
            except:
                pass
            return None
    
    def ensure_single_instance(self, port=5000):
        """
        确保只有一个实例在运行
        使用单独的锁端口（port+1）进行单实例检查，不影响Flask绑定主端口
        返回: (success: bool, message: str)
        """
        lock_port = port + 1  # 使用5001作为锁端口
        
        # 首先尝试绑定锁端口（最可靠的检查）
        self.lock_socket = self._try_bind_socket(lock_port)
        
        if not self.lock_socket:
            # socket绑定失败，说明已有实例在运行
            # 尝试获取更多信息
            pid_info = self._read_pid_file()
            
            if not pid_info:
                # 无法读取PID，尝试通过进程列表查找
                pid_info = self._find_existing_server()
            
            if pid_info:
                existing_pid = pid_info.get('pid', '未知')
                
                # 检查进程是否仍在运行
                if isinstance(existing_pid, int) and self._is_process_running(existing_pid):
                    return False, (
                        f"GUI服务器已经在运行\n"
                        f"  PID: {existing_pid}\n"
                        f"  端口: {pid_info.get('port', port)}\n\n"
                        f"如需重新启动，请先终止现有实例：\n"
                        f"  Windows: taskkill /F /PID {existing_pid}\n"
                        f"  Linux/Mac: kill -9 {existing_pid}"
                    )
                else:
                    # 进程不存在，清理僵尸PID文件
                    print(f"警告：检测到僵尸PID文件（进程 {existing_pid} 已不存在）")
                    print("正在清理...")
                    try:
                        self.pid_file.unlink()
                    except:
                        pass
                    
                    # 重新尝试绑定socket
                    self.lock_socket = self._try_bind_socket(lock_port)
                    if not self.lock_socket:
                        return False, "锁端口仍被占用，可能有其他实例正在启动"
            else:
                return False, (
                    "检测到已有GUI服务器实例在运行\n"
                    "可能原因：\n"
                    "  1. 另一个GUI服务器实例正在运行\n"
                    "  2. 之前的实例异常退出，锁端口被占用\n\n"
                    f"请检查是否有其他python进程在运行gui/server.py\n"
                    f"  Windows: tasklist | findstr python\n"
                    f"  Linux/Mac: ps aux | grep 'gui/server.py'"
                )
        
        # 成功绑定socket，写入PID文件
        self.locked = True
        self._write_pid_file(port)
        
        # 注册清理函数
        atexit.register(self.cleanup)
        
        return True, "成功获取单实例锁"
    
    def cleanup(self):
        """清理资源"""
        if self.locked:
            print("\n正在清理单实例锁...")
            self._release_socket()
            self.locked = False
        
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
                print("PID文件已清理")
        except:
            pass


# 创建单实例管理器
single_instance_manager = SingleInstanceManager(PID_FILE_PATH)


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
    global is_processing, current_process, SERVER_ID
    return jsonify({
        'is_processing': is_processing,
        'has_process': current_process is not None,
        'server_id': SERVER_ID
    })


@app.route('/api/stop', methods=['POST'])
def stop_process():
    """停止当前处理进程"""
    global current_process, is_processing
    
    if not current_process:
        return jsonify({'error': '没有正在运行的处理进程'}), 400
    
    try:
        import psutil
        import signal
        
        parent = psutil.Process(current_process.pid)
        children = parent.children(recursive=True)
        
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        
        try:
            current_process.terminate()
            current_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            for child in children:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            try:
                current_process.kill()
                current_process.wait(timeout=5)
            except:
                pass
        except Exception:
            pass
        
        is_processing = False
        current_process = None
        return jsonify({'status': 'ok'})
    except ImportError:
        try:
            current_process.terminate()
            current_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            current_process.kill()
            current_process.wait(timeout=5)
        except Exception:
            pass
        
        is_processing = False
        current_process = None
        return jsonify({'status': 'ok'})
    except Exception as e:
        is_processing = False
        current_process = None
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


def signal_handler(signum, frame):
    """信号处理函数"""
    print(f"\n接收到信号 {signum}，正在关闭服务器...")
    single_instance_manager.cleanup()
    sys.exit(0)


if __name__ == '__main__':
    print("=" * 60)
    print("ArXiv文献自动总结系统GUI服务器")
    print("=" * 60)
    print(f"基础目录：{BASE_DIR}")
    print(f"配置路径：{CONFIG_PATH}")
    print(f"论文目录：{PAPERS_DIR}")
    print(f"调试模式：{app.debug}")
    print(f"端口设置：5000")
    print("-" * 60)
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    if hasattr(signal, 'SIGBREAK'):  # Windows
        signal.signal(signal.SIGBREAK, signal_handler)
    
    # 检查单实例
    print("\n检查单实例...")
    success, message = single_instance_manager.ensure_single_instance(port=5000)
    if not success:
        print("\n" + "=" * 60)
        print("错误：无法启动服务器")
        print("=" * 60)
        print(message)
        print("=" * 60)
        sys.exit(1)
    
    print(message)
    print(f"当前进程PID: {os.getpid()}")
    print("-" * 60)
    
    print("\n访问GUI界面：http://localhost:5000")
    print("按Ctrl+C停止服务器\n")
    
    # 明确禁用debug模式并设置端口为5000
    print("正在启动服务器...")
    try:
        app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
    finally:
        # 确保清理
        single_instance_manager.cleanup()
