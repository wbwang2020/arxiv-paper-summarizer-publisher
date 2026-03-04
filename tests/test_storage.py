import os
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from config.config import StorageConfig
from models.paper import ArxivPaper
from models.summary import PaperSummary
from storage.storage import PaperStorage


def test_paper_storage_init():
    """测试PaperStorage初始化"""
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        config = StorageConfig(base_dir=temp_dir)
        storage = PaperStorage(config)
        
        assert storage.config == config
        assert storage.base_dir == Path(temp_dir)
        assert storage.index_file.exists()


def test_paper_storage_generate_filename():
    """测试PaperStorage._generate_filename方法"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = StorageConfig(
            base_dir=temp_dir,
            filename_template="{date}_{arxiv_id}_{title}"
        )
        storage = PaperStorage(config)
        
        # 创建论文对象
        paper = ArxivPaper(
            arxiv_id="2401.12345v1",
            title="Test Paper Title",
            authors=["Author 1"],
            published_date=datetime(2024, 1, 1),
            pdf_url="https://arxiv.org/pdf/2401.12345v1.pdf",
            abs_url="https://arxiv.org/abs/2401.12345v1",
            primary_category="cs.LG"
        )
        
        # 测试生成文件名
        filename = storage._generate_filename(paper, "md")
        assert "20240101" in filename
        assert "2401.12345v1" in filename
        assert "Test_Paper_Title" in filename
        assert filename.endswith(".md")


def test_paper_storage_get_year_month_folder():
    """测试PaperStorage._get_year_month_folder方法"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = StorageConfig(base_dir=temp_dir)
        storage = PaperStorage(config)
        
        # 测试获取年-月文件夹
        folder = storage._get_year_month_folder(datetime(2024, 1, 15))
        assert folder == "2024-01"


def test_paper_storage_get_storage_path():
    """测试PaperStorage._get_storage_path方法"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = StorageConfig(base_dir=temp_dir)
        storage = PaperStorage(config)
        
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
        
        # 测试获取存储路径
        path = storage._get_storage_path(paper)
        assert path.exists()
        assert path.name == "2024-01"


def test_paper_storage_save_summary():
    """测试PaperStorage.save_summary方法"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = StorageConfig(
            base_dir=temp_dir,
            format="markdown"
        )
        storage = PaperStorage(config)
        
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
        
        # 测试保存总结
        file_path = storage.save_summary(summary, paper, format="markdown")
        assert os.path.exists(file_path)
        assert file_path.endswith(".md")
        
        # 测试保存为JSON格式
        file_path_json = storage.save_summary(summary, paper, format="json")
        assert os.path.exists(file_path_json)
        assert file_path_json.endswith(".json")


def test_paper_storage_load_summary():
    """测试PaperStorage.load_summary方法"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = StorageConfig(base_dir=temp_dir)
        storage = PaperStorage(config)
        
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
        
        # 保存总结
        storage.save_summary(summary, paper)
        
        # 测试加载总结
        loaded_summary = storage.load_summary("2401.12345v1")
        assert loaded_summary is not None
        assert loaded_summary.arxiv_id == "2401.12345v1"
        assert loaded_summary.title == "Test Paper"


def test_paper_storage_exists():
    """测试PaperStorage.exists方法"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = StorageConfig(base_dir=temp_dir)
        storage = PaperStorage(config)
        
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
        
        # 测试不存在的情况
        assert not storage.exists("2401.12345v1")
        
        # 保存总结后测试存在的情况
        storage.save_summary(summary, paper)
        assert storage.exists("2401.12345v1")


def test_paper_storage_exists_in_recent_months():
    """测试PaperStorage.exists_in_recent_months方法"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = StorageConfig(base_dir=temp_dir)
        storage = PaperStorage(config)
        
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
        
        # 保存总结
        storage.save_summary(summary, paper)
        
        # 测试在最近月份内存在
        assert storage.exists_in_recent_months("2401.12345v1", months=2)


def test_paper_storage_list_summaries():
    """测试PaperStorage.list_summaries方法"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = StorageConfig(base_dir=temp_dir)
        storage = PaperStorage(config)
        
        # 创建论文和总结对象
        paper1 = ArxivPaper(
            arxiv_id="2401.12345v1",
            title="Test Paper 1",
            authors=["Author 1"],
            published_date=datetime(2024, 1, 1),
            pdf_url="https://arxiv.org/pdf/2401.12345v1.pdf",
            abs_url="https://arxiv.org/abs/2401.12345v1",
            primary_category="cs.LG"
        )
        
        summary1 = PaperSummary(
            arxiv_id="2401.12345v1",
            title="Test Paper 1",
            authors=["Author 1"],
            published_year=2024,
            venue="arXiv"
        )
        
        paper2 = ArxivPaper(
            arxiv_id="2402.23456v1",
            title="Test Paper 2",
            authors=["Author 2"],
            published_date=datetime(2024, 2, 1),
            pdf_url="https://arxiv.org/pdf/2402.23456v1.pdf",
            abs_url="https://arxiv.org/abs/2402.23456v1",
            primary_category="cs.AI"
        )
        
        summary2 = PaperSummary(
            arxiv_id="2402.23456v1",
            title="Test Paper 2",
            authors=["Author 2"],
            published_year=2024,
            venue="arXiv"
        )
        
        # 保存总结
        storage.save_summary(summary1, paper1)
        storage.save_summary(summary2, paper2)
        
        # 测试列出所有总结
        summaries = storage.list_summaries()
        assert len(summaries) == 2
        
        # 测试按分类过滤
        cs_lg_summaries = storage.list_summaries(category="cs.LG")
        assert len(cs_lg_summaries) == 1
        assert cs_lg_summaries[0]["primary_category"] == "cs.LG"


def test_paper_storage_list_recent_summaries():
    """测试PaperStorage.list_recent_summaries方法"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = StorageConfig(base_dir=temp_dir)
        storage = PaperStorage(config)
        
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
        
        # 保存总结
        storage.save_summary(summary, paper)
        
        # 测试列出最近总结
        recent_summaries = storage.list_recent_summaries(months=2)
        assert len(recent_summaries) == 1
        assert recent_summaries[0]["arxiv_id"] == "2401.12345v1"


def test_paper_storage_delete_summary():
    """测试PaperStorage.delete_summary方法"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = StorageConfig(base_dir=temp_dir)
        storage = PaperStorage(config)
        
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
        
        # 保存总结
        file_path = storage.save_summary(summary, paper)
        assert os.path.exists(file_path)
        
        # 测试删除总结
        success = storage.delete_summary("2401.12345v1")
        assert success
        assert not os.path.exists(file_path)
        assert not storage.exists("2401.12345v1")


def test_paper_storage_get_stats():
    """测试PaperStorage.get_stats方法"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = StorageConfig(base_dir=temp_dir)
        storage = PaperStorage(config)
        
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
        
        # 保存总结
        storage.save_summary(summary, paper)
        
        # 测试获取统计信息
        stats = storage.get_stats()
        assert stats["total_papers"] == 1
        assert "cs.LG" in stats["by_category"]
        assert stats["by_category"]["cs.LG"] == 1
        assert 2024 in stats["by_year"]
        assert stats["by_year"][2024] == 1


def test_paper_storage_update_zhihu_publish_status():
    """测试PaperStorage.update_zhihu_publish_status方法"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = StorageConfig(base_dir=temp_dir)
        storage = PaperStorage(config)
        
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
        
        # 保存总结
        storage.save_summary(summary, paper)
        
        # 测试更新知乎发布状态
        success = storage.update_zhihu_publish_status(
            "2401.12345v1",
            True,
            "https://zhihu.com/article/12345"
        )
        assert success
        
        # 测试检查发布状态
        assert storage.is_zhihu_published("2401.12345v1")


def test_paper_storage_get_folder_brief():
    """测试PaperStorage.get_folder_brief方法"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = StorageConfig(base_dir=temp_dir)
        storage = PaperStorage(config)
        
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
        
        # 保存总结
        storage.save_summary(summary, paper)
        
        # 测试获取文件夹简报
        brief = storage.get_folder_brief("2024-01")
        assert brief is not None
        assert "papers" in brief
        assert "2401.12345v1" in brief["papers"]


if __name__ == "__main__":
    test_paper_storage_init()
    test_paper_storage_generate_filename()
    test_paper_storage_get_year_month_folder()
    test_paper_storage_get_storage_path()
    test_paper_storage_save_summary()
    test_paper_storage_load_summary()
    test_paper_storage_exists()
    test_paper_storage_exists_in_recent_months()
    test_paper_storage_list_summaries()
    test_paper_storage_list_recent_summaries()
    test_paper_storage_delete_summary()
    test_paper_storage_get_stats()
    test_paper_storage_update_zhihu_publish_status()
    test_paper_storage_get_folder_brief()
    print("All tests passed!")