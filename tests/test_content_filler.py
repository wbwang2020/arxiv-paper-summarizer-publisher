"""
测试知乎文章主体填充模块
特别是"通过文件输入框上传文件"的发布路径
"""
import os
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

# 导入被测试的模块
from publisher.zhihu_modules.content_filler import ContentFiller


class TestContentFillerFileUpload:
    """测试ContentFiller的文件上传功能"""

    @pytest.fixture
    def mock_page(self):
        """创建模拟的Playwright页面对象"""
        page = Mock()
        page.query_selector = Mock(return_value=None)
        page.keyboard = Mock()
        page.evaluate = Mock(return_value=True)
        return page

    @pytest.fixture
    def mock_debug_funcs(self):
        """创建调试函数"""
        return lambda x: None, lambda x: None

    @pytest.fixture
    def content_filler(self, mock_page, mock_debug_funcs):
        """创建ContentFiller实例"""
        debug_print, debug_screenshot = mock_debug_funcs
        return ContentFiller(mock_page, debug_print, debug_screenshot)

    @pytest.fixture
    def temp_md_file(self, tmp_path):
        """创建临时Markdown文件"""
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

    def test_upload_via_file_input_with_valid_file_input(self, content_filler, mock_page, temp_md_file):
        """测试通过文件输入框上传文件 - 成功场景"""
        # 模拟找到文件输入框
        mock_file_input = Mock()
        mock_file_input.set_input_files = Mock()
        mock_page.query_selector = Mock(return_value=mock_file_input)

        # 执行测试
        content_filler._upload_via_file_input(temp_md_file)

        # 验证文件输入框被正确查找（第一个selector成功即可）
        first_call = mock_page.query_selector.call_args_list[0]
        assert first_call[0][0] == 'input[type="file"]'

        # 验证文件被正确设置
        abs_path = os.path.abspath(temp_md_file)
        mock_file_input.set_input_files.assert_called_once_with(abs_path)

    def test_upload_via_file_input_file_not_found(self, content_filler, mock_page):
        """测试通过文件输入框上传文件 - 文件不存在场景"""
        # 模拟找到文件输入框
        mock_file_input = Mock()
        mock_file_input.set_input_files = Mock()
        mock_page.query_selector = Mock(return_value=mock_file_input)

        # 使用不存在的文件路径
        non_existent_file = "/path/to/nonexistent/file.md"

        # 执行测试 - 不应抛出异常，应回退到拷贝粘贴
        with patch.object(content_filler, '_fallback_to_copy_paste') as mock_fallback:
            content_filler._upload_via_file_input(non_existent_file)

            # 验证回退到拷贝粘贴
            mock_fallback.assert_called_once_with(non_existent_file)

    def test_upload_via_file_input_no_file_input_found(self, content_filler, mock_page, temp_md_file):
        """测试通过文件输入框上传文件 - 未找到文件输入框场景"""
        # 模拟未找到文件输入框
        mock_page.query_selector = Mock(return_value=None)

        # 执行测试
        with patch.object(content_filler, '_fallback_to_copy_paste') as mock_fallback:
            content_filler._upload_via_file_input(temp_md_file)

            # 验证回退到拷贝粘贴
            mock_fallback.assert_called_once_with(temp_md_file)

    def test_upload_via_file_input_exception_handling(self, content_filler, mock_page, temp_md_file):
        """测试通过文件输入框上传文件 - 异常处理场景"""
        # 模拟找到文件输入框但设置文件时抛出异常
        mock_file_input = Mock()
        mock_file_input.set_input_files = Mock(side_effect=Exception("Upload failed"))
        mock_page.query_selector = Mock(return_value=mock_file_input)

        # 执行测试 - 不应抛出异常，应回退到拷贝粘贴
        with patch.object(content_filler, '_fallback_to_copy_paste') as mock_fallback:
            content_filler._upload_via_file_input(temp_md_file)

            # 验证回退到拷贝粘贴
            mock_fallback.assert_called_once_with(temp_md_file)

    def test_upload_via_file_input_selector_priority(self, content_filler, mock_page, temp_md_file):
        """测试文件输入框选择器的优先级"""
        # 按优先级顺序模拟文件输入框
        mock_inputs = {
            'input[type="file"]': Mock(),
            'input[accept*=".md"]': Mock(),
            'input[accept*=".doc"]': Mock(),
            'input[name="file"]': Mock(),
        }

        call_count = [0]

        def side_effect(selector):
            # 第三个选择器才返回有效结果
            call_count[0] += 1
            if call_count[0] >= 3:
                return mock_inputs.get(selector)
            return None

        mock_page.query_selector = Mock(side_effect=side_effect)

        # 执行测试
        content_filler._upload_via_file_input(temp_md_file)

        # 验证使用了第三个选择器
        assert call_count[0] == 3, f"期望调用3次，实际调用{call_count[0]}次"

    def test_upload_via_file_input_absolute_path(self, content_filler, mock_page, temp_md_file):
        """测试文件路径转换为绝对路径"""
        mock_file_input = Mock()
        mock_file_input.set_input_files = Mock()
        mock_page.query_selector = Mock(return_value=mock_file_input)

        # 使用相对路径
        rel_path = os.path.relpath(temp_md_file)

        # 执行测试
        content_filler._upload_via_file_input(rel_path)

        # 验证使用了绝对路径
        abs_path = os.path.abspath(rel_path)
        mock_file_input.set_input_files.assert_called_once_with(abs_path)


class TestContentFillerImportDocument:
    """测试导入文档方式的完整流程"""

    @pytest.fixture
    def mock_page(self):
        """创建模拟的Playwright页面对象"""
        page = Mock()
        page.query_selector = Mock(return_value=None)
        page.keyboard = Mock()
        return page

    @pytest.fixture
    def content_filler(self, mock_page):
        """创建ContentFiller实例"""
        return ContentFiller(mock_page, lambda x: None, lambda x: None)

    @pytest.fixture
    def temp_md_file(self, tmp_path):
        """创建临时Markdown文件"""
        md_file = tmp_path / "test_paper.md"
        md_content = "# Test Paper\n\nThis is test content."
        md_file.write_text(md_content, encoding='utf-8')
        return str(md_file)

    def test_fill_by_import_success_path(self, content_filler, mock_page, temp_md_file):
        """测试导入文档成功路径"""
        # 模拟找到导入按钮
        mock_import_button = Mock()
        mock_import_button.click = Mock()

        # 模拟找到导入文档选项
        mock_import_option = Mock()
        mock_import_option.click = Mock()

        # 设置query_selector的返回值序列
        def query_selector_side_effect(selector):
            if '导入' in selector and 'button' in selector:
                return mock_import_button
            elif '导入文档' in selector:
                return mock_import_option
            return None

        mock_page.query_selector = Mock(side_effect=query_selector_side_effect)

        # 模拟_upload_file方法
        with patch.object(content_filler, '_upload_file') as mock_upload:
            content_filler._fill_by_import(temp_md_file)

            # 验证流程
            mock_import_button.click.assert_called_once()
            mock_import_option.click.assert_called_once()
            mock_upload.assert_called_once_with(temp_md_file)

    def test_fill_by_import_no_import_button(self, content_filler, mock_page, temp_md_file):
        """测试导入文档 - 未找到导入按钮"""
        # 模拟未找到导入按钮
        mock_page.query_selector = Mock(return_value=None)

        with patch.object(content_filler, '_fallback_to_copy_paste') as mock_fallback:
            content_filler._fill_by_import(temp_md_file)

            # 验证回退到拷贝粘贴
            mock_fallback.assert_called_once_with(temp_md_file)

    def test_fill_by_import_no_import_option(self, content_filler, mock_page, temp_md_file):
        """测试导入文档 - 未找到导入选项"""
        # 模拟找到导入按钮但未找到导入选项
        mock_import_button = Mock()
        mock_import_button.click = Mock()

        def query_selector_side_effect(selector):
            if '导入' in selector and 'button' in selector:
                return mock_import_button
            return None

        mock_page.query_selector = Mock(side_effect=query_selector_side_effect)

        with patch.object(content_filler, '_fallback_to_copy_paste') as mock_fallback:
            content_filler._fill_by_import(temp_md_file)

            # 验证点击了导入按钮，但回退到拷贝粘贴
            mock_import_button.click.assert_called_once()
            mock_page.keyboard.press.assert_called_once_with('Escape')
            mock_fallback.assert_called_once_with(temp_md_file)

    def test_fill_by_import_exception_handling(self, content_filler, mock_page, temp_md_file):
        """测试导入文档 - 异常处理"""
        # 模拟导入按钮点击时抛出异常
        mock_import_button = Mock()
        mock_import_button.click = Mock(side_effect=Exception("Click failed"))

        mock_page.query_selector = Mock(return_value=mock_import_button)

        with patch.object(content_filler, '_fallback_to_copy_paste') as mock_fallback:
            content_filler._fill_by_import(temp_md_file)

            # 验证回退到拷贝粘贴
            mock_fallback.assert_called_once_with(temp_md_file)


class TestContentFillerIntegration:
    """测试ContentFiller的集成场景"""

    @pytest.fixture
    def mock_page(self):
        """创建模拟的Playwright页面对象"""
        page = Mock()
        page.query_selector = Mock(return_value=None)
        page.keyboard = Mock()
        page.evaluate = Mock(return_value=True)
        return page

    @pytest.fixture
    def content_filler(self, mock_page):
        """创建ContentFiller实例"""
        return ContentFiller(mock_page, lambda x: None, lambda x: None)

    @pytest.fixture
    def temp_md_file(self, tmp_path):
        """创建临时Markdown文件"""
        md_file = tmp_path / "test_paper.md"
        md_content = "# Test Paper\n\nThis is test content."
        md_file.write_text(md_content, encoding='utf-8')
        return str(md_file)

    def test_fill_content_import_document_mode(self, content_filler, mock_page, temp_md_file):
        """测试fill_content使用import_document模式"""
        # 模拟找到内容编辑器
        mock_editor = Mock()

        # 设置query_selector的返回值
        def query_selector_side_effect(selector):
            if 'DraftEditor' in selector or 'contenteditable' in selector:
                return mock_editor
            elif '导入' in selector:
                mock_btn = Mock()
                mock_btn.click = Mock()
                mock_btn.is_visible = Mock(return_value=True)
                return mock_btn
            elif '导入文档' in selector:
                mock_opt = Mock()
                mock_opt.click = Mock()
                mock_opt.is_visible = Mock(return_value=True)
                return mock_opt
            return None

        mock_page.query_selector = Mock(side_effect=query_selector_side_effect)
        mock_page.wait_for_selector = Mock(return_value=mock_editor)

        # 模拟_upload_via_file_input方法
        with patch.object(content_filler, '_upload_via_file_input') as mock_upload:
            result = content_filler.fill_content(
                content="# Test\n\nContent",
                file_path=temp_md_file,
                content_fill_mode='import_document'
            )

            # 验证结果
            assert result is True
            mock_upload.assert_called_once_with(temp_md_file)

    def test_fill_content_fallback_when_import_fails(self, content_filler, mock_page, temp_md_file):
        """测试当导入失败时回退到拷贝粘贴"""
        # 模拟找到内容编辑器
        mock_editor = Mock()
        mock_page.wait_for_selector = Mock(return_value=mock_editor)

        # 模拟_fill_by_import抛出异常
        with patch.object(content_filler, '_fill_by_import', side_effect=Exception("Import failed")):
            with patch.object(content_filler, '_fill_by_copy_paste') as mock_copy_paste:
                # 这里应该抛出异常，因为_fill_by_import失败了
                with pytest.raises(Exception):
                    content_filler.fill_content(
                        content="# Test\n\nContent",
                        file_path=temp_md_file,
                        content_fill_mode='import_document'
                    )


class TestContentFillerFileSizeHandling:
    """测试文件大小处理"""

    @pytest.fixture
    def mock_page(self):
        """创建模拟的Playwright页面对象"""
        page = Mock()
        page.query_selector = Mock(return_value=None)
        return page

    @pytest.fixture
    def content_filler(self, mock_page):
        """创建ContentFiller实例"""
        return ContentFiller(mock_page, lambda x: None, lambda x: None)

    def test_upload_large_file(self, content_filler, mock_page, tmp_path):
        """测试上传大文件"""
        # 创建大文件（1MB）
        large_file = tmp_path / "large_paper.md"
        large_content = "# Large Paper\n\n" + "x" * (1024 * 1024)
        large_file.write_text(large_content, encoding='utf-8')

        mock_file_input = Mock()
        mock_file_input.set_input_files = Mock()
        mock_page.query_selector = Mock(return_value=mock_file_input)

        # 执行测试
        content_filler._upload_via_file_input(str(large_file))

        # 验证文件被正确上传
        abs_path = os.path.abspath(str(large_file))
        mock_file_input.set_input_files.assert_called_once_with(abs_path)

    def test_upload_empty_file(self, content_filler, mock_page, tmp_path):
        """测试上传空文件"""
        # 创建空文件
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("", encoding='utf-8')

        mock_file_input = Mock()
        mock_file_input.set_input_files = Mock()
        mock_page.query_selector = Mock(return_value=mock_file_input)

        # 执行测试
        content_filler._upload_via_file_input(str(empty_file))

        # 验证文件被正确上传
        abs_path = os.path.abspath(str(empty_file))
        mock_file_input.set_input_files.assert_called_once_with(abs_path)


class TestContentFillerPathHandling:
    """测试路径处理"""

    @pytest.fixture
    def mock_page(self):
        """创建模拟的Playwright页面对象"""
        page = Mock()
        page.query_selector = Mock(return_value=None)
        return page

    @pytest.fixture
    def content_filler(self, mock_page):
        """创建ContentFiller实例"""
        return ContentFiller(mock_page, lambda x: None, lambda x: None)

    def test_upload_with_relative_path(self, content_filler, mock_page, tmp_path):
        """测试使用相对路径上传"""
        # 创建测试文件
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test", encoding='utf-8')

        # 切换到临时目录
        original_cwd = os.getcwd()
        os.chdir(str(tmp_path))

        try:
            mock_file_input = Mock()
            mock_file_input.set_input_files = Mock()
            mock_page.query_selector = Mock(return_value=mock_file_input)

            # 使用相对路径
            content_filler._upload_via_file_input("test.md")

            # 验证使用了绝对路径
            abs_path = os.path.abspath("test.md")
            mock_file_input.set_input_files.assert_called_once_with(abs_path)
        finally:
            os.chdir(original_cwd)

    def test_upload_with_special_characters_in_path(self, content_filler, mock_page, tmp_path):
        """测试路径中包含特殊字符"""
        # 创建包含特殊字符的文件
        special_dir = tmp_path / "folder with spaces"
        special_dir.mkdir()
        test_file = special_dir / "file with spaces.md"
        test_file.write_text("# Test", encoding='utf-8')

        mock_file_input = Mock()
        mock_file_input.set_input_files = Mock()
        mock_page.query_selector = Mock(return_value=mock_file_input)

        # 执行测试
        content_filler._upload_via_file_input(str(test_file))

        # 验证文件被正确上传
        abs_path = os.path.abspath(str(test_file))
        mock_file_input.set_input_files.assert_called_once_with(abs_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
