import os
from typing import Optional

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

from utils import get_logger, get_output_handler

logger = get_logger()
output_handler = get_output_handler(logger)


class PDFExtractor:
    """PDF文本提取器"""
    
    def __init__(self, preferred_method: str = "pdfplumber"):
        """
        初始化提取器
        
        Args:
            preferred_method: 首选提取方法 (pdfplumber, pypdf2)
        """
        self.preferred_method = preferred_method
        
        if preferred_method == "pdfplumber" and not PDFPLUMBER_AVAILABLE:
            output_handler.warning("pdfplumber不可用，回退到PyPDF2")
            self.preferred_method = "pypdf2" if PYPDF2_AVAILABLE else None
        
        if preferred_method == "pypdf2" and not PYPDF2_AVAILABLE:
            output_handler.warning("PyPDF2不可用，回退到pdfplumber")
            self.preferred_method = "pdfplumber" if PDFPLUMBER_AVAILABLE else None
    
    def extract_text(self, pdf_path: str, max_pages: Optional[int] = None) -> str:
        """
        从PDF提取文本
        
        Args:
            pdf_path: PDF文件路径
            max_pages: 最大提取页数（None表示全部）
            
        Returns:
            提取的文本
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if self.preferred_method == "pdfplumber":
            return self._extract_with_pdfplumber(pdf_path, max_pages)
        elif self.preferred_method == "pypdf2":
            return self._extract_with_pypdf2(pdf_path, max_pages)
        else:
            raise RuntimeError("No PDF extraction library available")
    
    def _extract_with_pdfplumber(self, pdf_path: str, 
                                  max_pages: Optional[int] = None) -> str:
        """使用pdfplumber提取文本"""
        text_parts = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                pages_to_extract = min(max_pages or total_pages, total_pages)
                
                output_handler.debug_print(f"使用pdfplumber从 {pages_to_extract} 页提取文本")
                
                for i, page in enumerate(pdf.pages[:pages_to_extract]):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
        
        except Exception as e:
            output_handler.error(f"使用pdfplumber提取文本时出错: {e}")
            raise
        
        return "\n\n".join(text_parts)
    
    def _extract_with_pypdf2(self, pdf_path: str, 
                              max_pages: Optional[int] = None) -> str:
        """使用PyPDF2提取文本"""
        text_parts = []
        
        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                total_pages = len(reader.pages)
                pages_to_extract = min(max_pages or total_pages, total_pages)
                
                output_handler.debug_print(f"使用PyPDF2从 {pages_to_extract} 页提取文本")
                
                for i in range(pages_to_extract):
                    page = reader.pages[i]
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
        
        except Exception as e:
            output_handler.error(f"使用PyPDF2提取文本时出错: {e}")
            raise
        
        return "\n\n".join(text_parts)
    
    def extract_abstract_section(self, text: str) -> str:
        """
        尝试提取摘要部分
        
        Args:
            text: 全文文本
            
        Returns:
            摘要文本
        """
        # 常见摘要标记
        abstract_markers = [
            "Abstract",
            "ABSTRACT",
            "摘要",
        ]
        
        lines = text.split("\n")
        abstract_start = -1
        abstract_end = -1
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            for marker in abstract_markers:
                if stripped.startswith(marker):
                    abstract_start = i
                    break
            if abstract_start >= 0:
                break
        
        if abstract_start < 0:
            return ""
        
        # 寻找摘要结束（通常是空行或下一个章节）
        for i in range(abstract_start + 1, min(abstract_start + 50, len(lines))):
            line = lines[i].strip()
            # 检查是否是章节标题
            if line and (line.isupper() or line.endswith(":") or 
                         line in ["1 Introduction", "1. Introduction", "I. Introduction"]):
                abstract_end = i
                break
            # 连续空行也可能表示结束
            if i > abstract_start + 1 and not lines[i-1].strip() and not line:
                abstract_end = i - 1
                break
        
        if abstract_end < 0:
            abstract_end = min(abstract_start + 30, len(lines))
        
        abstract_lines = lines[abstract_start:abstract_end]
        return "\n".join(abstract_lines).strip()
    
    def extract_introduction(self, text: str, max_length: int = 5000) -> str:
        """
        提取引言部分
        
        Args:
            text: 全文文本
            max_length: 最大长度
            
        Returns:
            引言文本
        """
        intro_markers = [
            "1 Introduction",
            "1. Introduction", 
            "I. Introduction",
            "INTRODUCTION",
        ]
        
        lines = text.split("\n")
        intro_start = -1
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            for marker in intro_markers:
                if marker in stripped:
                    intro_start = i
                    break
            if intro_start >= 0:
                break
        
        if intro_start < 0:
            return ""
        
        # 收集引言内容直到下一个章节
        intro_lines = []
        for i in range(intro_start, len(lines)):
            line = lines[i]
            # 检测下一个章节
            if i > intro_start and line.strip():
                # 检查是否是新的章节标题
                if (line.strip().startswith("2 ") or 
                    line.strip().startswith("2.") or
                    line.strip().startswith("II.") or
                    line.strip() in ["Related Work", "Method", "Methods", "Experiments"]):
                    break
            
            intro_lines.append(line)
            
            if len("\n".join(intro_lines)) > max_length:
                break
        
        return "\n".join(intro_lines).strip()
