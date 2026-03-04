import os
import tempfile
import yaml
from config.config import Config, ArxivConfig, AIConfig, StorageConfig, ZhihuConfig, SchedulerConfig


def test_arxiv_config_defaults():
    """测试ArxivConfig默认值"""
    config = ArxivConfig()
    assert config.keywords == []
    assert config.categories == []
    assert config.days_back == 7
    assert config.max_results == 50
    assert config.sort_by == "submittedDate"
    assert config.sort_order == "descending"


def test_ai_config_defaults():
    """测试AIConfig默认值"""
    config = AIConfig()
    assert config.provider == "deepseek"
    assert config.api_key == ""
    assert config.api_url == "https://api.deepseek.com/v1/chat/completions"
    assert config.model == "deepseek-chat"
    assert config.temperature == 0.7
    assert config.max_tokens == 8000
    assert config.max_input_tokens == 131072
    assert config.timeout == 120


def test_ai_config_get_api_key():
    """测试AIConfig.get_api_key方法"""
    # 直接返回API密钥
    config = AIConfig(api_key="test_key")
    assert config.get_api_key() == "test_key"
    
    # 从环境变量获取
    os.environ["TEST_API_KEY"] = "env_test_key"
    config = AIConfig(api_key="${TEST_API_KEY}")
    assert config.get_api_key() == "env_test_key"
    
    # 环境变量不存在
    config = AIConfig(api_key="${NON_EXISTENT_KEY}")
    assert config.get_api_key() == ""


def test_storage_config_defaults():
    """测试StorageConfig默认值"""
    config = StorageConfig()
    assert config.base_dir == "./papers"
    assert config.format == "markdown"
    assert config.filename_template == "{date}_{arxiv_id}_{title}"
    assert config.organize_by == "date"
    assert config.include_metadata is False


def test_zhihu_config_defaults():
    """测试ZhihuConfig默认值"""
    config = ZhihuConfig()
    assert config.enabled is True
    assert config.cookie == ""
    assert config.column_id is None
    assert config.username is None
    assert config.column_name is None
    assert config.create_column_if_not_exists is True
    assert config.draft_first is True
    assert config.auto_publish is False
    assert config.content_fill_mode == "copy_paste"
    assert config.debug is True


def test_zhihu_config_get_cookie():
    """测试ZhihuConfig.get_cookie方法"""
    # 直接返回Cookie
    config = ZhihuConfig(cookie="test_cookie")
    assert config.get_cookie() == "test_cookie"
    
    # 从环境变量获取
    os.environ["TEST_COOKIE"] = "env_test_cookie"
    config = ZhihuConfig(cookie="${TEST_COOKIE}")
    assert config.get_cookie() == "env_test_cookie"
    
    # 环境变量不存在
    config = ZhihuConfig(cookie="${NON_EXISTENT_COOKIE}")
    assert config.get_cookie() == ""


def test_scheduler_config_defaults():
    """测试SchedulerConfig默认值"""
    config = SchedulerConfig()
    assert config.enabled is True
    assert config.cron == "0 9 * * *"
    assert config.timezone == "Asia/Shanghai"


def test_config_from_yaml():
    """测试从YAML文件加载配置"""
    # 创建临时YAML文件
    yaml_content = """
    arxiv:
      keywords:
        - "World Model"
      categories:
        - "cs.LG"
        - "cs.AI"
      days_back: 14
      max_results: 100
      sort_by: "submittedDate"
      sort_order: "descending"
    
    ai:
      provider: "deepseek"
      api_key: "test_api_key"
      model: "deepseek-chat"
    
    storage:
      base_dir: "./test_papers"
      include_metadata: true
    
    zhihu:
      enabled: true
      cookie: "test_cookie"
      column_name: "测试专栏"
    
    scheduler:
      enabled: true
      cron: "0 10 * * *"
    """
    
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        temp_file = f.name
    
    try:
        config = Config.from_yaml(temp_file)
        assert config.arxiv.keywords == ["World Model"]
        assert config.arxiv.categories == ["cs.LG", "cs.AI"]
        assert config.arxiv.days_back == 14
        assert config.arxiv.max_results == 100
        assert config.ai.api_key == "test_api_key"
        assert config.storage.base_dir == "./test_papers"
        assert config.storage.include_metadata is True
        assert config.zhihu.cookie == "test_cookie"
        assert config.zhihu.column_name == "测试专栏"
        assert config.scheduler.cron == "0 10 * * *"
    finally:
        os.unlink(temp_file)


def test_config_from_env():
    """测试从环境变量加载配置"""
    # 设置环境变量
    os.environ["ARXIV_KEYWORDS"] = "World Model,LLM"
    os.environ["ARXIV_CATEGORIES"] = "cs.LG,cs.AI"
    os.environ["ARXIV_DAYS_BACK"] = "7"
    os.environ["ARXIV_MAX_RESULTS"] = "50"
    os.environ["DEEPSEEK_API_KEY"] = "env_api_key"
    os.environ["STORAGE_BASE_DIR"] = "./env_papers"
    os.environ["STORAGE_INCLUDE_METADATA"] = "true"
    os.environ["ZHIHU_ENABLED"] = "true"
    os.environ["ZHIHU_COOKIE"] = "env_cookie"
    os.environ["ZHIHU_COLUMN_ID"] = "env_column_id"
    os.environ["ZHIHU_COLUMN_NAME"] = "env_column_name"
    os.environ["ZHIHU_CREATE_COLUMN"] = "true"
    
    config = Config.from_env()
    assert config.arxiv.keywords == ["World Model", "LLM"]
    assert config.arxiv.categories == ["cs.LG", "cs.AI"]
    assert config.arxiv.days_back == 7
    assert config.arxiv.max_results == 50
    assert config.ai.api_key == "env_api_key"
    assert config.storage.base_dir == "./env_papers"
    assert config.storage.include_metadata is True
    assert config.zhihu.enabled is True
    assert config.zhihu.cookie == "env_cookie"
    assert config.zhihu.column_id == "env_column_id"
    assert config.zhihu.column_name == "env_column_name"
    assert config.zhihu.create_column_if_not_exists is True


def test_config_to_yaml():
    """测试保存配置到YAML文件"""
    config = Config(
        arxiv=ArxivConfig(
            keywords=["World Model"],
            categories=["cs.LG"],
            days_back=7
        ),
        storage=StorageConfig(
            base_dir="./test_papers",
            include_metadata=True
        )
    )
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        temp_file = f.name
    
    try:
        config.to_yaml(temp_file)
        
        # 读取并验证
        with open(temp_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        assert data['arxiv']['keywords'] == ["World Model"]
        assert data['arxiv']['categories'] == ["cs.LG"]
        assert data['arxiv']['days_back'] == 7
        assert data['storage']['base_dir'] == "./test_papers"
        assert data['storage']['include_metadata'] is True
    finally:
        os.unlink(temp_file)


if __name__ == "__main__":
    test_arxiv_config_defaults()
    test_ai_config_defaults()
    test_ai_config_get_api_key()
    test_storage_config_defaults()
    test_zhihu_config_defaults()
    test_zhihu_config_get_cookie()
    test_scheduler_config_defaults()
    test_config_from_yaml()
    test_config_from_env()
    test_config_to_yaml()
    print("All tests passed!")