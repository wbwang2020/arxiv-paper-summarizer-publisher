import time
import threading
from typing import Callable, Optional
from datetime import datetime

import schedule

from config import SchedulerConfig
from utils import get_logger

logger = get_logger()


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, config: SchedulerConfig):
        self.config = config
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def schedule_daily_task(
        self,
        hour: int,
        minute: int,
        task_func: Callable,
        *args,
        **kwargs
    ):
        """
        设置每日定时任务
        
        Args:
            hour: 小时 (0-23)
            minute: 分钟 (0-59)
            task_func: 任务函数
            *args: 位置参数
            **kwargs: 关键字参数
        """
        def job():
            try:
                logger.info(f"在 {datetime.now()} 执行定时任务")
                task_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"定时任务执行失败: {e}")
        
        schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(job)
        logger.info(f"已设置每日定时任务: {hour:02d}:{minute:02d}")
    
    def schedule_cron_task(
        self,
        cron_expr: str,
        task_func: Callable,
        *args,
        **kwargs
    ):
        """
        使用Cron表达式设置任务
        
        支持的基本格式:
        - "0 9 * * *" : 每天上午9点
        - "0 9 * * 1" : 每周一上午9点
        - "0 */6 * * *" : 每6小时
        
        Args:
            cron_expr: Cron表达式 (分 时 日 月 周)
            task_func: 任务函数
            *args: 位置参数
            **kwargs: 关键字参数
        """
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError("Invalid cron expression. Expected format: '分 时 日 月 周'")
        
        minute, hour, day, month, weekday = parts
        
        def job():
            try:
                logger.info(f"在 {datetime.now()} 执行定时任务")
                task_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"定时任务执行失败: {e}")
        
        # 解析并设置调度
        job_scheduled = self._parse_cron_schedule(minute, hour, day, month, weekday, job)
        
        if job_scheduled:
            logger.info(f"已设置Cron定时任务: {cron_expr}")
        else:
            logger.warning(f"无法解析Cron表达式: {cron_expr}")
    
    def _parse_cron_schedule(
        self,
        minute: str,
        hour: str,
        day: str,
        month: str,
        weekday: str,
        job: Callable
    ) -> bool:
        """
        解析Cron表达式并设置调度
        
        Returns:
            是否成功设置
        """
        try:
            # 处理 */n 格式（每n分钟/小时）
            if minute.startswith("*/") and hour == "*":
                interval = int(minute.split("/")[1])
                schedule.every(interval).minutes.do(job)
                return True
            
            if hour.startswith("*/") and minute == "0":
                interval = int(hour.split("/")[1])
                schedule.every(interval).hours.do(job)
                return True
            
            # 处理具体时间
            if minute.isdigit() and hour.isdigit():
                time_str = f"{int(hour):02d}:{int(minute):02d}"
                
                # 特定星期几
                if weekday.isdigit():
                    day_map = {
                        "0": schedule.every().sunday,
                        "1": schedule.every().monday,
                        "2": schedule.every().tuesday,
                        "3": schedule.every().wednesday,
                        "4": schedule.every().thursday,
                        "5": schedule.every().friday,
                        "6": schedule.every().saturday,
                    }
                    if weekday in day_map:
                        day_map[weekday].at(time_str).do(job)
                        return True
                
                # 每天
                if weekday == "*":
                    schedule.every().day.at(time_str).do(job)
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"解析Cron调度时出错: {e}")
            return False
    
    def start(self, block: bool = False):
        """
        启动调度器
        
        Args:
            block: 是否阻塞当前线程
        """
        if self.running:
            logger.warning("调度器已在运行")
            return
        
        self.running = True
        self._stop_event.clear()
        
        if block:
            self._run_scheduler()
        else:
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()
            logger.info("调度器已在后台线程启动")
    
    def _run_scheduler(self):
        """运行调度循环"""
        logger.info("调度器循环已启动")
        
        while self.running and not self._stop_event.is_set():
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"调度器循环出错: {e}")
                time.sleep(5)
        
        logger.info("调度器循环已停止")
    
    def stop(self):
        """停止调度器"""
        if not self.running:
            return
        
        logger.info("正在停止调度器...")
        self.running = False
        self._stop_event.set()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        # 清除所有任务
        schedule.clear()
        logger.info("调度器已停止")
    
    def get_next_run_time(self) -> Optional[datetime]:
        """
        获取下次运行时间
        
        Returns:
            下次运行时间，没有任务返回None
        """
        next_run = schedule.next_run()
        if next_run:
            return next_run
        return None
    
    def get_pending_jobs(self) -> list:
        """
        获取待执行的任务列表
        
        Returns:
            任务列表
        """
        return schedule.jobs
