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
from utils import get_logger, setup_logging, BatchProgress, PaperProgress, print_header, get_output_handler, get_log_level
from utils.exceptions import APIError, APIKeyError, ZhihuLoginError, ZhihuCookieError, ZhihuPublishError

logger = get_logger()

output_handler = None  # 延迟初始化


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
        global output_handler
        # 设置日志
        setup_logging()
        
        # 加载配置
        if config_path and os.path.exists(config_path):
            self.config = Config.from_yaml(config_path)
            # 初始化输出处理器
            core_config = self.config.output.get_module_config("core")
            log_level = get_log_level(core_config.log_level)
            output_handler = get_output_handler(
                "core", 
                logger, 
                debug=core_config.debug, 
                log_level=log_level, 
                enable_debug=core_config.enable_debug
            )
            output_handler.info(f"从 {config_path} 加载配置")
            # 环境变量覆盖YAML配置
            self._apply_env_overrides()
        else:
            self.config = Config.from_env()
            # 初始化输出处理器
            core_config = self.config.output.get_module_config("core")
            log_level = get_log_level(core_config.log_level)
            output_handler = get_output_handler(
                "core", 
                logger, 
                debug=core_config.debug, 
                log_level=log_level, 
                enable_debug=core_config.enable_debug
            )
            output_handler.info("从环境变量加载配置")
    
    def _apply_env_overrides(self):
        """应用环境变量覆盖配置"""
        global output_handler
        import os
        
        # 知乎配置覆盖
        if os.getenv("ZHIHU_ENABLED"):
            self.config.zhihu.enabled = os.getenv("ZHIHU_ENABLED", "true").lower() == "true"
            output_handler.info(f"从环境变量覆盖 zhihu.enabled: {self.config.zhihu.enabled}")
        
        # Cookie处理：优先使用环境变量，如果配置文件使用占位符格式则解析
        if os.getenv("ZHIHU_COOKIE"):
            old_cookie = self.config.zhihu.cookie
            self.config.zhihu.cookie = os.getenv("ZHIHU_COOKIE", "")
            # 只显示Cookie的前10个字符和后10个字符，保护敏感信息
            old_display = old_cookie[:10] + "..." + old_cookie[-10:] if old_cookie and not old_cookie.startswith("${") else "占位符"
            new_display = self.config.zhihu.cookie[:10] + "..." + self.config.zhihu.cookie[-10:] if self.config.zhihu.cookie else "空"
            output_handler.info(f"从环境变量覆盖 zhihu.cookie: {old_display} → {new_display}")
        elif self.config.zhihu.cookie.startswith("${") and self.config.zhihu.cookie.endswith("}"):
            # 配置文件使用占位符格式，尝试解析
            env_var = self.config.zhihu.cookie[2:-1]
            env_value = os.getenv(env_var, "")
            self.config.zhihu.cookie = env_value
            if env_value:
                output_handler.info(f"从环境变量解析 zhihu.cookie 占位符: {env_var}")
            else:
                output_handler.warning(f"zhihu.cookie 占位符 {env_var} 对应的环境变量未设置，使用空值")
        
        # API密钥处理：优先使用环境变量，如果配置文件使用占位符格式则解析
        if os.getenv("DEEPSEEK_API_KEY"):
            old_api_key = self.config.ai.api_key
            self.config.ai.api_key = os.getenv("DEEPSEEK_API_KEY", "")
            # 只显示API密钥的前10个字符和后4个字符，保护敏感信息
            old_display = old_api_key[:10] + "..." + old_api_key[-4:] if old_api_key and not old_api_key.startswith("${") else "占位符"
            new_display = self.config.ai.api_key[:10] + "..." + self.config.ai.api_key[-4:] if self.config.ai.api_key else "空"
            output_handler.info(f"从环境变量覆盖 ai.api_key: {old_display} → {new_display}")
        elif self.config.ai.api_key.startswith("${") and self.config.ai.api_key.endswith("}"):
            # 配置文件使用占位符格式，尝试解析
            env_var = self.config.ai.api_key[2:-1]
            env_value = os.getenv(env_var, "")
            self.config.ai.api_key = env_value
            if env_value:
                output_handler.info(f"从环境变量解析 ai.api_key 占位符: {env_var}")
            else:
                output_handler.warning(f"ai.api_key 占位符 {env_var} 对应的环境变量未设置，使用空值")
        
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
        
        Returns:
            bool: 登录是否成功
        """
        global output_handler
        try:
            if self.publisher.check_login():
                output_handler.info("知乎登录成功，可以发布")
                return True
            else:
                output_handler.warning("知乎登录失败，发布功能可能无法使用")
                # 禁用知乎发布功能
                self.config.zhihu.enabled = False
                output_handler.info("已自动禁用知乎发布功能")
                return False
        except ZhihuCookieError as e:
            output_handler.error(f"知乎Cookie无效: {e}")
            output_handler.info("已自动禁用知乎发布功能")
            self.config.zhihu.enabled = False
            return False
        except ZhihuLoginError as e:
            output_handler.error(f"知乎登录检查失败: {e}")
            output_handler.info("已自动禁用知乎发布功能")
            self.config.zhihu.enabled = False
            return False
        except Exception as e:
            output_handler.error(f"检查知乎登录状态时出错: {e}")
            output_handler.info("已自动禁用知乎发布功能")
            self.config.zhihu.enabled = False
            return False
    
    def run_once(self, publish: bool = True) -> ProcessingResult:
        """
        执行一次完整的扫描-总结-发布流程
        
        Args:
            publish: 是否发布到知乎（默认True）
            
        Returns:
            处理结果
        """
        global output_handler
        print_header("ArXiv 文献自动总结系统 - 单次运行")
        output_handler.info("=" * 60)
        output_handler.info("启动ArXiv文献自动总结系统 - 单次运行")
        output_handler.info("=" * 60)
        
        # 1. 扫描论文
        output_handler.info("\n步骤 1: 扫描 arXiv 论文...")
        papers = self.scanner.search_recent_papers()
        
        if not papers:
            output_handler.info("没有找到新论文")
            return ProcessingResult(0, 0, 0, [])
        
        output_handler.info(f"找到 {len(papers)} 篇论文待处理")
        
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
                output_handler.info(f"跳过已总结的论文: {paper.arxiv_id}{folder_info}")
                task.update_status(TaskStatus.SKIPPED)
                batch_progress.mark_skipped()
                continue
            
            # 检查全局是否已处理（向后兼容）
            if self.storage.exists(paper.arxiv_id):
                output_handler.info(f"跳过已处理的论文: {paper.arxiv_id}")
                task.update_status(TaskStatus.SKIPPED)
                batch_progress.mark_skipped()
                continue
            
            # 执行任务
            batch_progress.start_paper(paper.arxiv_id, paper.title)
            try:
                self._execute_task_with_progress(task, batch_progress, publish)
                batch_progress.mark_success()
            except APIKeyError as e:
                # API密钥错误，终止整个处理流程
                output_handler.error(f"处理论文 {paper.arxiv_id} 时出错: {e}")
                output_handler.error("API密钥无效，终止处理流程")
                task.update_status(TaskStatus.FAILED, str(e))
                batch_progress.mark_failed()
                # 终止后续处理
                break
            except Exception as e:
                output_handler.error(f"处理论文 {paper.arxiv_id} 时出错: {e}")
                task.update_status(TaskStatus.FAILED, str(e))
                batch_progress.mark_failed()
        
        # 3. 统计结果
        success = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED)
        skipped = sum(1 for t in tasks if t.status == TaskStatus.SKIPPED)
        
        batch_progress.show_summary()
        
        output_handler.info("=" * 60)
        output_handler.info("处理完成")
        output_handler.info(f"  成功: {success}")
        output_handler.info(f"  失败: {failed}")
        output_handler.info(f"  跳过: {skipped}")
        output_handler.info("=" * 60)
        
        return ProcessingResult(success, failed, skipped, tasks)
    
    def run_continuous(self):
        """持续运行，按配置定时执行"""
        global output_handler
        if not self.config.scheduler.enabled:
            output_handler.warning("配置中禁用了调度器")
            return
        
        output_handler.info("=" * 60)
        output_handler.info("启动ArXiv文献自动总结系统 - 持续运行模式")
        output_handler.info(f"调度计划: {self.config.scheduler.cron}")
        output_handler.info("=" * 60)
        
        # 设置定时任务
        self.scheduler.schedule_cron_task(
            self.config.scheduler.cron,
            self.run_once
        )
        
        # 启动调度器
        try:
            self.scheduler.start(block=True)
        except KeyboardInterrupt:
            output_handler.info("收到中断信号，正在停止...")
            self.scheduler.stop()
    
    def process_single_paper(self, arxiv_id: str) -> PaperTask:
        """
        处理单篇论文
        
        Args:
            arxiv_id: arXiv ID
            
        Returns:
            处理任务
        """
        global output_handler
        output_handler.info(f"处理单篇论文: {arxiv_id}")
        
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
        global output_handler
        paper = task.paper
        if not paper:
            task.update_status(TaskStatus.FAILED, "Paper info is missing")
            return task
        
        try:
            # 1. 下载PDF
            output_handler.info(f"[{paper.arxiv_id}] 步骤 1/5: 下载PDF...")
            task.update_status(TaskStatus.DOWNLOADING)
            
            pdf_path = self.temp_dir / f"{paper.arxiv_id.replace('/', '_')}.pdf"
            
            if not self.scanner.download_pdf(paper, str(pdf_path)):
                raise RuntimeError("Failed to download PDF")
            
            # 2. 提取文本
            output_handler.info(f"[{paper.arxiv_id}] 步骤 2/5: 从PDF提取文本...")
            
            extractor = PDFExtractor()
            content = extractor.extract_text(str(pdf_path))
            
            if not content:
                raise RuntimeError("Failed to extract text from PDF")
            
            output_handler.info(f"[{paper.arxiv_id}] 提取了 {len(content)} 个字符")
            
            # 3. AI总结
            output_handler.info(f"[{paper.arxiv_id}] 步骤 3/5: 使用AI生成总结...")
            task.update_status(TaskStatus.SUMMARIZING)
            
            summary = self.summarizer.summarize(paper, content)
            task.summary = summary
            
            # 4. 保存到本地
            output_handler.info(f"[{paper.arxiv_id}] 步骤 4/5: 保存到本地存储...")
            task.update_status(TaskStatus.STORING)
            
            file_path = self.storage.save_summary(summary, paper)
            task.local_path = file_path
            
            # 5. 发布到知乎
            if self.config.zhihu.enabled:
                output_handler.info(f"[{paper.arxiv_id}] 步骤 5/5: 发布到知乎...")
                task.update_status(TaskStatus.PUBLISHING)
                
                try:
                    zhihu_url = self.publisher.publish(summary, paper)
                    if zhihu_url:
                        task.zhihu_url = zhihu_url
                        output_handler.info(f"[{paper.arxiv_id}] 已发布到知乎: {zhihu_url}")
                    else:
                        output_handler.warning(f"[{paper.arxiv_id}] 发布到知乎失败")
                except ZhihuCookieError as e:
                    output_handler.error(f"[{paper.arxiv_id}] 知乎Cookie无效: {e}")
                    output_handler.info("已自动禁用知乎发布功能，后续论文将只保存到本地")
                    self.config.zhihu.enabled = False
                    # 任务仍然算成功，因为总结已完成并保存
                    output_handler.info(f"[{paper.arxiv_id}] 论文已保存到本地，跳过知乎发布")
                except ZhihuLoginError as e:
                    output_handler.error(f"[{paper.arxiv_id}] 知乎登录失败: {e}")
                    output_handler.info("已自动禁用知乎发布功能，后续论文将只保存到本地")
                    self.config.zhihu.enabled = False
                    # 任务仍然算成功，因为总结已完成并保存
                    output_handler.info(f"[{paper.arxiv_id}] 论文已保存到本地，跳过知乎发布")
                except ZhihuPublishError as e:
                    output_handler.error(f"[{paper.arxiv_id}] 知乎发布失败: {e}")
                    # 发布失败不影响任务完成，因为总结已保存
                    output_handler.info(f"[{paper.arxiv_id}] 论文已保存到本地，知乎发布失败")
            else:
                output_handler.info(f"[{paper.arxiv_id}] 步骤 5/5: 知乎发布已禁用")
            
            # 完成任务
            task.update_status(TaskStatus.COMPLETED)
            output_handler.info(f"[{paper.arxiv_id}] 任务完成")
            
            # 清理临时文件
            if pdf_path.exists():
                pdf_path.unlink()
            
        except APIKeyError as e:
            # API密钥错误，终止整个处理流程
            error_msg = f"[{paper.arxiv_id}] AI API密钥错误: {e}"
            output_handler.error(error_msg)
            output_handler.error("API密钥无效，请检查配置后重新运行")
            task.update_status(TaskStatus.FAILED, str(e))
            # 重新抛出异常，让上层处理
            raise
        except APIError as e:
            # 其他API错误
            error_msg = f"[{paper.arxiv_id}] AI API错误: {e}"
            output_handler.error(error_msg)
            task.update_status(TaskStatus.FAILED, str(e))
        except Exception as e:
            output_handler.error(f"[{paper.arxiv_id}] 任务失败: {e}")
            task.update_status(TaskStatus.FAILED, str(e))
        
        return task
    
    def _execute_task_with_progress(self, task: PaperTask, batch_progress: BatchProgress, publish: bool = True) -> PaperTask:
        """
        执行单个任务（带进度显示）
        
        Args:
            task: 处理任务
            batch_progress: 批量进度显示
            publish: 是否发布到知乎（默认True）
            
        Returns:
            更新后的任务
        """
        global output_handler
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
            if publish and self.config.zhihu.enabled:
                progress.start_step(5, "发布知乎")
                task.update_status(TaskStatus.PUBLISHING)
                
                try:
                    zhihu_url = self.publisher.publish(summary, paper)
                    if zhihu_url:
                        task.zhihu_url = zhihu_url
                        progress.complete_step(f"已发布到知乎: {zhihu_url}")
                    else:
                        progress.warning("发布到知乎失败")
                except ZhihuCookieError as e:
                    progress.error(f"知乎Cookie无效: {e}")
                    output_handler.error(f"[{paper.arxiv_id}] 知乎Cookie无效: {e}")
                    output_handler.info("已自动禁用知乎发布功能，后续论文将只保存到本地")
                    self.config.zhihu.enabled = False
                    progress.info("论文已保存到本地，跳过知乎发布")
                except ZhihuLoginError as e:
                    progress.error(f"知乎登录失败: {e}")
                    output_handler.error(f"[{paper.arxiv_id}] 知乎登录失败: {e}")
                    output_handler.info("已自动禁用知乎发布功能，后续论文将只保存到本地")
                    self.config.zhihu.enabled = False
                    progress.info("论文已保存到本地，跳过知乎发布")
                except ZhihuPublishError as e:
                    progress.error(f"知乎发布失败: {e}")
                    output_handler.error(f"[{paper.arxiv_id}] 知乎发布失败: {e}")
                    progress.info("论文已保存到本地，知乎发布失败")
            else:
                progress.info("知乎发布已禁用")
            
            # 完成任务
            task.update_status(TaskStatus.COMPLETED)
            progress.info("任务完成")
            
            # 清理临时文件
            if pdf_path.exists():
                pdf_path.unlink()
            
        except APIKeyError as e:
            # API密钥错误，终止整个处理流程
            error_msg = f"[{paper.arxiv_id}] AI API密钥错误: {e}"
            progress.error(f"API密钥错误: {e}")
            output_handler.error(error_msg)
            output_handler.error("API密钥无效，请检查配置后重新运行")
            task.update_status(TaskStatus.FAILED, str(e))
            # 重新抛出异常，让上层处理
            raise
        except APIError as e:
            # 其他API错误
            error_msg = f"[{paper.arxiv_id}] AI API错误: {e}"
            progress.error(f"AI API错误: {e}")
            output_handler.error(error_msg)
            task.update_status(TaskStatus.FAILED, str(e))
        except Exception as e:
            progress.error(f"任务失败: {e}")
            output_handler.error(f"[{paper.arxiv_id}] 任务失败: {e}")
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
