#!/usr/bin/env python3
"""
ArXiv 文献自动总结系统

Usage:
    python main.py --scan                        # 仅扫描和总结论文
    python main.py --publish                     # 仅发布已总结的论文到知乎
    python main.py --run-once                    # 完整流程：扫描+总结+发布
    python main.py --daemon                      # 持续运行（定时任务）
    python main.py --paper 2401.12345            # 处理单篇论文
    python main.py --list                        # 列出已处理论文
    python main.py --stats                       # 显示统计信息
    python main.py --check-zhihu                 # 检查知乎登录状态
    python main.py --init-config                 # 生成配置文件模板
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

from dotenv import load_dotenv

from core import ArxivSurveySystem
from config import Config
from publisher import ZhihuPlaywrightPublisher
from models import ArxivPaper
from utils import get_logger, setup_logging, get_output_handler, get_log_level

logger = get_logger()

# 加载配置以获取输出设置
config = Config.from_yaml("config/config.yaml")
main_config = config.output.get_module_config("main")

# 转换日志级别
log_level = get_log_level(main_config.log_level)

output_handler = get_output_handler(
    "main", 
    logger, 
    debug=main_config.debug, 
    log_level=log_level, 
    enable_debug=main_config.enable_debug
)


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="ArXiv 文献自动总结系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --scan                          # 仅扫描和总结论文
  %(prog)s --publish                       # 仅发布已总结的论文到知乎
  %(prog)s --run-once                      # 完整流程：扫描+总结+发布
  %(prog)s --daemon                        # 后台定时运行
  %(prog)s --paper 2401.12345              # 处理指定论文
  %(prog)s --list --days 7                 # 列出最近7天处理的论文
  %(prog)s --stats                         # 显示统计信息
  %(prog)s --check-zhihu                   # 检查知乎登录状态
  %(prog)s --init-config                   # 生成配置文件模板
        """
    )
    
    # 运行模式（互斥）
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--scan",
        action="store_true",
        help="仅扫描和总结论文（不发布到知乎）"
    )
    mode_group.add_argument(
        "--publish",
        action="store_true",
        help="仅发布已总结的论文到知乎"
    )
    mode_group.add_argument(
        "--run-once",
        action="store_true",
        help="完整流程：扫描+总结+发布（默认）"
    )
    mode_group.add_argument(
        "--daemon",
        action="store_true",
        help="持续运行（定时任务模式）"
    )
    
    # 单篇论文处理
    parser.add_argument(
        "--paper",
        metavar="ARXIV_ID",
        help="处理指定arXiv ID的论文"
    )
    
    # 查询和管理
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出已处理的论文"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="显示存储统计信息"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="列出最近N天的论文（默认30天）"
    )
    
    # 知乎相关
    parser.add_argument(
        "--check-zhihu",
        action="store_true",
        help="检查知乎登录状态"
    )
    parser.add_argument(
        "--list-columns",
        action="store_true",
        help="列出知乎专栏"
    )
    
    # 配置
    parser.add_argument(
        "--config",
        metavar="PATH",
        default="config/config.yaml",
        help="配置文件路径（默认: config/config.yaml）"
    )
    
    # 其他选项
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细日志"
    )
    
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="生成配置文件模板"
    )
    
    return parser


def init_config():
    """生成配置文件模板"""
    config_template = '''# ArXiv 文献自动总结系统配置文件

arxiv:
  # 搜索关键词（OR关系）
  keywords:
    # - "你的关键词1"
    # - "你的关键词2"
  
  # arXiv分类（AND关系）
  categories:
    - "cs.LG"      # 机器学习
    - "cs.AI"      # 人工智能
  
  # 扫描最近N天的论文
  days_back: 7
  
  # 每次最大获取数量
  max_results: 50
  
  # 排序方式: submittedDate, lastUpdatedDate, relevance
  sort_by: "submittedDate"
  
  # 排序顺序: ascending, descending
  sort_order: "descending"

ai:
  # AI提供商: deepseek, openai, claude
  provider: "deepseek"
  
  # API密钥（支持环境变量语法: ${ENV_VAR_NAME}）
  api_key: "${DEEPSEEK_API_KEY}"
  
  # API地址
  api_url: "https://api.deepseek.com/v1/chat/completions"
  
  # 模型名称
  model: "deepseek-chat"
  
  # 温度参数 (0.0-1.0)
  temperature: 0.7
  
  # 最大token数
  max_tokens: 8000
  
  # 请求超时时间(秒)
  timeout: 300

storage:
  # 本地存储根目录
  base_dir: "./papers"
  
  # 存储格式: markdown, json
  format: "markdown"
  
  # 文件名模板: {date}, {arxiv_id}, {title}, {category}
  filename_template: "{date}_{arxiv_id}_{title}"
  
  # 组织方式: date, category, flat
  organize_by: "date"

zhihu:
  # 是否启用知乎发布
  enabled: true
  
  # 知乎Cookie
  cookie: "${ZHIHU_COOKIE}"
  
  # 知乎专栏名称
  column_name: "世界模型-arxiv预印本总结"
  
  # 专栏不存在时是否自动创建
  create_column_if_not_exists: false
  
  # 先保存为草稿
  draft_first: false
  
  # 是否自动发布（false则保存为草稿）
  auto_publish: true
  
  # 正文填充模式: copy_paste（拷贝粘贴）, import_document（导入文档）
  content_fill_mode: "copy_paste"
  
  # 调试模式: true（调试模式，输出详细日志和生成截图）, false（执行模式，简洁输出）
  debug: true

scheduler:
  # 是否启用定时任务
  enabled: true
  
  # Cron表达式 (分 时 日 月 周)
  # 每天上午9点: "0 9 * * *"
  # 每周一上午9点: "0 9 * * 1"
  cron: "0 9 * * *"
  
  # 时区
  timezone: "Asia/Shanghai"
'''
    
    config_path = "config/config.yaml"
    
    if os.path.exists(config_path):
        overwrite = input(f"配置文件 {config_path} 已存在，是否覆盖？(y/N): ")
        if overwrite.lower() != 'y':
            print("已取消")
            return
    
    os.makedirs("config", exist_ok=True)
    
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_template)
    
    print(f"配置文件已生成: {config_path}")
    print("\n请编辑配置文件，设置您的API密钥和Cookie:")
    print("  1. 设置 DEEPSEEK_API_KEY 环境变量")
    print("  2. 设置 ZHIHU_COOKIE 环境变量")
    print("  3. 或直接在配置文件中填写")


def check_environment():
    """检查环境配置"""
    # 加载.env文件
    load_dotenv()
    
    required_vars = []
    
    # 检查DeepSeek API密钥
    if not os.getenv("DEEPSEEK_API_KEY"):
        logger.warning("未设置 DEEPSEEK_API_KEY 环境变量")
        required_vars.append("DEEPSEEK_API_KEY")
    
    # 检查知乎Cookie
    if not os.getenv("ZHIHU_COOKIE"):
        logger.warning("未设置 ZHIHU_COOKIE 环境变量")
        required_vars.append("ZHIHU_COOKIE")
    
    if required_vars:
        logger.info("可以设置这些环境变量或使用 config.yaml")
    
    return len(required_vars) == 0


def get_unpublished_papers(storage) -> List[Dict]:
    """
    获取所有未发布的论文
    
    Returns:
        未发布论文列表
    """
    unpublished = []
    base_dir = Path(storage.config.base_dir)
    
    # 遍历所有年-月文件夹
    for folder in base_dir.iterdir():
        if folder.is_dir():
            brief_file = folder / "brief.json"
            if brief_file.exists():
                try:
                    import json
                    with open(brief_file, 'r', encoding='utf-8') as f:
                        brief = json.load(f)
                    
                    for arxiv_id, paper_info in brief.get("papers", {}).items():
                        zhihu_published = paper_info.get("zhihu_published", False)
                        zhihu_url = paper_info.get("zhihu_article_url")
                        
                        if not zhihu_published or not zhihu_url:
                            unpublished.append({
                                "arxiv_id": arxiv_id,
                                "title": paper_info.get("title", ""),
                                "authors": paper_info.get("authors", []),
                                "published_date": paper_info.get("published_date", ""),
                                "primary_category": paper_info.get("primary_category", ""),
                                "file_path": paper_info.get("file_path", ""),
                                "folder": folder.name
                            })
                except Exception as e:
                    logger.warning(f"读取 {brief_file} 失败: {e}")
    
    return unpublished


def publish_papers_to_zhihu(config: Config, papers: List[Dict]) -> Dict:
    """
    将论文发布到知乎专栏（顺序执行，Playwright sync模式）
    
    Args:
        config: 配置对象
        papers: 论文列表
        
    Returns:
        发布结果统计
    """
    if not papers:
        output_handler.info("[成功] 没有需要发布的论文")
        return {"success": 0, "failed": 0, "total": 0}
    
    output_handler.info(f"\n[警告] 找到 {len(papers)} 篇未发布的论文")
    output_handler.info(f"   目标专栏: {config.zhihu.column_name}")
    
    # 创建发布器
    output_handler.info("\n初始化知乎发布器...")
    publisher = ZhihuPlaywrightPublisher(config.zhihu)
    
    # 检查知乎登录
    output_handler.info("检查知乎登录状态...")
    if not publisher.check_login():
        output_handler.error("[错误] 知乎登录失败，请检查cookie")
        return {"success": 0, "failed": len(papers), "total": len(papers)}
    output_handler.info("[成功] 知乎登录成功")
    
    success_count = 0
    failed_count = 0
    base_dir = Path(config.storage.base_dir)
    
    # 发布每篇论文（顺序执行）
    for i, paper_info in enumerate(papers, 1):
        arxiv_id = paper_info["arxiv_id"]
        title = paper_info["title"]
        file_path = paper_info["file_path"]
        
        output_handler.info(f"\n[{i}/{len(papers)}] 发布论文: {title[:50]}...")
        output_handler.info(f"   arXiv ID: {arxiv_id}")
        
        try:
            # 检查文件路径
            if not file_path:
                output_handler.error(f"[错误] 论文文件路径不存在: {arxiv_id}")
                failed_count += 1
                continue
            
            # file_path 已经包含 "papers/" 前缀，直接使用
            full_path = Path(file_path)
            if not full_path.exists():
                # 尝试添加 base_dir 前缀
                full_path = base_dir / file_path
            if not full_path.exists():
                output_handler.error(f"[错误] 论文文件不存在: {full_path}")
                failed_count += 1
                continue
            
            # 创建论文对象
            published_date = datetime.fromisoformat(paper_info["published_date"].replace('Z', '+00:00')) if paper_info["published_date"] else datetime.now()
            
            paper = ArxivPaper(
                arxiv_id=arxiv_id,
                title=title,
                authors=paper_info["authors"],
                author_affiliations=[],
                abstract="",
                categories=[paper_info["primary_category"]] if paper_info["primary_category"] else [],
                primary_category=paper_info["primary_category"],
                published_date=published_date,
                pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                abs_url=f"https://arxiv.org/abs/{arxiv_id}",
                journal_ref=None,
                doi=None
            )
            
            # 发布到知乎（直接调用，不使用线程）
            article_url = publisher.publish_from_file(
                str(full_path),
                paper=paper,
                headless=False  # 显示浏览器窗口
            )
            
            if article_url:
                output_handler.info(f"[成功] 发布成功: {article_url}")
                success_count += 1
            else:
                output_handler.error(f"[错误] 发布失败")
                failed_count += 1
                
        except Exception as e:
            output_handler.error(f"[错误] 发布时出错: {e}")
            logger.error(f"发布论文 {arxiv_id} 时出错: {e}", exc_info=True)
            failed_count += 1
    
    return {"success": success_count, "failed": failed_count, "total": len(papers)}


def scan_and_summarize(system: ArxivSurveySystem) -> Dict:
    """
    扫描arXiv并总结论文
    
    Args:
        system: 系统实例
        
    Returns:
        扫描结果统计
    """
    output_handler.info("=" * 70)
    output_handler.info("步骤1: 扫描arXiv论文")
    output_handler.info("=" * 70)
    
    result = system.run_once()
    
    output_handler.info(f"\n扫描完成:")
    output_handler.info(f"  成功: {result.success}")
    output_handler.info(f"  失败: {result.failed}")
    output_handler.info(f"  跳过: {result.skipped}")
    
    return {
        "success": result.success,
        "failed": result.failed,
        "skipped": result.skipped
    }


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        setup_logging(log_level="DEBUG")
    else:
        setup_logging(log_level="INFO")
    
    # 生成配置文件
    if args.init_config:
        init_config()
        return 0
    
    # 检查环境
    check_environment()
    
    # 确定配置文件路径
    config_path = args.config if os.path.exists(args.config) else None
    
    # 加载配置
    try:
        config = Config.from_yaml(config_path) if config_path else Config.from_yaml("config/config.yaml")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        output_handler.error(f"错误: 加载配置文件失败 - {e}")
        return 1
    
    # 初始化系统
    try:
        system = ArxivSurveySystem(config_path if config_path else "config/config.yaml")
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        output_handler.error(f"错误: 系统初始化失败 - {e}")
        output_handler.info("请检查配置文件和环境变量设置")
        return 1
    
    # 执行命令
    try:
        if args.paper:
            # 处理单篇论文
            output_handler.info(f"\n处理单篇论文: {args.paper}")
            task = system.process_single_paper(args.paper)
            if task.is_successful():
                output_handler.info(f"论文处理成功: {task.arxiv_id}")
                if task.zhihu_url:
                    output_handler.info(f"  知乎链接: {task.zhihu_url}")
                if task.local_path:
                    output_handler.info(f"  本地文件: {task.local_path}")
            else:
                output_handler.error(f"论文处理失败: {task.arxiv_id}")
                if task.error_message:
                    output_handler.error(f"  错误: {task.error_message}")
                return 1
        
        elif args.list:
            # 列出已处理论文
            date_from = datetime.now() - timedelta(days=args.days)
            papers = system.list_processed_papers(date_from=date_from)
            
            output_handler.info(f"\n最近 {args.days} 天处理的论文 ({len(papers)} 篇):\n")
            output_handler.info(f"{'arXiv ID':<15} {'日期':<12} {'标题':<50}")
            output_handler.info("-" * 80)
            
            for p in papers:
                date_str = p["published_date"][:10]
                title = p["title"][:47] + "..." if len(p["title"]) > 50 else p["title"]
                output_handler.info(f"{p['arxiv_id']:<15} {date_str:<12} {title:<50}")
        
        elif args.stats:
            # 显示统计信息
            stats = system.get_storage_stats()
            
            output_handler.info("\n=== 存储统计 ===\n")
            output_handler.info(f"总论文数: {stats['total_papers']}")
            
            if stats['by_category']:
                output_handler.info("\n按分类统计:")
                for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
                    output_handler.info(f"  {cat}: {count}")
            
            if stats['by_year']:
                output_handler.info("\n按年份统计:")
                for year, count in sorted(stats['by_year'].items(), key=lambda x: -x[0]):
                    output_handler.info(f"  {year}: {count}")
        
        elif args.check_zhihu:
            # 检查知乎登录状态
            if system.check_zhihu_login():
                output_handler.info("知乎登录状态正常")
            else:
                output_handler.error("知乎未登录或Cookie已过期")
                output_handler.info("  请更新 ZHIHU_COOKIE 环境变量或配置文件")
                return 1
        
        elif args.list_columns:
            # 列出知乎专栏
            columns = system.get_zhihu_columns()
            if columns:
                output_handler.info("\n知乎专栏列表:\n")
                for col in columns:
                    output_handler.info(f"  ID: {col['id']}")
                    output_handler.info(f"  标题: {col['title']}")
                    output_handler.info(f"  描述: {col.get('description', 'N/A')}")
                    output_handler.info("")
            else:
                output_handler.info("未找到专栏或Cookie无效")
        
        elif args.daemon:
            # 持续运行模式
            output_handler.info("启动定时任务模式，按 Ctrl+C 停止")
            system.run_continuous()
        
        elif args.scan:
            # 仅扫描和总结
            output_handler.info("\n执行论文扫描和总结...")
            result = scan_and_summarize(system)
            
            output_handler.info("\n" + "=" * 70)
            output_handler.info("扫描和总结完成")
            output_handler.info("=" * 70)
            output_handler.info(f"成功: {result['success']}, 失败: {result['failed']}, 跳过: {result['skipped']}")
            
            if result['failed'] > 0:
                return 1
        
        elif args.publish:
            # 仅发布到知乎
            output_handler.info("\n执行知乎发布...")
            output_handler.info("=" * 70)
            output_handler.info("步骤2: 发布到知乎专栏")
            output_handler.info("=" * 70)
            
            # 获取未发布的论文
            unpublished = get_unpublished_papers(system.storage)
            
            # 发布到知乎
            result = publish_papers_to_zhihu(config, unpublished)
            
            output_handler.info("\n" + "=" * 70)
            output_handler.info("发布完成")
            output_handler.info("=" * 70)
            output_handler.info(f"成功: {result['success']}, 失败: {result['failed']}, 总计: {result['total']}")
            
            if result['failed'] > 0:
                return 1
        
        elif args.run_once:
            # 完整流程：扫描+总结+发布
            output_handler.info("\n执行完整流程：扫描+总结+发布...")
            
            # 步骤1: 扫描和总结
            scan_result = scan_and_summarize(system)
            
            if scan_result['success'] == 0 and scan_result['failed'] == 0:
                output_handler.info("\n没有新论文需要处理")
                return 0
            
            # 步骤2: 发布到知乎
            output_handler.info("\n" + "=" * 70)
            output_handler.info("步骤2: 发布到知乎专栏")
            output_handler.info("=" * 70)
            
            # 获取未发布的论文（包括刚刚总结的）
            unpublished = get_unpublished_papers(system.storage)
            
            # 发布到知乎
            publish_result = publish_papers_to_zhihu(config, unpublished)
            
            output_handler.info("\n" + "=" * 70)
            output_handler.info("完整流程执行完成")
            output_handler.info("=" * 70)
            output_handler.info(f"\n扫描总结: 成功 {scan_result['success']}, 失败 {scan_result['failed']}")
            output_handler.info(f"知乎发布: 成功 {publish_result['success']}, 失败 {publish_result['failed']}")
            
            if scan_result['failed'] > 0 or publish_result['failed'] > 0:
                return 1
        
        else:
            # 默认完整流程：扫描+总结+发布
            output_handler.info("\n执行完整流程：扫描+总结+发布...")
            
            # 步骤1: 扫描和总结
            scan_result = scan_and_summarize(system)
            
            if scan_result['success'] == 0 and scan_result['failed'] == 0:
                output_handler.info("\n没有新论文需要处理")
                return 0
            
            # 步骤2: 发布到知乎
            output_handler.info("\n" + "=" * 70)
            output_handler.info("步骤2: 发布到知乎专栏")
            output_handler.info("=" * 70)
            
            # 获取未发布的论文（包括刚刚总结的）
            unpublished = get_unpublished_papers(system.storage)
            
            # 发布到知乎
            publish_result = publish_papers_to_zhihu(config, unpublished)
            
            output_handler.info("\n" + "=" * 70)
            output_handler.info("完整流程执行完成")
            output_handler.info("=" * 70)
            output_handler.info(f"\n扫描总结: 成功 {scan_result['success']}, 失败 {scan_result['failed']}")
            output_handler.info(f"知乎发布: 成功 {publish_result['success']}, 失败 {publish_result['failed']}")
            
            if scan_result['failed'] > 0 or publish_result['failed'] > 0:
                return 1
    
    except KeyboardInterrupt:
        output_handler.info("\n操作已取消")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        output_handler.error(f"错误: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
