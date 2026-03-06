#!/usr/bin/env python3
"""
启动GUI服务器的脚本
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from gui.server import app, BASE_DIR, CONFIG_PATH, PAPERS_DIR, check_single_instance
    
    print("启动ArXiv文献自动总结系统GUI服务器...")
    print(f"基础目录：{BASE_DIR}")
    print(f"配置路径：{CONFIG_PATH}")
    print(f"论文目录：{PAPERS_DIR}")
    print(f"调试模式：{app.debug}")
    print(f"端口设置：5006")
    print("\n访问GUI界面：http://localhost:5006")
    print("按Ctrl+C停止服务器\n")
    
    # 检查单实例
    if not check_single_instance(port=5006):
        print("错误：GUI服务器已经在运行（端口5006被占用）")
        print("请关闭已运行的实例后再启动")
        sys.exit(1)
    
    # 明确禁用debug模式并设置端口为5006
    print("正在启动服务器...")
    app.run(debug=False, host='0.0.0.0', port=5006)
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
