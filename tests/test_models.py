from datetime import datetime
from models.paper import ArxivPaper
from models.summary import PaperSummary, FigureTableInfo, ReferenceInfo
from models.task import TaskStatus, PaperTask


def test_arxiv_paper():
    """测试ArxivPaper类"""
    paper = ArxivPaper(
        arxiv_id="2401.12345v1",
        title="Test Paper",
        authors=["Author 1", "Author 2", "Author 3", "Author 4"],
        author_affiliations=["University 1", "University 2"],
        abstract="Test abstract",
        categories=["cs.LG", "cs.AI"],
        published_date=datetime(2024, 1, 1),
        updated_date=datetime(2024, 1, 2),
        pdf_url="https://arxiv.org/pdf/2401.12345v1.pdf",
        abs_url="https://arxiv.org/abs/2401.12345v1",
        primary_category="cs.LG",
        venue="arXiv"
    )
    
    assert paper.arxiv_id == "2401.12345v1"
    assert paper.title == "Test Paper"
    assert len(paper.authors) == 4
    assert len(paper.author_affiliations) == 2
    assert paper.get_short_id() == "2401.12345"
    assert paper.get_authors_text() == "Author 1, Author 2, Author 3 et al. (4 authors)"
    assert paper.get_authors_text(max_authors=2) == "Author 1, Author 2 et al. (4 authors)"
    assert paper.get_authors_text(max_authors=5) == "Author 1, Author 2, Author 3, Author 4"
    assert str(paper) == "[2401.12345v1] Test Paper"


def test_figure_table_info():
    """测试FigureTableInfo类"""
    fig_info = FigureTableInfo(
        number="Figure 1",
        title="Test Figure",
        description="Test description"
    )
    
    assert fig_info.number == "Figure 1"
    assert fig_info.title == "Test Figure"
    assert fig_info.description == "Test description"


def test_reference_info():
    """测试ReferenceInfo类"""
    ref_info = ReferenceInfo(
        authors="Author 1, Author 2",
        year="2024",
        title="Test Reference",
        journal="Test Journal",
        volume_issue="Vol. 1, No. 1",
        pages="1-10"
    )
    
    assert ref_info.authors == "Author 1, Author 2"
    assert ref_info.year == "2024"
    assert ref_info.title == "Test Reference"
    assert ref_info.journal == "Test Journal"
    assert ref_info.volume_issue == "Vol. 1, No. 1"
    assert ref_info.pages == "1-10"


def test_paper_summary():
    """测试PaperSummary类"""
    summary = PaperSummary(
        arxiv_id="2401.12345v1",
        title="Test Paper",
        authors=["Author 1", "Author 2"],
        author_affiliations=["University 1"],
        published_year=2024,
        venue="arXiv",
        doi="10.1234/test",
        motivation="Test motivation",
        core_hypothesis="Test hypothesis",
        research_design="Test design",
        data_source="Test data",
        methods="Test methods",
        analysis_process="Test analysis",
        data_analysis="Test data analysis",
        core_findings="Test findings",
        experimental_results="Test results",
        supporting_results="Test supporting results",
        conclusions="Test conclusions",
        contributions="Test contributions",
        relevance="Test relevance",
        highlights="Test highlights",
        figures_tables=[
            FigureTableInfo(
                number="Figure 1",
                title="Test Figure",
                description="Test figure description"
            )
        ],
        evaluation="Test evaluation",
        questions="Test questions",
        inspiration="Test inspiration",
        references=[
            ReferenceInfo(
                authors="Author 1, Author 2",
                year="2024",
                title="Test Reference",
                journal="Test Journal"
            )
        ],
        ai_model="deepseek-chat",
        processing_time=10.5
    )
    
    assert summary.arxiv_id == "2401.12345v1"
    assert summary.title == "Test Paper"
    assert len(summary.authors) == 2
    assert summary.published_year == 2024
    assert summary.venue == "arXiv"
    assert summary.doi == "10.1234/test"
    assert summary.ai_model == "deepseek-chat"
    assert summary.processing_time == 10.5
    
    # 测试to_markdown方法
    markdown_content = summary.to_markdown()
    assert "# Test Paper" in markdown_content
    assert "## 1. 基本信息" in markdown_content
    assert "- **论文标题**: Test Paper" in markdown_content
    assert "- **作者**: Author 1, Author 2" in markdown_content
    assert "- **作者单位**: University 1" in markdown_content
    assert "- **发表年份**: 2024" in markdown_content
    assert "- **期刊/会议**: arXiv" in markdown_content
    assert "- **arXiv ID**: 2401.12345v1" in markdown_content
    assert "- **DOI**: 10.1234/test" in markdown_content
    assert "## 2. 研究动机" in markdown_content
    assert "Test motivation" in markdown_content
    assert "## 3. 核心假设" in markdown_content
    assert "Test hypothesis" in markdown_content
    
    # 测试包含元数据的情况
    markdown_with_metadata = summary.to_markdown(include_metadata=True)
    assert "---" in markdown_with_metadata
    assert "总结生成时间:" in markdown_with_metadata
    assert "AI模型: deepseek-chat" in markdown_with_metadata
    assert "处理耗时: 10.50秒" in markdown_with_metadata


def test_task_status():
    """测试TaskStatus枚举"""
    assert TaskStatus.PENDING == "pending"
    assert TaskStatus.SCANNING == "scanning"
    assert TaskStatus.DOWNLOADING == "downloading"
    assert TaskStatus.SUMMARIZING == "summarizing"
    assert TaskStatus.STORING == "storing"
    assert TaskStatus.PUBLISHING == "publishing"
    assert TaskStatus.COMPLETED == "completed"
    assert TaskStatus.FAILED == "failed"
    assert TaskStatus.SKIPPED == "skipped"


def test_paper_task():
    """测试PaperTask类"""
    task = PaperTask(
        task_id="test-task-id",
        arxiv_id="2401.12345v1"
    )
    
    assert task.task_id == "test-task-id"
    assert task.arxiv_id == "2401.12345v1"
    assert task.status == TaskStatus.PENDING
    assert task.retry_count == 0
    assert not task.is_successful()
    assert not task.is_failed()
    assert task.can_retry()
    
    # 更新状态
    task.update_status(TaskStatus.COMPLETED)
    assert task.status == TaskStatus.COMPLETED
    assert task.is_successful()
    assert not task.is_failed()
    
    # 测试失败状态
    task2 = PaperTask(
        task_id="test-task-id-2",
        arxiv_id="2401.12345v1"
    )
    task2.update_status(TaskStatus.FAILED, "Test error")
    assert task2.status == TaskStatus.FAILED
    assert task2.error_message == "Test error"
    assert not task2.is_successful()
    assert task2.is_failed()
    assert task2.can_retry()
    
    # 测试重试次数
    task2.increment_retry()
    assert task2.retry_count == 1
    assert task2.can_retry()
    
    # 测试达到最大重试次数
    for i in range(3):
        task2.increment_retry()
    assert task2.retry_count == 4
    assert not task2.can_retry()


if __name__ == "__main__":
    test_arxiv_paper()
    test_figure_table_info()
    test_reference_info()
    test_paper_summary()
    test_task_status()
    test_paper_task()
    print("All tests passed!")