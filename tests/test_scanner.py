import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from config.config import ArxivConfig
from scanner.scanner import ArxivScanner
from scanner.pdf_extractor import PDFExtractor
from models.paper import ArxivPaper


def test_arxiv_scanner_build_query():
    """测试ArxivScanner._build_query方法"""
    config = ArxivConfig(
        keywords=["测试关键词1", "测试关键词2"],
        categories=["cs.LG", "cs.AI"]
    )
    scanner = ArxivScanner(config)
    
    # 测试使用配置中的关键词和分类
    query = scanner._build_query()
    assert "cat:cs.LG" in query
    assert "cat:cs.AI" in query
    assert 'all:"测试关键词1"' in query
    assert 'all:"测试关键词2"' in query
    
    # 测试使用自定义关键词和分类
    query = scanner._build_query(
        keywords=["GPT", "Transformer"],
        categories=["cs.CL"]
    )
    assert "cat:cs.CL" in query
    assert 'all:"GPT"' in query
    assert 'all:"Transformer"' in query
    
    # 测试空查询
    config_empty = ArxivConfig(keywords=[], categories=[])
    scanner_empty = ArxivScanner(config_empty)
    query = scanner_empty._build_query()
    assert query == ""


def test_arxiv_scanner_sort_criterion():
    """测试ArxivScanner._get_sort_criterion方法"""
    # 测试默认排序
    config = ArxivConfig()
    scanner = ArxivScanner(config)
    criterion = scanner._get_sort_criterion()
    assert criterion is not None
    
    # 测试其他排序方式
    config.sort_by = "lastUpdatedDate"
    criterion = scanner._get_sort_criterion()
    assert criterion is not None
    
    config.sort_by = "relevance"
    criterion = scanner._get_sort_criterion()
    assert criterion is not None


def test_arxiv_scanner_sort_order():
    """测试ArxivScanner._get_sort_order方法"""
    # 测试默认排序顺序
    config = ArxivConfig()
    scanner = ArxivScanner(config)
    order = scanner._get_sort_order()
    assert order is not None
    
    # 测试升序
    config.sort_order = "ascending"
    order = scanner._get_sort_order()
    assert order is not None


def test_arxiv_scanner_result_to_paper():
    """测试ArxivScanner._result_to_paper方法"""
    config = ArxivConfig()
    scanner = ArxivScanner(config)
    
    # 创建模拟的arxiv.Result对象
    mock_result = Mock()
    mock_result.entry_id = "http://arxiv.org/abs/2401.12345v1"
    mock_result.title = "Test Paper"
    mock_result.authors = ["Author 1 (University 1)", "Author 2 (University 2)"]
    mock_result.summary = "Test abstract"
    mock_result.categories = ["cs.LG", "cs.AI"]
    mock_result.published = datetime(2024, 1, 1)
    mock_result.updated = datetime(2024, 1, 2)
    mock_result.pdf_url = "https://arxiv.org/pdf/2401.12345v1.pdf"
    mock_result.primary_category = "cs.LG"
    
    paper = scanner._result_to_paper(mock_result)
    
    assert paper.arxiv_id == "2401.12345v1"
    assert paper.title == "Test Paper"
    assert paper.authors == ["Author 1 (University 1)", "Author 2 (University 2)"]
    assert paper.author_affiliations == ["University 1", "University 2"]
    assert paper.abstract == "Test abstract"
    assert paper.categories == ["cs.LG", "cs.AI"]
    assert paper.published_date == datetime(2024, 1, 1)
    assert paper.updated_date == datetime(2024, 1, 2)
    assert paper.pdf_url == "https://arxiv.org/pdf/2401.12345v1.pdf"
    assert paper.abs_url == "http://arxiv.org/abs/2401.12345v1"
    assert paper.primary_category == "cs.LG"

@patch('scanner.scanner.arxiv.Search')
@patch('scanner.scanner.arxiv.Client')
def test_arxiv_scanner_search_papers(mock_client_class, mock_search_class):
    """测试ArxivScanner.search_papers方法"""
    # 配置模拟对象
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    
    # 创建模拟的arxiv.Result对象
    mock_result = Mock()
    mock_result.entry_id = "http://arxiv.org/abs/2401.12345v1"
    mock_result.title = "Test Paper"
    mock_result.authors = ["Author 1"]
    mock_result.summary = "Test abstract"
    mock_result.categories = ["cs.LG"]
    mock_result.published = datetime(2024, 1, 1)
    mock_result.updated = datetime(2024, 1, 2)
    mock_result.pdf_url = "https://arxiv.org/pdf/2401.12345v1.pdf"
    mock_result.primary_category = "cs.LG"
    
    mock_client.results.return_value = [mock_result]
    
    # 测试搜索
    config = ArxivConfig(keywords=["测试关键词"], categories=["cs.LG"])
    scanner = ArxivScanner(config)
    papers = scanner.search_papers()
    
    assert len(papers) == 1
    assert papers[0].arxiv_id == "2401.12345v1"
    assert papers[0].title == "Test Paper"

@patch('scanner.scanner.ArxivScanner.search_papers')
def test_arxiv_scanner_search_recent_papers(mock_search_papers):
    """测试ArxivScanner.search_recent_papers方法"""
    # 配置模拟对象
    mock_paper = Mock()
    mock_search_papers.return_value = [mock_paper]
    
    # 测试搜索最近论文
    config = ArxivConfig(days_back=7)
    scanner = ArxivScanner(config)
    papers = scanner.search_recent_papers()
    
    mock_search_papers.assert_called_once()
    assert len(papers) == 1

@patch('scanner.scanner.arxiv.Search')
@patch('scanner.scanner.arxiv.Client')
def test_arxiv_scanner_get_paper_by_id(mock_client_class, mock_search_class):
    """测试ArxivScanner.get_paper_by_id方法"""
    # 配置模拟对象
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    
    # 创建模拟的arxiv.Result对象
    mock_result = Mock()
    mock_result.entry_id = "http://arxiv.org/abs/2401.12345v1"
    mock_result.title = "Test Paper"
    mock_result.authors = ["Author 1"]
    mock_result.summary = "Test abstract"
    mock_result.categories = ["cs.LG"]
    mock_result.published = datetime(2024, 1, 1)
    mock_result.updated = datetime(2024, 1, 2)
    mock_result.pdf_url = "https://arxiv.org/pdf/2401.12345v1.pdf"
    mock_result.primary_category = "cs.LG"
    
    mock_client.results.return_value = [mock_result]
    
    # 测试通过ID获取论文
    config = ArxivConfig()
    scanner = ArxivScanner(config)
    paper = scanner.get_paper_by_id("2401.12345v1")
    
    assert paper is not None
    assert paper.arxiv_id == "2401.12345v1"
    assert paper.title == "Test Paper"

@patch('scanner.scanner.requests.get')
def test_arxiv_scanner_download_pdf(mock_get):
    """测试ArxivScanner.download_pdf方法"""
    # 配置模拟对象
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.iter_content.return_value = [b"test pdf content"]
    mock_get.return_value = mock_response
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        temp_file = f.name
    
    try:
        # 创建论文对象
        paper = ArxivPaper(
            arxiv_id="2401.12345v1",
            title="Test Paper",
            authors=["Author 1"],
            published_date=datetime(2024, 1, 1),
            pdf_url="https://arxiv.org/pdf/2401.12345v1.pdf",
            abs_url="https://arxiv.org/abs/2401.12345v1",
            primary_category="cs.LG"
        )
        
        # 测试下载PDF
        config = ArxivConfig()
        scanner = ArxivScanner(config)
        success = scanner.download_pdf(paper, temp_file)
        
        assert success is True
        assert os.path.exists(temp_file)
        with open(temp_file, 'rb') as f:
            content = f.read()
        assert content == b"test pdf content"
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)


def test_pdf_extractor_init():
    """测试PDFExtractor初始化"""
    # 测试默认初始化
    extractor = PDFExtractor()
    assert extractor.preferred_method in ["pdfplumber", "pypdf2"]
    
    # 测试指定方法初始化
    extractor = PDFExtractor(preferred_method="pdfplumber")
    assert extractor.preferred_method in ["pdfplumber", "pypdf2"]


def test_pdf_extractor_extract_abstract_section():
    """测试PDFExtractor.extract_abstract_section方法"""
    extractor = PDFExtractor()
    
    # 测试包含摘要的文本
    text = """Abstract
This is the abstract of the paper.
It contains multiple lines.

1 Introduction
This is the introduction.
"""
    abstract = extractor.extract_abstract_section(text)
    assert "Abstract" in abstract
    assert "This is the abstract of the paper" in abstract
    assert "1 Introduction" not in abstract


def test_pdf_extractor_extract_introduction():
    """测试PDFExtractor.extract_introduction方法"""
    extractor = PDFExtractor()
    
    # 测试包含引言的文本
    text = """1 Introduction
This is the introduction of the paper.
It contains multiple lines.

2 Method
This is the method section.
"""
    introduction = extractor.extract_introduction(text)
    assert "1 Introduction" in introduction
    assert "This is the introduction of the paper" in introduction
    assert "2 Method" not in introduction


if __name__ == "__main__":
    test_arxiv_scanner_build_query()
    test_arxiv_scanner_sort_criterion()
    test_arxiv_scanner_sort_order()
    test_arxiv_scanner_result_to_paper()
    test_arxiv_scanner_search_papers()
    test_arxiv_scanner_search_recent_papers()
    test_arxiv_scanner_get_paper_by_id()
    test_arxiv_scanner_download_pdf()
    test_pdf_extractor_init()
    test_pdf_extractor_extract_abstract_section()
    test_pdf_extractor_extract_introduction()
    print("All tests passed!")