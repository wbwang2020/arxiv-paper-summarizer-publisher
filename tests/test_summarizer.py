import time
from datetime import datetime
from unittest.mock import Mock, patch

from config.config import AIConfig
from models.paper import ArxivPaper
from models.summary import PaperSummary
from summarizer.summarizer import PaperSummarizer


def test_paper_summarizer_init():
    """测试PaperSummarizer初始化"""
    config = AIConfig(api_key="test-api-key", model="deepseek-chat")
    summarizer = PaperSummarizer(config)
    
    assert summarizer.config == config
    assert summarizer.api_key == "test-api-key"


def test_paper_summarizer_build_prompt():
    """测试PaperSummarizer._build_prompt方法"""
    config = AIConfig(
        api_key="test-api-key", 
        model="deepseek-chat",
        max_input_tokens=10000
    )
    summarizer = PaperSummarizer(config)
    
    # 创建论文对象
    paper = ArxivPaper(
        arxiv_id="2401.12345v1",
        title="Test Paper",
        authors=["Author 1", "Author 2"],
        published_date=datetime(2024, 1, 1),
        abstract="Test abstract",
        pdf_url="https://arxiv.org/pdf/2401.12345v1.pdf",
        abs_url="https://arxiv.org/abs/2401.12345v1",
        primary_category="cs.LG"
    )
    
    # 测试构建提示词
    prompt = summarizer._build_prompt(paper, "Test content")
    assert "Test Paper" in prompt
    assert "Author 1, Author 2" in prompt
    assert "2024" in prompt
    assert "2401.12345v1" in prompt
    assert "Test abstract" in prompt
    assert "Test content" in prompt

@patch('summarizer.summarizer.requests.post')
def test_paper_summarizer_call_api(mock_post):
    """测试PaperSummarizer._call_api方法"""
    # 配置模拟对象
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": "## 1. 基本信息\n- **论文标题**: Test Paper\n- **作者**: Author 1, Author 2\n- **发表年份**: 2024\n- **期刊/会议**: arXiv\n- **arXiv ID**: 2401.12345v1"
            }
        }]
    }
    mock_post.return_value = mock_response
    
    # 测试API调用
    config = AIConfig(
        api_key="test-api-key", 
        model="deepseek-chat",
        api_url="https://api.deepseek.com/v1/chat/completions"
    )
    summarizer = PaperSummarizer(config)
    
    response = summarizer._call_api("Test prompt")
    assert "## 1. 基本信息" in response
    assert "Test Paper" in response

@patch('summarizer.summarizer.requests.post')
def test_paper_summarizer_call_api_with_retry(mock_post):
    """测试PaperSummarizer._call_api_with_retry方法"""
    # 配置模拟对象，第一次失败，第二次成功
    mock_response_fail = Mock()
    mock_response_fail.status_code = 500
    mock_response_fail.raise_for_status.side_effect = Exception("API error")
    
    mock_response_success = Mock()
    mock_response_success.status_code = 200
    mock_response_success.json.return_value = {
        "choices": [{
            "message": {
                "content": "## 1. 基本信息\n- **论文标题**: Test Paper"
            }
        }]
    }
    
    mock_post.side_effect = [mock_response_fail, mock_response_success]
    
    # 测试带重试的API调用
    config = AIConfig(
        api_key="test-api-key", 
        model="deepseek-chat",
        api_url="https://api.deepseek.com/v1/chat/completions"
    )
    summarizer = PaperSummarizer(config)
    
    response = summarizer._call_api_with_retry("Test prompt", 2)
    assert "## 1. 基本信息" in response
    assert "Test Paper" in response
    assert mock_post.call_count == 2


def test_paper_summarizer_extract_sections():
    """测试PaperSummarizer._extract_sections方法"""
    config = AIConfig(api_key="test-api-key", model="deepseek-chat")
    summarizer = PaperSummarizer(config)
    
    # 测试提取章节
    text = """## 1. 基本信息
This is section 1.

## 2. 研究动机
This is section 2.

## 3. 核心假设
This is section 3.
"""
    
    sections = summarizer._extract_sections(text)
    assert "1" in sections
    assert "2" in sections
    assert "3" in sections
    assert sections["1"] == "This is section 1."
    assert sections["2"] == "This is section 2."
    assert sections["3"] == "This is section 3."


def test_paper_summarizer_parse_figures_tables():
    """测试PaperSummarizer._parse_figures_tables方法"""
    config = AIConfig(api_key="test-api-key", model="deepseek-chat")
    summarizer = PaperSummarizer(config)
    
    # 测试解析图表信息
    text = """- **Figure 1**: Test Figure 1
  Description of figure 1

- **Table 2**: Test Table 2
  Description of table 2
"""
    
    figures_tables = summarizer._parse_figures_tables(text)
    assert len(figures_tables) == 2
    assert figures_tables[0].number == "Figure 1"
    assert figures_tables[0].title == "Test Figure 1"
    assert figures_tables[0].description == "Description of figure 1"
    assert figures_tables[1].number == "Table 2"
    assert figures_tables[1].title == "Test Table 2"
    assert figures_tables[1].description == "Description of table 2"


def test_paper_summarizer_parse_references():
    """测试PaperSummarizer._parse_references方法"""
    config = AIConfig(api_key="test-api-key", model="deepseek-chat")
    summarizer = PaperSummarizer(config)
    
    # 测试解析参考文献
    text = """1. Author 1, Author 2, 2024, "Test Paper", Journal of Testing, 1(1), 1-10

2. Author 3, 2023, "Another Paper", Conference Proceedings

3. Short ref
"""
    
    references = summarizer._parse_references(text)
    assert len(references) == 2  # 只取前2篇
    assert references[0].authors == "Author 1, Author 2"
    assert references[0].year == "2024"
    assert references[0].title == "Test Paper"
    assert references[1].authors == "Author 3"
    assert references[1].year == "2023"
    assert references[1].title == "Another Paper"


def test_paper_summarizer_extract_affiliations():
    """测试PaperSummarizer._extract_affiliations方法"""
    config = AIConfig(api_key="test-api-key", model="deepseek-chat")
    summarizer = PaperSummarizer(config)
    
    # 测试提取作者单位
    text = """- **作者单位**: University 1, University 2
- **其他信息**: Some info
"""
    
    affiliations = summarizer._extract_affiliations(text)
    assert len(affiliations) == 2
    assert affiliations[0] == "University 1"
    assert affiliations[1] == "University 2"


def test_paper_summarizer_extract_doi():
    """测试PaperSummarizer._extract_doi方法"""
    config = AIConfig(api_key="test-api-key", model="deepseek-chat")
    summarizer = PaperSummarizer(config)
    
    # 测试提取DOI
    text = """- **DOI**: 10.1234/test
- **其他信息**: Some info
"""
    
    doi = summarizer._extract_doi(text)
    assert doi == "10.1234/test"

@patch('summarizer.summarizer.PaperSummarizer._call_api')
def test_paper_summarizer_summarize(mock_call_api):
    """测试PaperSummarizer.summarize方法"""
    # 配置模拟对象
    mock_call_api.return_value = """## 1. 基本信息
- **论文标题**: Test Paper
- **作者**: Author 1, Author 2
- **作者单位**: University 1, University 2
- **发表年份**: 2024
- **期刊/会议**: arXiv
- **arXiv ID**: 2401.12345v1
- **DOI**: 10.1234/test

## 2. 研究动机
Test motivation

## 3. 核心假设
Test hypothesis

## 4. 研究设计
Test design

## 5. 数据/样本来源
Test data

## 6. 方法与技术
Test methods

## 7. 分析流程
Test analysis

## 8. 数据分析
Test data analysis

## 9. 核心发现
Test findings

## 10. 实验结果
Test results

## 11. 辅助结果
Test supporting results

## 12. 结论
Test conclusions

## 13. 贡献
Test contributions

## 14. 与研究主题的关联
Test relevance

## 15. 亮点
Test highlights

## 16. 图表信息
- **Figure 1**: Test Figure
  Description of figure

## 17. 评价
Test evaluation

## 18. 疑问
Test questions

## 19. 启发
Test inspiration

## 20. 参考文献
1. Author 1, 2024, "Test Paper", Journal
"""
    
    # 创建论文对象
    paper = ArxivPaper(
        arxiv_id="2401.12345v1",
        title="Test Paper",
        authors=["Author 1", "Author 2"],
        published_date=datetime(2024, 1, 1),
        abstract="Test abstract",
        pdf_url="https://arxiv.org/pdf/2401.12345v1.pdf",
        abs_url="https://arxiv.org/abs/2401.12345v1",
        primary_category="cs.LG"
    )
    
    # 测试总结
    config = AIConfig(api_key="test-api-key", model="deepseek-chat")
    summarizer = PaperSummarizer(config)
    
    summary = summarizer.summarize(paper, "Test content")
    
    assert isinstance(summary, PaperSummary)
    assert summary.arxiv_id == "2401.12345v1"
    assert summary.title == "Test Paper"
    assert summary.authors == ["Author 1", "Author 2"]
    assert summary.author_affiliations == ["University 1", "University 2"]
    assert summary.published_year == 2024
    assert summary.venue == "arXiv"
    assert summary.doi == "10.1234/test"
    assert summary.motivation == "Test motivation"
    assert summary.core_hypothesis == "Test hypothesis"
    assert summary.research_design == "Test design"
    assert summary.data_source == "Test data"
    assert summary.methods == "Test methods"
    assert summary.analysis_process == "Test analysis"
    assert summary.data_analysis == "Test data analysis"
    assert summary.core_findings == "Test findings"
    assert summary.experimental_results == "Test results"
    assert summary.supporting_results == "Test supporting results"
    assert summary.conclusions == "Test conclusions"
    assert summary.contributions == "Test contributions"
    assert summary.relevance == "Test relevance"
    assert summary.highlights == "Test highlights"
    assert summary.evaluation == "Test evaluation"
    assert summary.questions == "Test questions"
    assert summary.inspiration == "Test inspiration"
    assert len(summary.figures_tables) == 1
    assert len(summary.references) == 1
    assert summary.ai_model == "deepseek-chat"
    assert summary.processing_time > 0


if __name__ == "__main__":
    test_paper_summarizer_init()
    test_paper_summarizer_build_prompt()
    test_paper_summarizer_call_api()
    test_paper_summarizer_call_api_with_retry()
    test_paper_summarizer_extract_sections()
    test_paper_summarizer_parse_figures_tables()
    test_paper_summarizer_parse_references()
    test_paper_summarizer_extract_affiliations()
    test_paper_summarizer_extract_doi()
    test_paper_summarizer_summarize()
    print("All tests passed!")