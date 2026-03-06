import re
import time
from typing import Optional

import requests

from config import AIConfig, Config
from models import ArxivPaper, PaperSummary, FigureTableInfo, ReferenceInfo
from utils import get_logger, chunk_text, estimate_tokens, get_output_handler, get_log_level
from utils.exceptions import APIError, APIKeyError, APITimeoutError, APIRateLimitError

logger = get_logger()

output_handler = None  # 延迟初始化


class PaperSummarizer:
    """论文AI总结器"""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.api_key = config.get_api_key()
        self.system_prompt = config.system_prompt
        self.prompt_template = config.prompt_template
        self.section_mappings = self._build_section_mappings()
        
        # 初始化输出处理器
        global output_handler
        if output_handler is None:
            # 加载配置以获取输出设置
            try:
                full_config = Config.from_yaml("config/config.yaml")
                summarizer_config = full_config.output.get_module_config("summarizer")
                log_level = get_log_level(summarizer_config.log_level)
                output_handler = get_output_handler(
                    "summarizer", 
                    logger, 
                    debug=summarizer_config.debug, 
                    log_level=log_level, 
                    enable_debug=summarizer_config.enable_debug
                )
            except Exception as e:
                # 如果加载失败，使用默认设置
                output_handler = get_output_handler("summarizer", logger)
        
        if not self.api_key:
            output_handler.warning("AI API密钥未配置")
    
    def _build_section_mappings(self) -> dict:
        """
        根据配置构建章节映射
        
        Returns:
            章节编号到字段名的映射字典
        """
        mappings = {}
        if hasattr(self.config, 'summary_sections') and self.config.summary_sections:
            for section in self.config.summary_sections:
                mappings[section.section_number] = {
                    'field_name': section.field_name,
                    'description': section.description,
                    'field_type': section.field_type
                }
        return mappings
    
    def summarize(
        self,
        paper: ArxivPaper,
        content: str,
        max_retries: int = 3
    ) -> PaperSummary:
        """
        对论文进行AI总结
        
        Args:
            paper: 论文信息
            content: 论文全文内容
            max_retries: 最大重试次数
            
        Returns:
            论文总结对象
        """
        start_time = time.time()
        
        # 构建提示词
        prompt = self._build_prompt(paper, content)
        
        # 调用API
        response_text = self._call_api_with_retry(prompt, max_retries)
        
        # 解析响应
        summary = self._parse_response(response_text, paper)
        
        # 设置元数据
        summary.ai_model = self.config.model
        summary.processing_time = time.time() - start_time
        
        output_handler.info(f"总结论文 {paper.arxiv_id} 完成，耗时 {summary.processing_time:.2f}秒")
        
        return summary
    
    def _build_prompt(self, paper: ArxivPaper, content: str) -> str:
        """构建提示词"""
        # 计算提示词模板的token数
        template_tokens = estimate_tokens(self.prompt_template.format(
            title=paper.title,
            authors=", ".join(paper.authors),
            year=paper.published_date.year,
            arxiv_id=paper.arxiv_id,
            abstract=paper.abstract,
            content=""
        ))
        
        # 计算系统提示词的token数
        system_tokens = estimate_tokens(self.system_prompt)
        
        # 计算可用的输入token数
        available_tokens = self.config.max_input_tokens - template_tokens - system_tokens - 1000  # 留1000 token的缓冲区
        
        # 计算最大内容长度（假设1 token ≈ 3 chars）
        max_content_length = available_tokens * 3
        
        if len(content) > max_content_length:
            output_handler.warning(f"论文内容过长 ({len(content)} 字符)，截断到 {max_content_length} (约{available_tokens} tokens)")
            content = content[:max_content_length] + "\n\n[内容已截断...]"
        
        return self.prompt_template.format(
            title=paper.title,
            authors=", ".join(paper.authors),
            year=paper.published_date.year,
            arxiv_id=paper.arxiv_id,
            abstract=paper.abstract,
            content=content
        )
    
    def _call_api_with_retry(self, prompt: str, max_retries: int) -> str:
        """带重试的API调用"""
        last_error = None
        for attempt in range(max_retries):
            try:
                return self._call_api(prompt)
            except APIKeyError as e:
                # API密钥错误，不需要重试，直接抛出
                output_handler.error(f"API密钥错误，停止重试: {e}")
                raise
            except APIRateLimitError as e:
                # 频率限制错误，等待更长时间后重试
                output_handler.warning(f"API频率限制 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 2)  # 更长的指数退避
                    output_handler.info(f"{wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    last_error = e
            except APITimeoutError as e:
                # 超时错误，可以重试
                output_handler.warning(f"API请求超时 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    output_handler.info(f"{wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    last_error = e
            except APIError as e:
                # 其他API错误，可以重试
                output_handler.warning(f"API调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    output_handler.info(f"{wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    last_error = e
            except Exception as e:
                # 未知错误
                output_handler.error(f"未知错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    output_handler.info(f"{wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    last_error = e
        
        # 所有重试都失败了
        if last_error:
            raise last_error
        raise APIError("All retry attempts failed")
    
    def _call_api(self, prompt: str) -> str:
        """调用AI API"""
        if not self.api_key:
            raise APIKeyError("API key is not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
        
        output_handler.info(f"使用模型 {self.config.model} 调用AI API")
        output_handler.debug_print(f"API URL: {self.config.api_url}")
        
        try:
            response = requests.post(
                self.config.api_url,
                headers=headers,
                json=payload,
                timeout=self.config.timeout
            )
            
            output_handler.info(f"API响应状态: {response.status_code}")
            
            # 根据状态码处理不同类型的错误
            if response.status_code == 401:
                error_msg = "API密钥无效或已过期"
                output_handler.error(f"{error_msg}: {response.text}")
                raise APIKeyError(error_msg, status_code=401, response_text=response.text)
            
            elif response.status_code == 429:
                error_msg = "API请求频率超限"
                output_handler.error(f"{error_msg}: {response.text}")
                raise APIRateLimitError(error_msg, status_code=429, response_text=response.text)
            
            elif response.status_code >= 500:
                error_msg = f"API服务器错误 ({response.status_code})"
                output_handler.error(f"{error_msg}: {response.text}")
                raise APIError(error_msg, status_code=response.status_code, response_text=response.text)
            
            elif response.status_code != 200:
                error_msg = f"API请求失败 ({response.status_code})"
                output_handler.error(f"{error_msg}: {response.text}")
                raise APIError(error_msg, status_code=response.status_code, response_text=response.text)
            
            result = response.json()
            output_handler.debug_print(f"API响应: {result}")
            
            content = result["choices"][0]["message"]["content"]
            output_handler.info(f"收到AI API响应")
            
            return content
            
        except requests.exceptions.Timeout as e:
            error_msg = f"API请求超时 ({self.config.timeout}秒)"
            output_handler.error(error_msg)
            raise APITimeoutError(error_msg)
        
        except requests.exceptions.ConnectionError as e:
            error_msg = "无法连接到API服务器，请检查网络连接"
            output_handler.error(f"{error_msg}: {e}")
            raise APIError(error_msg)
        
        except requests.exceptions.RequestException as e:
            error_msg = f"API请求失败: {e}"
            output_handler.error(error_msg)
            raise APIError(error_msg)
        
        except (KeyError, IndexError) as e:
            error_msg = f"解析API响应失败: {e}"
            output_handler.error(error_msg)
            raise APIError(error_msg)
    
    def _parse_response(self, response: str, paper: ArxivPaper) -> PaperSummary:
        """
        解析API响应为结构化数据（使用配置的章节映射）
        
        Args:
            response: AI API返回的文本
            paper: 论文信息
            
        Returns:
            结构化的PaperSummary对象
        """
        summary = PaperSummary(
            arxiv_id=paper.arxiv_id,
            title=paper.title,
            authors=paper.authors,
            author_affiliations=paper.author_affiliations if hasattr(paper, 'author_affiliations') else [],
            published_year=paper.published_date.year,
            venue=paper.venue if hasattr(paper, 'venue') and paper.venue else "arXiv"
        )
        
        # 提取各个章节
        sections = self._extract_sections(response)
        
        # 使用配置的章节映射填充字段
        for section_num, section_content in sections.items():
            if section_num in self.section_mappings:
                mapping = self.section_mappings[section_num]
                field_name = mapping['field_name']
                field_type = mapping['field_type']
                
                # 根据字段类型进行特殊处理
                if field_type == 'list':
                    if field_name == 'figures_tables':
                        setattr(summary, field_name, self._parse_figures_tables(section_content))
                    elif field_name == 'references':
                        setattr(summary, field_name, self._parse_references(section_content))
                else:
                    setattr(summary, field_name, section_content)
        
        # 解析基本信息部分，提取作者单位等
        basic_info = sections.get("1", "")
        affiliations = self._extract_affiliations(basic_info)
        if affiliations:
            summary.author_affiliations = affiliations
        
        doi = self._extract_doi(basic_info)
        if doi:
            summary.doi = doi
        
        return summary
    
    def _extract_sections(self, text: str) -> dict:
        """提取各个章节内容"""
        sections = {}
        
        # 匹配 ## 数字. 标题 格式的章节
        pattern = r'##\s*(\d+)\.\s*([^\n]*)\n(.*?)(?=##\s*\d+\.|$)'
        matches = re.findall(pattern, text, re.DOTALL)
        
        for num, title, content in matches:
            sections[num] = content.strip()
        
        return sections
    
    def _parse_figures_tables(self, text: str) -> list:
        """解析图表信息"""
        figures_tables = []
        
        # 匹配列表项
        pattern = r'[-*]\s*\*\*(Figure|Table|图|表)\s*(\d+)[:\.\s]*\*\*\s*(.*?)(?=\n\s*[-*]|$)'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            ft_type = match[0]
            number = match[1]
            rest = match[2].strip()
            
            # 分离标题和描述
            lines = rest.split('\n', 1)
            title = lines[0].strip()
            # 移除标题中的冒号前缀
            if title.startswith(': '):
                title = title[2:]
            description = lines[1].strip() if len(lines) > 1 else ""
            
            figures_tables.append(FigureTableInfo(
                number=f"{ft_type} {number}",
                title=title,
                description=description
            ))
        
        return figures_tables
    
    def _parse_references(self, text: str) -> list:
        """解析参考文献"""
        references = []
        
        # 匹配编号列表项
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 移除编号
            line = re.sub(r'^\d+[.\)]\s*', '', line)
            
            if len(line) > 10:  # 至少有一定长度
                ref = ReferenceInfo()
                
                # 尝试提取年份
                year_match = re.search(r'\b(19|20)\d{2}\b', line)
                if year_match:
                    ref.year = year_match.group(0)
                
                # 尝试提取标题（通常在引号内）
                title_match = re.search(r'["""]([^"""]+)["""]', line)
                if title_match:
                    ref.title = title_match.group(1)
                
                # 解析作者（直到年份前的部分）
                year_match = re.search(r'\b(19|20)\d{2}\b', line)
                if year_match:
                    authors_part = line[:year_match.start()].strip()
                    # 移除末尾的逗号
                    if authors_part.endswith(','):
                        authors_part = authors_part[:-1].strip()
                    ref.authors = authors_part
                else:
                    # 如果没有年份，尝试使用逗号分割
                    parts = line.split(',', 1)
                    if parts:
                        ref.authors = parts[0].strip()
                
                references.append(ref)
        
        return references[:2]  # 只取前2篇
    
    def _extract_affiliations(self, text: str) -> list:
        """从基本信息中提取作者单位"""
        affiliations = []
        
        # 匹配作者单位行
        patterns = [
            r'[-*]\s*\*\*作者单位\*\*[:\s]*(.+?)(?=\n|$)',
            r'[-*]\s*\*\*Affiliations?\*\*[:\s]*(.+?)(?=\n|$)',
            r'[-*]\s*作者单位[:\s]*(.+?)(?=\n|$)',
            r'[-*]\s*Affiliations?[:\s]*(.+?)(?=\n|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # 分割多个单位
                aff_text = match.group(1).strip()
                # 支持逗号、分号分隔
                for sep in [';', '；', ',', '，']:
                    if sep in aff_text:
                        affiliations = [a.strip() for a in aff_text.split(sep) if a.strip()]
                        break
                else:
                    affiliations = [aff_text]
                break
        
        return affiliations
    
    def _extract_doi(self, text: str) -> Optional[str]:
        """从基本信息中提取DOI"""
        # 匹配DOI行
        patterns = [
            r'[-*]\s*\*\*DOI\*\*[:\s]*(10\.\S+)(?=\n|$)',
            r'[-*]\s*DOI[:\s]*(10\.\S+)(?=\n|$)',
            r'DOI[:\s]*(10\.\S+)(?=\n|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
