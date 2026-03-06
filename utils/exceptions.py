"""
自定义异常类
用于处理系统运行过程中的特定错误情况
"""


class ArxivSurveyError(Exception):
    """基础异常类"""
    pass


class APIError(ArxivSurveyError):
    """AI API 错误"""
    
    def __init__(self, message: str, status_code: int = None, response_text: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
        
    def __str__(self):
        if self.status_code:
            return f"API错误 (状态码: {self.status_code}): {self.args[0]}"
        return f"API错误: {self.args[0]}"


class APIKeyError(APIError):
    """API密钥错误或无效"""
    pass


class APITimeoutError(APIError):
    """API请求超时"""
    pass


class APIRateLimitError(APIError):
    """API请求频率限制"""
    pass


class ZhihuLoginError(ArxivSurveyError):
    """知乎登录错误"""
    
    def __init__(self, message: str, cookie_valid: bool = False):
        super().__init__(message)
        self.cookie_valid = cookie_valid
        
    def __str__(self):
        return f"知乎登录失败: {self.args[0]}"


class ZhihuCookieError(ZhihuLoginError):
    """知乎Cookie无效或过期"""
    pass


class ZhihuPublishError(ArxivSurveyError):
    """知乎发布错误"""
    pass


class ConfigurationError(ArxivSurveyError):
    """配置错误"""
    pass
