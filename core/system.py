import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from config import Config, ArxivConfig, AIConfig, StorageConfig, ZhihuConfig, SchedulerConfig
from models import ArxivPaper, PaperSummary, PaperTask, TaskStatus
from scanner import ArxivScanner, PDFExtractor
from summarizer import PaperSummarizer
from storage import PaperStorage
from publisher import ZhihuPlaywrightPublisher
from scheduler import TaskScheduler
from utils import get_logger, setup_logging, BatchProgress, PaperProgress, print_header

logger = get_logger()


@dataclass
class ProcessingResult:
    """处理结果"""
    success: int
    failed: int
    skipped: int
    tasks: List[PaperTask]


class ArxivSurveySystem:
    """文献总结系统主控制器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化系统
        
        Args:
            config_path: 配置文件路径，None则使用环境变量
        """
        # 设置日志
        setup_logging()
        
        # 加载配置
        if config_path and os.path.exists(config_path):
            self.config = Config.from_yaml(config_path)
            logger.info(f"从 {config_path} 加载配置")
            # 环境变量覆盖YAML配置
            self._apply_env_overrides()
        else:
            self.config = Config.from_env()
            logger.info("从环境变量加载配置")
    
    def _apply_env_overrides(self):
        """应用环境变量覆盖配置"""
        import os
        
        # 知乎配置覆盖
        if os.getenv("ZHIHU_ENABLED"):
            self.config.zhihu.enabled = os.getenv("ZHIHU_ENABLED", "true").lower() == "true"
            logger.info(f"从环境变量覆盖 zhihu.enabled: {self.config.zhihu.enabled}")
        
        if os.getenv("ZHIHU_COOKIE"):
            self.config.zhihu.cookie = os.getenv("ZHIHU_COOKIE", "")
            logger.info("从环境变量覆盖 zhihu.cookie")
        
        # DeepSeek API密钥覆盖
        if os.getenv("DEEPSEEK_API_KEY"):
            self.config.ai.api_key = os.getenv("DEEPSEEK_API_KEY", "")
            logger.info("从环境变量覆盖 ai.api_key")
        
        # 初始化组件
        self.scanner = ArxivScanner(self.config.arxiv)
        self.summarizer = PaperSummarizer(self.config.ai)
        self.storage = PaperStorage(self.config.storage)
        self.publisher = ZhihuPlaywrightPublisher(self.config.zhihu)
        self.scheduler = TaskScheduler(self.config.scheduler)
        
        # PDF临时目录
        self.temp_dir = Path("./temp")
        self.temp_dir.mkdir(exist_ok=True)
        
        # 检查知乎登录状态（如果启用）
        if self.config.zhihu.enabled:
            self._check_zhihu_login()
    
    def _check_zhihu_login(self):
        """
        检查知乎登录状态
        """
        if self.publisher.check_login():
            logger.info("知乎登录成功，可以发布")
        else:
            logger.warning("知乎登录失败，发布功能可能无法使用")
    
    def run_once(self) -> ProcessingResult:
        """
        执行一次完整的扫描-总结-发布流程
        
        Returns:
            处理结果
        """
        print_header("ArXiv 文献自动总结系统 - 单次运行")
        logger.info("=" * 60)
        logger.info("启动ArXiv文献自动总结系统 - 单次运行")
        logger.info("=" * 60)
        
        # 1. 扫描论文
        print("\n🔍 步骤 1: 扫描 arXiv 论文...")
        logger.info("步骤 1: 扫描arXiv论文...")
        papers = self.scanner.search_recent_papers()
        
        if not papers:
            print("❌ 没有找到新论文")
            logger.info("没有找到新论文")
            return ProcessingResult(0, 0, 0, [])
        
        print(f"✅ 找到 {len(papers)} 篇论文待处理")
        logger.info(f"找到 {len(papers)} 篇论文待处理")
        
        # 2. 处理每篇论文
        batch_progress = BatchProgress(len(papers))
        tasks = []
        
        for paper in papers:
            task = self._create_task(paper)
            tasks.append(task)
            
            # 检查是否在最近两个月内已处理（通过简报检查）
            if self.storage.exists_in_recent_months(paper.arxiv_id, months=2):
                # 获取已存在的信息
                existing_info = self.storage.get_paper_summary_info(paper.arxiv_id, months=2)
                folder_info = f" (位于 {existing_info['folder']} 文件夹)" if existing_info else ""
                print(f"⏭️  跳过已总结的论文: {paper.arxiv_id}{folder_info}")
                logger.info(f"跳过已总结的论文: {paper.arxiv_id}{folder_info}")
                task.update_status(TaskStatus.SKIPPED)
                batch_progress.mark_skipped()
                continue
            
            # 检查全局是否已处理（向后兼容）
            if self.storage.exists(paper.arxiv_id):
                print(f"⏭️  跳过已处理的论文: {paper.arxiv_id}")
                logger.info(f"跳过已处理的论文: {paper.arxiv_id}")
                task.update_status(TaskStatus.SKIPPED)
                batch_progress.mark_skipped()
                continue
            
            # 执行任务
            batch_progress.start_paper(paper.arxiv_id, paper.title)
            try:
                self._execute_task_with_progress(task, batch_progress)
                batch_progress.mark_success()
            except Exception as e:
                print(f"❌ 处理论文 {paper.arxiv_id} 时出错: {e}")
                logger.error(f"处理论文 {paper.arxiv_id} 时出错: {e}")
                task.update_status(TaskStatus.FAILED, str(e))
                batch_progress.mark_failed()
        
        # 3. 统计结果
        success = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED)
        skipped = sum(1 for t in tasks if t.status == TaskStatus.SKIPPED)
        
        batch_progress.show_summary()
        
        logger.info("=" * 60)
        logger.info("处理完成")
        logger.info(f"  成功: {success}")
        logger.info(f"  失败: {failed}")
        logger.info(f"  跳过: {skipped}")
        logger.info("=" * 60)
        
        return ProcessingResult(success, failed, skipped, tasks)
    
    def run_continuous(self):
        """持续运行，按配置定时执行"""
        if not self.config.scheduler.enabled:
            logger.warning("配置中禁用了调度器")
            return
        
        logger.info("=" * 60)
        logger.info("启动ArXiv文献自动总结系统 - 持续运行模式")
        logger.info(f"调度计划: {self.config.scheduler.cron}")
        logger.info("=" * 60)
        
        # 设置定时任务
        self.scheduler.schedule_cron_task(
            self.config.scheduler.cron,
            self.run_once
        )
        
        # 启动调度器
        try:
            self.scheduler.start(block=True)
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在停止...")
            self.scheduler.stop()
    
    def process_single_paper(self, arxiv_id: str) -> PaperTask:
        """
        处理单篇论文
        
        Args:
            arxiv_id: arXiv ID
            
        Returns:
            处理任务
        """
        logger.info(f"处理单篇论文: {arxiv_id}")
        
        # 获取论文信息
        paper = self.scanner.get_paper_by_id(arxiv_id)
        if not paper:
            task = PaperTask(
                task_id=str(uuid.uuid4()),
                arxiv_id=arxiv_id,
                status=TaskStatus.FAILED,
                error_message="Paper not found on arXiv"
            )
            return task
        
        # 创建并执行任务
        task = self._create_task(paper)
        self._execute_task(task)
        
        return task
    
    def _create_task(self, paper: ArxivPaper) -> PaperTask:
        """创建处理任务"""
        return PaperTask(
            task_id=str(uuid.uuid4()),
            arxiv_id=paper.arxiv_id,
            paper=paper
        )
    
    def _execute_task(self, task: PaperTask) -> PaperTask:
        """
        执行单个任务
        
        Args:
            task: 处理任务
            
        Returns:
            更新后的任务
        """
        paper = task.paper
        if not paper:
            task.update_status(TaskStatus.FAILED, "Paper info is missing")
            return task
        
        try:
            # 1. 下载PDF
            logger.info(f"[{paper.arxiv_id}] 步骤 1/5: 下载PDF...")
            task.update_status(TaskStatus.DOWNLOADING)
            
            pdf_path = self.temp_dir / f"{paper.arxiv_id.replace('/', '_')}.pdf"
            
            if not self.scanner.download_pdf(paper, str(pdf_path)):
                raise RuntimeError("Failed to download PDF")
            
            # 2. 提取文本
            logger.info(f"[{paper.arxiv_id}] 步骤 2/5: 从PDF提取文本...")
            
            extractor = PDFExtractor()
            content = extractor.extract_text(str(pdf_path))
            
            if not content:
                raise RuntimeError("Failed to extract text from PDF")
            
            logger.info(f"[{paper.arxiv_id}] 提取了 {len(content)} 个字符")
            
            # 3. AI总结
            logger.info(f"[{paper.arxiv_id}] 步骤 3/5: 使用AI生成总结...")
            task.update_status(TaskStatus.SUMMARIZING)
            
            summary = self.summarizer.summarize(paper, content)
            task.summary = summary
            
            # 4. 保存到本地
            logger.info(f"[{paper.arxiv_id}] 步骤 4/5: 保存到本地存储...")
            task.update_status(TaskStatus.STORING)
            
            file_path = self.storage.save_summary(summary, paper)
            task.local_path = file_path
            
            # 5. 发布到知乎
            if self.config.zhihu.enabled:
                logger.info(f"[{paper.arxiv_id}] 步骤 5/5: 发布到知乎...")
                task.update_status(TaskStatus.PUBLISHING)
                
                zhihu_url = self.publisher.publish(summary, paper)
                if zhihu_url:
                    task.zhihu_url = zhihu_url
                    logger.info(f"[{paper.arxiv_id}] 已发布到知乎: {zhihu_url}")
                else:
                    logger.warning(f"[{paper.arxiv_id}] 发布到知乎失败")
            else:
                logger.info(f"[{paper.arxiv_id}] 步骤 5/5: 知乎发布已禁用")
            
            # 完成任务
            task.update_status(TaskStatus.COMPLETED)
            logger.info(f"[{paper.arxiv_id}] 任务完成")
            
            # 清理临时文件
            if pdf_path.exists():
                pdf_path.unlink()
            
        except Exception as e:
            logger.error(f"[{paper.arxiv_id}] 任务失败: {e}")
            task.update_status(TaskStatus.FAILED, str(e))
        
        return task
    
    def _execute_task_with_progress(self, task: PaperTask, batch_progress: BatchProgress) -> PaperTask:
        """
        执行单个任务（带进度显示）
        
        Args:
            task: 处理任务
            batch_progress: 批量进度显示
            
        Returns:
            更新后的任务
        """
        paper = task.paper
        if not paper:
            task.update_status(TaskStatus.FAILED, "Paper info is missing")
            return task
        
        progress = PaperProgress(paper.arxiv_id)
        
        try:
            # 1. 下载PDF
            progress.start_step(1, "下载PDF")
            task.update_status(TaskStatus.DOWNLOADING)
            
            pdf_path = self.temp_dir / f"{paper.arxiv_id.replace('/', '_')}.pdf"
            
            if not self.scanner.download_pdf(paper, str(pdf_path)):
                raise RuntimeError("Failed to download PDF")
            
            progress.complete_step(f"PDF已保存到 {pdf_path}")
            
            # 2. 提取文本
            progress.start_step(2, "提取文本")
            
            extractor = PDFExtractor()
            content = extractor.extract_text(str(pdf_path))
            
            if not content:
                raise RuntimeError("Failed to extract text from PDF")
            
            progress.complete_step(f"提取了 {len(content)} 个字符")
            
            # 3. AI总结
            progress.start_step(3, "AI总结")
            task.update_status(TaskStatus.SUMMARIZING)
            
            summary = self.summarizer.summarize(paper, content)
            task.summary = summary
            
            progress.complete_step(f"使用模型 {summary.ai_model} 生成总结")
            
            # 4. 保存到本地
            progress.start_step(4, "保存本地")
            task.update_status(TaskStatus.STORING)
            
            file_path = self.storage.save_summary(summary, paper)
            task.local_path = file_path
            
            progress.complete_step(f"已保存到 {file_path}")
            
            # 5. 发布到知乎
            if self.config.zhihu.enabled:
                progress.start_step(5, "发布知乎")
                task.update_status(TaskStatus.PUBLISHING)
                
                zhihu_url = self.publisher.publish(summary, paper)
                if zhihu_url:
                    task.zhihu_url = zhihu_url
                    progress.complete_step(f"已发布到知乎: {zhihu_url}")
                else:
                    progress.warning("发布到知乎失败")
            else:
                progress.info("知乎发布已禁用")
            
            # 完成任务
            task.update_status(TaskStatus.COMPLETED)
            progress.info("✅ 任务完成")
            
            # 清理临时文件
            if pdf_path.exists():
                pdf_path.unlink()
            
        except Exception as e:
            progress.error(f"任务失败: {e}")
            logger.error(f"[{paper.arxiv_id}] 任务失败: {e}")
            task.update_status(TaskStatus.FAILED, str(e))
        
        return task
    
    def check_zhihu_login(self) -> bool:
        """检查知乎登录状态"""
        return self.publisher.check_login()
    
    def get_zhihu_columns(self) -> list:
        """获取知乎专栏列表"""
        return self.publisher.get_columns()
    
    def get_storage_stats(self) -> dict:
        """获取存储统计"""
        return self.storage.get_stats()
    
    def list_processed_papers(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> list:
        """
        列出已处理的论文
        
        Args:
            date_from: 起始日期
            date_to: 结束日期
            
        Returns:
            论文信息列表
        """
        return self.storage.list_summaries(date_from, date_to)
    
    def list_recent_summaries(self, months: int = 2) -> list:
        """
        列出最近N个月的总结
        
        Args:
            months: 月数
            
        Returns:
            总结信息列表
        """
        return self.storage.list_recent_summaries(months)
    
    def get_folder_brief(self, folder_name: str) -> Optional[dict]:
        """
        获取指定文件夹的简报
        
        Args:
            folder_name: 文件夹名称 (YYYY-MM)
            
        Returns:
            简报内容
        """
        return self.storage.get_folder_brief(folder_name)
    
    def check_paper_exists_in_recent_months(self, arxiv_id: str, months: int = 2) -> bool:
        """
        检查论文是否在最近N个月内已总结
        
        Args:
            arxiv_id: arXiv ID
            months: 检查的月数
            
        Returns:
            是否已总结
        """
        return self.storage.exists_in_recent_months(arxiv_id, months)
