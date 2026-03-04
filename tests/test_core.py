import os
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from config.config import Config, ArxivConfig, AIConfig, StorageConfig, ZhihuConfig, SchedulerConfig
from models.paper import ArxivPaper
from models.summary import PaperSummary
from models.task import PaperTask, TaskStatus
from core.system import ArxivSurveySystem, ProcessingResult


def test_arxiv_survey_system_init():
    """测试ArxivSurveySystem初始化"""
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
arxiv:
  keywords:
    - World Model
  categories:
    - cs.LG
  max_results: 10
  days_back: 7
  sort_by: submittedDate
  sort_order: descending

ai:
  api_key: test-api-key
  model: deepseek-chat
  api_url: https://api.deepseek.com/v1/chat/completions
  temperature: 0.7
  max_tokens: 4000
  max_input_tokens: 16000
  timeout: 60

storage:
  base_dir: ./papers
  format: markdown
  filename_template: "{date}_{arxiv_id}_{title}"
  organize_by: date
  include_metadata: false

zhihu:
  enabled: false
  cookie: ""
  draft_first: true
  column_id: ""
  column_name: ""
  create_column_if_not_exists: false

scheduler:
  enabled: false
  cron: "0 9 * * *"
""")
        config_path = f.name
    
    try:
        # 测试从配置文件初始化
        system = ArxivSurveySystem(config_path)
        assert system.config is not None
        assert system.config.arxiv.keywords == ["World Model"]
        assert system.config.arxiv.categories == ["cs.LG"]
    finally:
        if os.path.exists(config_path):
            os.unlink(config_path)

@patch('core.system.ArxivScanner')
@patch('core.system.PaperSummarizer')
@patch('core.system.PaperStorage')
@patch('core.system.ZhihuPlaywrightPublisher')
@patch('core.system.TaskScheduler')
@patch('core.system.PDFExtractor')
def test_arxiv_survey_system_run_once(mock_pdf_extractor, mock_scheduler, mock_publisher, mock_storage, mock_summarizer, mock_scanner):
    """测试ArxivSurveySystem.run_once方法"""
    # 配置模拟对象
    mock_scanner_instance = Mock()
    mock_scanner.return_value = mock_scanner_instance
    
    # 创建模拟论文
    mock_paper = Mock(spec=ArxivPaper)
    mock_paper.arxiv_id = "2401.12345v1"
    mock_paper.title = "Test Paper"
    mock_paper.published_date = datetime(2024, 1, 1)
    
    mock_scanner_instance.search_recent_papers.return_value = [mock_paper]
    
    # 模拟存储
    mock_storage_instance = Mock()
    mock_storage.return_value = mock_storage_instance
    mock_storage_instance.exists_in_recent_months.return_value = False
    mock_storage_instance.exists.return_value = False
    
    # 模拟摘要器
    mock_summarizer_instance = Mock()
    mock_summarizer.return_value = mock_summarizer_instance
    
    mock_summary = Mock(spec=PaperSummary)
    mock_summary.ai_model = "deepseek-chat"
    mock_summarizer_instance.summarize.return_value = mock_summary
    
    # 模拟存储保存
    mock_storage_instance.save_summary.return_value = "./papers/2024-01/test.md"
    
    # 模拟知乎发布
    mock_publisher_instance = Mock()
    mock_publisher.return_value = mock_publisher_instance
    mock_publisher_instance.publish.return_value = "https://zhihu.com/p/12345"
    
    # 模拟调度器
    mock_scheduler_instance = Mock()
    mock_scheduler.return_value = mock_scheduler_instance
    
    # 模拟PDFExtractor
    mock_extractor_instance = Mock()
    mock_pdf_extractor.return_value = mock_extractor_instance
    mock_extractor_instance.extract_text.return_value = "Test PDF content"
    
    # 创建系统实例
    system = ArxivSurveySystem()
    system.scanner = mock_scanner_instance
    system.summarizer = mock_summarizer_instance
    system.storage = mock_storage_instance
    system.publisher = mock_publisher_instance
    system.scheduler = mock_scheduler_instance
    from pathlib import Path
    system.temp_dir = Path("./temp")
    
    # 测试运行
    result = system.run_once()
    assert isinstance(result, ProcessingResult)
    assert len(result.tasks) == 1

@patch('core.system.ArxivScanner')
@patch('core.system.PaperSummarizer')
@patch('core.system.PaperStorage')
@patch('core.system.ZhihuPlaywrightPublisher')
@patch('core.system.TaskScheduler')
@patch('core.system.PDFExtractor')
def test_arxiv_survey_system_process_single_paper(mock_pdf_extractor, mock_scheduler, mock_publisher, mock_storage, mock_summarizer, mock_scanner):
    """测试ArxivSurveySystem.process_single_paper方法"""
    # 配置模拟对象
    mock_scanner_instance = Mock()
    mock_scanner.return_value = mock_scanner_instance
    
    # 创建模拟论文
    mock_paper = Mock(spec=ArxivPaper)
    mock_paper.arxiv_id = "2401.12345v1"
    mock_paper.title = "Test Paper"
    mock_paper.published_date = datetime(2024, 1, 1)
    
    mock_scanner_instance.get_paper_by_id.return_value = mock_paper
    
    # 模拟PDF下载
    mock_scanner_instance.download_pdf.return_value = True
    
    # 模拟摘要器
    mock_summarizer_instance = Mock()
    mock_summarizer.return_value = mock_summarizer_instance
    
    mock_summary = Mock(spec=PaperSummary)
    mock_summary.ai_model = "deepseek-chat"
    mock_summarizer_instance.summarize.return_value = mock_summary
    
    # 模拟存储
    mock_storage_instance = Mock()
    mock_storage.return_value = mock_storage_instance
    mock_storage_instance.save_summary.return_value = "./papers/2024-01/test.md"
    
    # 模拟知乎发布
    mock_publisher_instance = Mock()
    mock_publisher.return_value = mock_publisher_instance
    mock_publisher_instance.publish.return_value = "https://zhihu.com/p/12345"
    
    # 模拟调度器
    mock_scheduler_instance = Mock()
    mock_scheduler.return_value = mock_scheduler_instance
    
    # 模拟PDFExtractor
    mock_extractor_instance = Mock()
    mock_pdf_extractor.return_value = mock_extractor_instance
    mock_extractor_instance.extract_text.return_value = "Test PDF content"
    
    # 创建系统实例
    system = ArxivSurveySystem()
    system.scanner = mock_scanner_instance
    system.summarizer = mock_summarizer_instance
    system.storage = mock_storage_instance
    system.publisher = mock_publisher_instance
    system.scheduler = mock_scheduler_instance
    from pathlib import Path
    system.temp_dir = Path("./temp")
    
    # 测试处理单篇论文
    task = system.process_single_paper("2401.12345v1")
    assert isinstance(task, PaperTask)
    assert task.arxiv_id == "2401.12345v1"

@patch('core.system.ArxivScanner')
@patch('core.system.PaperSummarizer')
@patch('core.system.PaperStorage')
@patch('core.system.ZhihuPlaywrightPublisher')
@patch('core.system.TaskScheduler')
@patch('core.system.PDFExtractor')
def test_arxiv_survey_system_execute_task(mock_pdf_extractor, mock_scheduler, mock_publisher, mock_storage, mock_summarizer, mock_scanner):
    """测试ArxivSurveySystem._execute_task方法"""
    # 配置模拟对象
    mock_scanner_instance = Mock()
    mock_scanner.return_value = mock_scanner_instance
    # 模拟download_pdf方法，设置local_path
    def mock_download_pdf(paper, save_path):
        # 直接使用save_path作为local_path
        return True
    mock_scanner_instance.download_pdf.side_effect = mock_download_pdf
    
    # 模拟摘要器
    mock_summarizer_instance = Mock()
    mock_summarizer.return_value = mock_summarizer_instance
    
    mock_summary = Mock(spec=PaperSummary)
    mock_summary.ai_model = "deepseek-chat"
    mock_summarizer_instance.summarize.return_value = mock_summary
    
    # 模拟存储
    mock_storage_instance = Mock()
    mock_storage.return_value = mock_storage_instance
    mock_storage_instance.save_summary.return_value = "./papers/2024-01/test.md"
    
    # 模拟知乎发布
    mock_publisher_instance = Mock()
    mock_publisher.return_value = mock_publisher_instance
    mock_publisher_instance.publish.return_value = "https://zhihu.com/p/12345"
    
    # 模拟调度器
    mock_scheduler_instance = Mock()
    mock_scheduler.return_value = mock_scheduler_instance
    
    # 模拟PDFExtractor
    mock_extractor_instance = Mock()
    mock_pdf_extractor.return_value = mock_extractor_instance
    mock_extractor_instance.extract_text.return_value = "Test PDF content"
    
    # 创建系统实例
    system = ArxivSurveySystem()
    system.scanner = mock_scanner_instance
    system.summarizer = mock_summarizer_instance
    system.storage = mock_storage_instance
    system.publisher = mock_publisher_instance
    system.scheduler = mock_scheduler_instance
    from pathlib import Path
    system.temp_dir = Path("./temp")
    
    # 创建模拟论文
    mock_paper = Mock(spec=ArxivPaper)
    mock_paper.arxiv_id = "2401.12345v1"
    mock_paper.title = "Test Paper"
    mock_paper.published_date = datetime(2024, 1, 1)
    
    # 创建任务
    task = system._create_task(mock_paper)
    
    # 测试执行任务
    updated_task = system._execute_task(task)
    assert updated_task.status == TaskStatus.COMPLETED

@patch('core.system.ArxivScanner')
@patch('core.system.PaperSummarizer')
@patch('core.system.PaperStorage')
@patch('core.system.ZhihuPlaywrightPublisher')
@patch('core.system.TaskScheduler')
def test_arxiv_survey_system_check_zhihu_login(mock_scheduler, mock_publisher, mock_storage, mock_summarizer, mock_scanner):
    """测试ArxivSurveySystem.check_zhihu_login方法"""
    # 配置模拟对象
    mock_publisher_instance = Mock()
    mock_publisher.return_value = mock_publisher_instance
    mock_publisher_instance.check_login.return_value = True
    
    # 创建系统实例
    system = ArxivSurveySystem()
    system.publisher = mock_publisher_instance
    
    # 测试检查知乎登录状态
    assert system.check_zhihu_login() is True

@patch('core.system.ArxivScanner')
@patch('core.system.PaperSummarizer')
@patch('core.system.PaperStorage')
@patch('core.system.ZhihuPlaywrightPublisher')
@patch('core.system.TaskScheduler')
def test_arxiv_survey_system_get_zhihu_columns(mock_scheduler, mock_publisher, mock_storage, mock_summarizer, mock_scanner):
    """测试ArxivSurveySystem.get_zhihu_columns方法"""
    # 配置模拟对象
    mock_publisher_instance = Mock()
    mock_publisher.return_value = mock_publisher_instance
    mock_publisher_instance.get_columns.return_value = [{"id": "123", "title": "Test Column"}]
    
    # 创建系统实例
    system = ArxivSurveySystem()
    system.publisher = mock_publisher_instance
    
    # 测试获取知乎专栏列表
    columns = system.get_zhihu_columns()
    assert len(columns) == 1
    assert columns[0]["id"] == "123"
    assert columns[0]["title"] == "Test Column"

@patch('core.system.ArxivScanner')
@patch('core.system.PaperSummarizer')
@patch('core.system.PaperStorage')
@patch('core.system.ZhihuPlaywrightPublisher')
@patch('core.system.TaskScheduler')
def test_arxiv_survey_system_get_storage_stats(mock_scheduler, mock_publisher, mock_storage, mock_summarizer, mock_scanner):
    """测试ArxivSurveySystem.get_storage_stats方法"""
    # 配置模拟对象
    mock_storage_instance = Mock()
    mock_storage.return_value = mock_storage_instance
    mock_storage_instance.get_stats.return_value = {
        "total_papers": 10,
        "by_category": {"cs.LG": 5, "cs.AI": 5},
        "by_year": {2024: 10},
        "by_folder": [{"folder": "2024-01", "total_papers": 10}]
    }
    
    # 创建系统实例
    system = ArxivSurveySystem()
    system.storage = mock_storage_instance
    
    # 测试获取存储统计
    stats = system.get_storage_stats()
    assert stats["total_papers"] == 10
    assert "cs.LG" in stats["by_category"]
    assert stats["by_category"]["cs.LG"] == 5

@patch('core.system.ArxivScanner')
@patch('core.system.PaperSummarizer')
@patch('core.system.PaperStorage')
@patch('core.system.ZhihuPlaywrightPublisher')
@patch('core.system.TaskScheduler')
def test_arxiv_survey_system_list_processed_papers(mock_scheduler, mock_publisher, mock_storage, mock_summarizer, mock_scanner):
    """测试ArxivSurveySystem.list_processed_papers方法"""
    # 配置模拟对象
    mock_storage_instance = Mock()
    mock_storage.return_value = mock_storage_instance
    mock_storage_instance.list_summaries.return_value = [{"arxiv_id": "2401.12345v1", "title": "Test Paper"}]
    
    # 创建系统实例
    system = ArxivSurveySystem()
    system.storage = mock_storage_instance
    
    # 测试列出已处理的论文
    papers = system.list_processed_papers()
    assert len(papers) == 1
    assert papers[0]["arxiv_id"] == "2401.12345v1"
    assert papers[0]["title"] == "Test Paper"

@patch('core.system.ArxivScanner')
@patch('core.system.PaperSummarizer')
@patch('core.system.PaperStorage')
@patch('core.system.ZhihuPlaywrightPublisher')
@patch('core.system.TaskScheduler')
def test_arxiv_survey_system_list_recent_summaries(mock_scheduler, mock_publisher, mock_storage, mock_summarizer, mock_scanner):
    """测试ArxivSurveySystem.list_recent_summaries方法"""
    # 配置模拟对象
    mock_storage_instance = Mock()
    mock_storage.return_value = mock_storage_instance
    mock_storage_instance.list_recent_summaries.return_value = [{"arxiv_id": "2401.12345v1", "title": "Test Paper"}]
    
    # 创建系统实例
    system = ArxivSurveySystem()
    system.storage = mock_storage_instance
    
    # 测试列出最近的总结
    summaries = system.list_recent_summaries()
    assert len(summaries) == 1
    assert summaries[0]["arxiv_id"] == "2401.12345v1"
    assert summaries[0]["title"] == "Test Paper"

@patch('core.system.ArxivScanner')
@patch('core.system.PaperSummarizer')
@patch('core.system.PaperStorage')
@patch('core.system.ZhihuPlaywrightPublisher')
@patch('core.system.TaskScheduler')
def test_arxiv_survey_system_get_folder_brief(mock_scheduler, mock_publisher, mock_storage, mock_summarizer, mock_scanner):
    """测试ArxivSurveySystem.get_folder_brief方法"""
    # 配置模拟对象
    mock_storage_instance = Mock()
    mock_storage.return_value = mock_storage_instance
    mock_storage_instance.get_folder_brief.return_value = {
        "papers": {"2401.12345v1": {"title": "Test Paper"}},
        "meta": {"folder": "2024-01", "total_papers": 1}
    }
    
    # 创建系统实例
    system = ArxivSurveySystem()
    system.storage = mock_storage_instance
    
    # 测试获取文件夹简报
    brief = system.get_folder_brief("2024-01")
    assert brief is not None
    assert "papers" in brief
    assert "2401.12345v1" in brief["papers"]

@patch('core.system.ArxivScanner')
@patch('core.system.PaperSummarizer')
@patch('core.system.PaperStorage')
@patch('core.system.ZhihuPlaywrightPublisher')
@patch('core.system.TaskScheduler')
def test_arxiv_survey_system_check_paper_exists_in_recent_months(mock_scheduler, mock_publisher, mock_storage, mock_summarizer, mock_scanner):
    """测试ArxivSurveySystem.check_paper_exists_in_recent_months方法"""
    # 配置模拟对象
    mock_storage_instance = Mock()
    mock_storage.return_value = mock_storage_instance
    mock_storage_instance.exists_in_recent_months.return_value = True
    
    # 创建系统实例
    system = ArxivSurveySystem()
    system.storage = mock_storage_instance
    
    # 测试检查论文是否在最近月份内存在
    assert system.check_paper_exists_in_recent_months("2401.12345v1") is True


if __name__ == "__main__":
    test_arxiv_survey_system_init()
    test_arxiv_survey_system_run_once()
    test_arxiv_survey_system_process_single_paper()
    test_arxiv_survey_system_execute_task()
    test_arxiv_survey_system_check_zhihu_login()
    test_arxiv_survey_system_get_zhihu_columns()
    test_arxiv_survey_system_get_storage_stats()
    test_arxiv_survey_system_list_processed_papers()
    test_arxiv_survey_system_list_recent_summaries()
    test_arxiv_survey_system_get_folder_brief()
    test_arxiv_survey_system_check_paper_exists_in_recent_months()
    print("All tests passed!")