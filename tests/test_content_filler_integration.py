"""
集成测试：使用现有markdown文件测试content_filler的文件upload路径
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from publisher.zhihu_modules.content_filler import ContentFiller


class TestContentFillerWithRealFiles:
    """使用真实markdown文件测试ContentFiller"""

    @pytest.fixture
    def sample_paper_file(self):
        """获取项目中现有的论文总结文件"""
        # 使用项目中现有的论文总结文件
        paper_file = Path("papers/2026-02/20260225_2602.22260v1_Code_World_Models_for_Parameter_Control_in_Evoluti.md")
        if not paper_file.exists():
            # 尝试其他路径
            paper_file = Path("d:/工作区/Workspace/survey-tool/arxiv-survey/papers/2026-02/20260225_2602.22260v1_Code_World_Models_for_Parameter_Control_in_Evoluti.md")

        if not paper_file.exists():
            pytest.skip("Sample paper file not found")

        return str(paper_file)

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
        return ContentFiller(mock_page, print, lambda x: None)

    def test_upload_via_file_input_with_real_file(self, content_filler, mock_page, sample_paper_file):
        """测试使用真实论文文件通过文件输入框上传"""
        print(f"\n测试文件: {sample_paper_file}")
        print(f"文件大小: {os.path.getsize(sample_paper_file)} 字节")

        # 模拟找到文件输入框
        mock_file_input = Mock()
        mock_file_input.set_input_files = Mock()
        mock_page.query_selector = Mock(return_value=mock_file_input)

        # 执行测试
        content_filler._upload_via_file_input(sample_paper_file)

        # 验证文件输入框被正确查找
        mock_page.query_selector.assert_called()

        # 验证文件被正确设置
        abs_path = os.path.abspath(sample_paper_file)
        mock_file_input.set_input_files.assert_called_once_with(abs_path)

        print("✅ 文件上传测试通过")

    def test_fill_by_import_with_real_file(self, content_filler, mock_page, sample_paper_file):
        """测试使用真实论文文件的完整导入流程"""
        print(f"\n测试文件: {sample_paper_file}")

        # 模拟找到导入按钮
        mock_import_button = Mock()
        mock_import_button.click = Mock()
        mock_import_button.is_visible = Mock(return_value=True)

        # 模拟找到导入文档选项
        mock_import_option = Mock()
        mock_import_option.click = Mock()
        mock_import_option.is_visible = Mock(return_value=True)

        # 设置query_selector的返回值序列
        call_count = [0]
        def query_selector_side_effect(selector):
            call_count[0] += 1
            if '导入' in selector and 'button' in selector:
                return mock_import_button
            elif '导入文档' in selector:
                return mock_import_option
            return None

        mock_page.query_selector = Mock(side_effect=query_selector_side_effect)

        # 模拟_upload_file方法
        with patch.object(content_filler, '_upload_file') as mock_upload:
            content_filler._fill_by_import(sample_paper_file)

            # 验证流程
            mock_import_button.click.assert_called_once()
            mock_import_option.click.assert_called_once()
            mock_upload.assert_called_once_with(sample_paper_file)

        print("✅ 导入流程测试通过")

    def test_fallback_to_copy_paste_with_real_file(self, content_filler, mock_page, sample_paper_file):
        """测试使用真实论文文件的回退到拷贝粘贴流程"""
        print(f"\n测试文件: {sample_paper_file}")

        # 模拟未找到文件输入框
        mock_page.query_selector = Mock(return_value=None)

        # 执行测试
        with patch.object(content_filler, '_fallback_to_copy_paste') as mock_fallback:
            content_filler._upload_via_file_input(sample_paper_file)

            # 验证回退到拷贝粘贴
            mock_fallback.assert_called_once_with(sample_paper_file)

        print("✅ 回退流程测试通过")

    def test_file_content_integrity(self, content_filler, sample_paper_file):
        """测试文件内容完整性"""
        print(f"\n测试文件: {sample_paper_file}")

        # 读取文件内容
        with open(sample_paper_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 验证文件内容不为空
        assert len(content) > 0, "文件内容为空"

        # 验证文件包含预期的markdown结构
        assert '# ' in content, "文件不包含标题"
        assert '##' in content, "文件不包含二级标题"

        print(f"✅ 文件内容完整性测试通过")
        print(f"   文件大小: {len(content)} 字符")
        print(f"   包含标题: {'# ' in content}")
        print(f"   包含二级标题: {'##' in content}")


class TestContentFillerWithMultipleRealFiles:
    """使用多个真实markdown文件测试ContentFiller"""

    def get_paper_files(self):
        """获取所有可用的论文文件"""
        paper_dirs = [
            Path("papers/2026-02"),
            Path("papers/2026-03"),
            Path("d:/工作区/Workspace/survey-tool/arxiv-survey/papers/2026-02"),
            Path("d:/工作区/Workspace/survey-tool/arxiv-survey/papers/2026-03"),
        ]

        files = []
        for dir_path in paper_dirs:
            if dir_path.exists():
                files.extend(list(dir_path.glob("*.md")))

        return files[:3]  # 最多返回3个文件

    def test_upload_multiple_files(self):
        """测试上传多个真实文件"""
        paper_files = self.get_paper_files()

        if not paper_files:
            pytest.skip("No paper files found")

        print(f"\n找到 {len(paper_files)} 个论文文件")

        for paper_file in paper_files:
            print(f"\n测试文件: {paper_file.name}")
            print(f"文件大小: {os.path.getsize(paper_file)} 字节")

            # 创建模拟对象
            mock_page = Mock()
            mock_file_input = Mock()
            mock_file_input.set_input_files = Mock()
            mock_page.query_selector = Mock(return_value=mock_file_input)

            content_filler = ContentFiller(mock_page, print, lambda x: None)

            # 执行测试
            content_filler._upload_via_file_input(str(paper_file))

            # 验证
            abs_path = os.path.abspath(str(paper_file))
            mock_file_input.set_input_files.assert_called_once_with(abs_path)

            print(f"✅ {paper_file.name} 测试通过")


class TestContentFillerFileValidation:
    """测试文件验证功能"""

    @pytest.fixture
    def mock_page(self):
        """创建模拟的Playwright页面对象"""
        page = Mock()
        page.query_selector = Mock(return_value=None)
        return page

    @pytest.fixture
    def content_filler(self, mock_page):
        """创建ContentFiller实例"""
        return ContentFiller(mock_page, print, lambda x: None)

    def test_upload_nonexistent_file(self, content_filler, mock_page):
        """测试上传不存在的文件"""
        nonexistent_file = "/path/to/nonexistent/file.md"

        # 模拟找到文件输入框
        mock_file_input = Mock()
        mock_file_input.set_input_files = Mock()
        mock_page.query_selector = Mock(return_value=mock_file_input)

        # 执行测试
        with patch.object(content_filler, '_fallback_to_copy_paste') as mock_fallback:
            content_filler._upload_via_file_input(nonexistent_file)

            # 验证回退到拷贝粘贴
            mock_fallback.assert_called_once_with(nonexistent_file)

        print("✅ 不存在的文件测试通过")

    def test_upload_empty_file(self, content_filler, mock_page, tmp_path):
        """测试上传空文件"""
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("", encoding='utf-8')

        # 模拟找到文件输入框
        mock_file_input = Mock()
        mock_file_input.set_input_files = Mock()
        mock_page.query_selector = Mock(return_value=mock_file_input)

        # 执行测试
        content_filler._upload_via_file_input(str(empty_file))

        # 验证文件被正确上传
        abs_path = os.path.abspath(str(empty_file))
        mock_file_input.set_input_files.assert_called_once_with(abs_path)

        print("✅ 空文件测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
