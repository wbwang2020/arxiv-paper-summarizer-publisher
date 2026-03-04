from unittest.mock import Mock, patch
from datetime import datetime

from config.config import ZhihuConfig
from models.paper import ArxivPaper
from models.summary import PaperSummary
from publisher.zhihu import ZhihuPublisher


def test_zhihu_publisher_init():
    """测试ZhihuPublisher初始化"""
    config = ZhihuConfig(
        enabled=True,
        cookie="test_cookie",
        draft_first=True
    )
    publisher = ZhihuPublisher(config)
    
    assert publisher.config == config
    assert publisher.cookie == "test_cookie"
    assert "Cookie" in publisher.session.headers


def test_zhihu_publisher_extract_xsrf():
    """测试ZhihuPublisher._extract_xsrf方法"""
    config = ZhihuConfig(cookie="_xsrf=test_token; other_cookie=value")
    publisher = ZhihuPublisher(config)
    
    # 测试提取XSRF token
    xsrf = publisher._extract_xsrf()
    assert xsrf == "test_token"
    
    # 测试没有XSRF token的情况
    config_no_xsrf = ZhihuConfig(cookie="other_cookie=value")
    publisher_no_xsrf = ZhihuPublisher(config_no_xsrf)
    xsrf = publisher_no_xsrf._extract_xsrf()
    assert xsrf is None


def test_zhihu_publisher_markdown_to_zhihu_html():
    """测试ZhihuPublisher._markdown_to_zhihu_html方法"""
    config = ZhihuConfig()
    publisher = ZhihuPublisher(config)
    
    # 测试Markdown转换
    markdown = """# 标题1

## 标题2

**粗体**和*斜体*

- 无序列表项1
- 无序列表项2

1. 有序列表项1
2. 有序列表项2

[链接](https://example.com)

```
代码块
```

---
"""
    
    html = publisher._markdown_to_zhihu_html(markdown)
    assert "<h1>标题1</h1>" in html
    assert "<h2>标题2</h2>" in html
    assert "<strong>粗体</strong>" in html
    assert "<em>斜体</em>" in html
    assert "<ul>" in html
    assert "<li>无序列表项1</li>" in html
    assert "<ol>" in html
    assert "<li>有序列表项1</li>" in html
    assert '<a href="https://example.com">链接</a>' in html
    assert "<pre><code>代码块" in html
    assert "</code></pre>" in html
    assert "<hr>" in html

@patch('publisher.zhihu.requests.Session.post')
def test_zhihu_publisher_publish(mock_post):
    """测试ZhihuPublisher.publish方法"""
    # 配置模拟对象
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": "12345"
    }
    # 模拟headers属性
    mock_response.headers = {}
    mock_post.return_value = mock_response
    
    # 配置模拟XSRF提取
    config = ZhihuConfig(
        enabled=True,
        cookie="_xsrf=test_token",
        draft_first=True
    )
    publisher = ZhihuPublisher(config)
    
    # 模拟_extract_xsrf方法
    publisher._extract_xsrf = Mock(return_value="test_token")
    
    # 创建论文和总结对象
    paper = ArxivPaper(
        arxiv_id="2401.12345v1",
        title="Test Paper",
        authors=["Author 1"],
        published_date=datetime(2024, 1, 1),
        pdf_url="https://arxiv.org/pdf/2401.12345v1.pdf",
        abs_url="https://arxiv.org/abs/2401.12345v1",
        primary_category="cs.LG"
    )
    
    summary = PaperSummary(
        arxiv_id="2401.12345v1",
        title="Test Paper",
        authors=["Author 1"],
        published_year=2024,
        venue="arXiv"
    )
    
    # 测试发布
    url = publisher.publish(summary, paper)
    assert url == "https://www.zhihu.com/p/12345"
    mock_post.assert_called_once()

@patch('publisher.zhihu.requests.Session.get')
def test_zhihu_publisher_check_login(mock_get):
    """测试ZhihuPublisher.check_login方法"""
    # 配置模拟对象
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "name": "Test User"
    }
    mock_get.return_value = mock_response
    
    # 测试登录状态检查
    config = ZhihuConfig(cookie="test_cookie")
    publisher = ZhihuPublisher(config)
    
    assert publisher.check_login() is True
    
    # 测试未登录状态
    mock_response.status_code = 401
    assert publisher.check_login() is False

@patch('publisher.zhihu.requests.Session.get')
def test_zhihu_publisher_get_user_info(mock_get):
    """测试ZhihuPublisher.get_user_info方法"""
    # 配置模拟对象
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "123",
        "name": "Test User",
        "url_token": "test-user",
        "headline": "Test Headline",
        "avatar_url": "https://example.com/avatar.jpg"
    }
    mock_get.return_value = mock_response
    
    # 测试获取用户信息
    config = ZhihuConfig(cookie="test_cookie")
    publisher = ZhihuPublisher(config)
    
    user_info = publisher.get_user_info()
    assert user_info is not None
    assert user_info["id"] == "123"
    assert user_info["name"] == "Test User"
    assert user_info["url_token"] == "test-user"

@patch('publisher.zhihu.requests.Session.get')
def test_zhihu_publisher_search_columns(mock_get):
    """测试ZhihuPublisher.search_columns方法"""
    # 配置模拟对象
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {
                "type": "search_result",
                "object": {
                    "id": "123",
                    "title": "Test Column",
                    "description": "Test Description",
                    "url": "https://zhihu.com/column/test",
                    "author": {
                        "name": "Test Author"
                    }
                }
            }
        ]
    }
    mock_get.return_value = mock_response
    
    # 测试搜索专栏
    config = ZhihuConfig(cookie="test_cookie")
    publisher = ZhihuPublisher(config)
    
    columns = publisher.search_columns("test")
    assert len(columns) == 1
    assert columns[0]["id"] == "123"
    assert columns[0]["title"] == "Test Column"

@patch('publisher.zhihu.requests.Session.post')
def test_zhihu_publisher_create_column(mock_post):
    """测试ZhihuPublisher.create_column方法"""
    # 配置模拟对象
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": "123"
    }
    mock_post.return_value = mock_response
    
    # 测试创建专栏
    config = ZhihuConfig(cookie="test_cookie")
    publisher = ZhihuPublisher(config)
    
    column_id = publisher.create_column("Test Column", "Test Description")
    assert column_id == "123"
    mock_post.assert_called_once()

@patch('publisher.zhihu.ZhihuPublisher.find_column_by_name')
def test_zhihu_publisher_get_target_column_id(mock_find_column):
    """测试ZhihuPublisher._get_target_column_id方法"""
    # 测试直接配置column_id的情况
    config = ZhihuConfig(column_id="123")
    publisher = ZhihuPublisher(config)
    
    column_id = publisher._get_target_column_id()
    assert column_id == "123"
    
    # 测试通过column_name查找的情况
    config2 = ZhihuConfig(column_name="Test Column")
    publisher2 = ZhihuPublisher(config2)
    
    mock_find_column.return_value = {"id": "456", "title": "Test Column"}
    column_id = publisher2._get_target_column_id()
    assert column_id == "456"

@patch('publisher.zhihu.requests.Session.post')
def test_zhihu_publisher_add_to_column(mock_post):
    """测试ZhihuPublisher._add_to_column方法"""
    # 配置模拟对象
    mock_response = Mock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response
    
    # 测试添加到专栏
    config = ZhihuConfig(cookie="test_cookie")
    publisher = ZhihuPublisher(config)
    
    success = publisher._add_to_column("article123", "column456")
    assert success is True
    mock_post.assert_called_once()


def test_zhihu_publisher_disabled():
    """测试ZhihuPublisher在禁用状态下的行为"""
    config = ZhihuConfig(enabled=False)
    publisher = ZhihuPublisher(config)
    
    # 创建论文和总结对象
    paper = ArxivPaper(
        arxiv_id="2401.12345v1",
        title="Test Paper",
        authors=["Author 1"],
        published_date=datetime(2024, 1, 1),
        pdf_url="https://arxiv.org/pdf/2401.12345v1.pdf",
        abs_url="https://arxiv.org/abs/2401.12345v1",
        primary_category="cs.LG"
    )
    
    summary = PaperSummary(
        arxiv_id="2401.12345v1",
        title="Test Paper",
        authors=["Author 1"],
        published_year=2024,
        venue="arXiv"
    )
    
    # 测试禁用状态下的发布
    url = publisher.publish(summary, paper)
    assert url is None


def test_zhihu_publisher_no_cookie():
    """测试ZhihuPublisher在没有cookie的情况下的行为"""
    config = ZhihuConfig(enabled=True, cookie="")
    publisher = ZhihuPublisher(config)
    
    # 创建论文和总结对象
    paper = ArxivPaper(
        arxiv_id="2401.12345v1",
        title="Test Paper",
        authors=["Author 1"],
        published_date=datetime(2024, 1, 1),
        pdf_url="https://arxiv.org/pdf/2401.12345v1.pdf",
        abs_url="https://arxiv.org/abs/2401.12345v1",
        primary_category="cs.LG"
    )
    
    summary = PaperSummary(
        arxiv_id="2401.12345v1",
        title="Test Paper",
        authors=["Author 1"],
        published_year=2024,
        venue="arXiv"
    )
    
    # 测试无cookie状态下的发布
    url = publisher.publish(summary, paper)
    assert url is None


if __name__ == "__main__":
    test_zhihu_publisher_init()
    test_zhihu_publisher_extract_xsrf()
    test_zhihu_publisher_markdown_to_zhihu_html()
    test_zhihu_publisher_publish()
    test_zhihu_publisher_check_login()
    test_zhihu_publisher_get_user_info()
    test_zhihu_publisher_search_columns()
    test_zhihu_publisher_create_column()
    test_zhihu_publisher_get_target_column_id()
    test_zhihu_publisher_add_to_column()
    test_zhihu_publisher_disabled()
    test_zhihu_publisher_no_cookie()
    print("All tests passed!")