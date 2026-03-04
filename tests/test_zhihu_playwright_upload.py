"""
测试zhihu_playwright模块通过上传markdown文件到知乎编辑器的发布模式
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from publisher.zhihu_playwright import ZhihuPlaywrightPublisher
from config import ZhihuConfig
from models import ArxivPaper, PaperSummary


class TestZhihuPlaywrightFileUpload:
    """测试ZhihuPlaywrightPublisher的文件上传功能"""

    @pytest.fixture
    def zhihu_config(self):
        """创建知乎配置"""
        return ZhihuConfig(
            enabled=True,
            cookie="test_cookie=value; _xsrf=test_xsrf",
            column_id="test_column_id",
            draft_first=True,
            content_fill_mode='import_document'  # 使用导入文档模式
        )

    @pytest.fixture
    def sample_paper(self):
        """创建示例论文"""
        return ArxivPaper(
            arxiv_id="2401.12345",
            title="Test Paper Title",
            authors=["Author 1", "Author 2"],
            abstract="Test abstract",
            categories=["cs.LG"],
            published_date=datetime.now(),
            pdf_url="https://arxiv.org/pdf/2401.12345",
            abs_url="https://arxiv.org/abs/2401.12345",
            primary_category="cs.LG"
        )

    @pytest.fixture
    def sample_summary(self):
        """创建示例论文总结"""
        return PaperSummary(
            arxiv_id="2401.12345",
            title="Test Paper Title",
            authors=["Author 1", "Author 2"],
            published_year=2024,
            venue="arXiv"
        )

    @pytest.fixture
    def sample_md_file(self, tmp_path):
        """创建示例markdown文件"""
        md_file = tmp_path / "test_paper.md"
        md_content = """# Test Paper Title

## 1. 基本信息
- **论文标题**: Test Paper
- **作者**: Author 1, Author 2
- **发表年份**: 2024

## 2. 研究动机
This is a test motivation section.

## 3. 核心假设
Test hypothesis.
"""
        md_file.write_text(md_content, encoding='utf-8')
        return str(md_file)

    @pytest.fixture
    def mock_playwright(self):
        """创建模拟的Playwright对象"""
        mock_pw = Mock()
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()

        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        return mock_pw, mock_browser, mock_context, mock_page

    def test_publish_from_file_reads_file_content(self, zhihu_config, sample_paper, sample_md_file):
        """测试publish_from_file方法读取文件内容"""
        publisher = ZhihuPlaywrightPublisher(zhihu_config)

        # 模拟浏览器初始化
        with patch.object(publisher, '_init_browser'):
            with patch.object(publisher, '_close_browser'):
                with patch.object(publisher, '_fill_editor') as mock_fill:
                    with patch.object(publisher, '_publish_article') as mock_publish:
                        mock_publish.return_value = "https://zhuanlan.zhihu.com/p/12345"

                        # 执行测试
                        result = publisher.publish_from_file(sample_md_file, sample_paper)

                        # 验证_fill_editor被调用，且传入了文件路径
                        mock_fill.assert_called_once()
                        call_args = mock_fill.call_args
                        assert call_args[1]['file_path'] == sample_md_file

    def test_publish_from_file_with_import_document_mode(self, zhihu_config, sample_paper, sample_md_file):
        """测试使用import_document模式发布"""
        zhihu_config.content_fill_mode = 'import_document'
        publisher = ZhihuPlaywrightPublisher(zhihu_config)

        # 模拟浏览器初始化
        with patch.object(publisher, '_init_browser'):
            with patch.object(publisher, '_close_browser'):
                with patch.object(publisher, '_fill_editor') as mock_fill:
                    with patch.object(publisher, '_publish_article') as mock_publish:
                        mock_publish.return_value = "https://zhuanlan.zhihu.com/p/12345"

                        # 执行测试
                        result = publisher.publish_from_file(sample_md_file, sample_paper)

                        # 验证_fill_editor被调用
                        mock_fill.assert_called_once()

    def test_fill_editor_calls_content_filler_with_file_path(self, zhihu_config, sample_md_file):
        """测试_fill_editor方法调用content_filler并传入文件路径"""
        publisher = ZhihuPlaywrightPublisher(zhihu_config)

        # 模拟页面对象
        mock_page = Mock()
        publisher.page = mock_page

        # 模拟content_filler
        mock_content_filler = Mock()
        mock_content_filler.fill_content = Mock(return_value=True)
        publisher.content_filler = mock_content_filler

        # 模拟title_handler和publish_settings_handler
        publisher.title_handler = Mock()
        publisher.publish_settings_handler = Mock()

        # 执行测试
        publisher._fill_editor("Test Title", "Test Content", sample_md_file)

        # 验证content_filler.fill_content被调用
        mock_content_filler.fill_content.assert_called_once()
        call_args = mock_content_filler.fill_content.call_args

        # 验证传入了文件路径和content_fill_mode
        assert call_args[1]['file_path'] == sample_md_file
        assert call_args[1]['content_fill_mode'] == 'import_document'

    def test_fill_editor_uses_config_content_fill_mode(self, zhihu_config, sample_md_file):
        """测试_fill_editor使用配置中的content_fill_mode"""
        zhihu_config.content_fill_mode = 'copy_paste'
        publisher = ZhihuPlaywrightPublisher(zhihu_config)

        # 模拟页面对象
        mock_page = Mock()
        publisher.page = mock_page

        # 模拟content_filler
        mock_content_filler = Mock()
        mock_content_filler.fill_content = Mock(return_value=True)
        publisher.content_filler = mock_content_filler

        # 模拟title_handler和publish_settings_handler
        publisher.title_handler = Mock()
        publisher.publish_settings_handler = Mock()

        # 执行测试
        publisher._fill_editor("Test Title", "Test Content", sample_md_file)

        # 验证content_filler.fill_content被调用，且使用了copy_paste模式
        mock_content_filler.fill_content.assert_called_once()
        call_args = mock_content_filler.fill_content.call_args
        assert call_args[1]['content_fill_mode'] == 'copy_paste'

    def test_publish_from_file_handles_file_not_found(self, zhihu_config, sample_paper):
        """测试publish_from_file处理文件不存在的情况"""
        publisher = ZhihuPlaywrightPublisher(zhihu_config)

        # 使用不存在的文件路径
        nonexistent_file = "/path/to/nonexistent/file.md"

        # 执行测试 - 应该抛出FileNotFoundError
        with pytest.raises(FileNotFoundError):
            publisher.publish_from_file(nonexistent_file, sample_paper)

    def test_publish_from_file_integration(self, zhihu_config, sample_paper, sample_md_file):
        """测试publish_from_file的完整流程"""
        publisher = ZhihuPlaywrightPublisher(zhihu_config)

        # 模拟整个流程
        with patch.object(publisher, '_init_browser') as mock_init:
            with patch.object(publisher, '_close_browser') as mock_close:
                with patch.object(publisher, '_fill_editor') as mock_fill:
                    with patch.object(publisher, '_publish_article') as mock_publish:
                        mock_publish.return_value = "https://zhuanlan.zhihu.com/p/12345"

                        # 执行测试
                        result = publisher.publish_from_file(sample_md_file, sample_paper)

                        # 验证流程
                        mock_init.assert_called_once()
                        mock_fill.assert_called_once()
                        mock_publish.assert_called_once()
                        mock_close.assert_called_once()

                        # 验证返回结果
                        assert result == "https://zhuanlan.zhihu.com/p/12345"


class TestZhihuPlaywrightWithRealFiles:
    """使用真实markdown文件测试ZhihuPlaywrightPublisher"""

    def get_real_paper_file(self):
        """获取项目中真实的论文文件"""
        paper_files = [
            Path("papers/2026-02/20260225_2602.22260v1_Code_World_Models_for_Parameter_Control_in_Evoluti.md"),
            Path("d:/工作区/Workspace/survey-tool/arxiv-survey/papers/2026-02/20260225_2602.22260v1_Code_World_Models_for_Parameter_Control_in_Evoluti.md"),
        ]

        for file_path in paper_files:
            if file_path.exists():
                return str(file_path)

        return None

    @pytest.fixture
    def zhihu_config(self):
        """创建知乎配置"""
        return ZhihuConfig(
            enabled=True,
            cookie="test_cookie=value; _xsrf=test_xsrf",
            column_id="test_column_id",
            draft_first=True,
            content_fill_mode='import_document'
        )

    @pytest.fixture
    def sample_paper(self):
        """创建示例论文"""
        from datetime import datetime
        return ArxivPaper(
            arxiv_id="2401.12345",
            title="Test Paper Title",
            authors=["Author 1", "Author 2"],
            abstract="Test abstract",
            categories=["cs.LG"],
            published_date=datetime.now(),
            pdf_url="https://arxiv.org/pdf/2401.12345",
            abs_url="https://arxiv.org/abs/2401.12345",
            primary_category="cs.LG"
        )

    def test_publish_from_file_with_real_paper(self, zhihu_config, sample_paper):
        """测试使用真实论文文件发布"""
        real_file = self.get_real_paper_file()

        if not real_file:
            pytest.skip("No real paper file found")

        print(f"\n使用真实文件: {real_file}")
        print(f"文件大小: {os.path.getsize(real_file)} 字节")

        publisher = ZhihuPlaywrightPublisher(zhihu_config)

        # 验证文件内容可以被读取
        with open(real_file, 'r', encoding='utf-8') as f:
            content = f.read()

        assert len(content) > 0
        assert '# ' in content

        # 模拟发布流程
        with patch.object(publisher, '_init_browser'):
            with patch.object(publisher, '_close_browser'):
                with patch.object(publisher, '_fill_editor') as mock_fill:
                    with patch.object(publisher, '_publish_article') as mock_publish:
                        mock_publish.return_value = "https://zhuanlan.zhihu.com/p/12345"

                        result = publisher.publish_from_file(real_file, sample_paper)

                        # 验证_fill_editor被调用，且传入了文件路径
                        mock_fill.assert_called_once()
                        call_args = mock_fill.call_args
                        assert call_args[1]['file_path'] == real_file

        print("✅ 真实文件测试通过")


class TestContentFillerIntegration:
    """测试ContentFiller与ZhihuPlaywrightPublisher的集成"""

    @pytest.fixture
    def zhihu_config(self):
        """创建知乎配置"""
        return ZhihuConfig(
            enabled=True,
            cookie="test_cookie=value; _xsrf=test_xsrf",
            column_id="test_column_id",
            draft_first=True,
            content_fill_mode='import_document'
        )

    def test_content_filler_import_document_mode(self, zhihu_config, tmp_path):
        """测试ContentFiller的import_document模式"""
        from publisher.zhihu_modules import ContentFiller

        # 创建测试文件
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\n\nContent", encoding='utf-8')

        # 创建模拟页面对象
        mock_page = Mock()

        # 模拟找到内容编辑器
        mock_editor = Mock()
        mock_page.wait_for_selector = Mock(return_value=mock_editor)

        # 模拟找到导入按钮和导入选项
        mock_import_button = Mock()
        mock_import_button.click = Mock()
        mock_import_button.is_visible = Mock(return_value=True)

        mock_import_option = Mock()
        mock_import_option.click = Mock()
        mock_import_option.is_visible = Mock(return_value=True)

        # 设置query_selector的返回值
        call_count = [0]
        def query_selector_side_effect(selector):
            call_count[0] += 1
            if '导入' in selector and 'button' in selector:
                return mock_import_button
            elif '导入文档' in selector:
                return mock_import_option
            return None

        mock_page.query_selector = Mock(side_effect=query_selector_side_effect)

        # 创建ContentFiller实例
        content_filler = ContentFiller(mock_page, print, lambda x: None)

        # 模拟_upload_file方法
        with patch.object(content_filler, '_upload_file') as mock_upload:
            # 执行测试
            result = content_filler.fill_content(
                content="# Test\n\nContent",
                file_path=str(test_file),
                content_fill_mode='import_document'
            )

            # 验证结果
            assert result is True
            mock_upload.assert_called_once_with(str(test_file))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
