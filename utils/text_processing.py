import re
import logging
from typing import Dict, Any, List, Tuple
import unicodedata
import sys

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def clean_ocr_text(text: str) -> str:
    """
    OCRで抽出したテキストをクリーニング
    
    Args:
        text (str): クリーニングするテキスト
        
    Returns:
        str: クリーニングされたテキスト
    """
    try:
        # 不要な空白の削除
        text = re.sub(r'\s+', ' ', text)
        
        # 特殊文字の置換
        text = text.replace('|', 'I')  # 縦線をIに置換
        text = text.replace('l', 'I')  # 小文字のlを大文字のIに置換
        
        # 全角文字の正規化
        text = unicodedata.normalize('NFKC', text)
        
        # 行頭の不要な文字を削除
        text = re.sub(r'^[^a-zA-Z0-9]+', '', text)
        
        # 行末の不要な文字を削除
        text = re.sub(r'[^a-zA-Z0-9]+$', '', text)
        
        return text.strip()
        
    except Exception as e:
        logger.error(f"Error cleaning OCR text: {str(e)}")
        return text

def format_text_for_display(text: str, max_length: int = 100) -> str:
    """
    テキストを表示用にフォーマット
    
    Args:
        text (str): フォーマットするテキスト
        max_length (int): 1行の最大文字数
        
    Returns:
        str: フォーマットされたテキスト
    """
    try:
        # テキストをクリーニング
        text = clean_ocr_text(text)
        
        # 長い行を分割
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= max_length:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\n'.join(lines)
        
    except Exception as e:
        logger.error(f"Error formatting text: {str(e)}")
        return text

def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """
    テキストからキーワードを抽出
    
    Args:
        text (str): キーワードを抽出するテキスト
        min_length (int): キーワードの最小長
        
    Returns:
        List[str]: 抽出されたキーワードのリスト
    """
    try:
        # テキストをクリーニング
        text = clean_ocr_text(text)
        
        # 単語に分割
        words = text.split()
        
        # キーワードの抽出
        keywords = []
        for word in words:
            # 最小長を満たす単語のみを抽出
            if len(word) >= min_length:
                # 特殊文字を除去
                word = re.sub(r'[^a-zA-Z0-9]', '', word)
                if word:
                    keywords.append(word.lower())
        
        return list(set(keywords))  # 重複を除去
        
    except Exception as e:
        logger.error(f"Error extracting keywords: {str(e)}")
        return []

def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    2つのテキスト間の類似度を計算
    
    Args:
        text1 (str): 比較するテキスト1
        text2 (str): 比較するテキスト2
        
    Returns:
        float: 類似度（0.0から1.0の間）
    """
    try:
        # テキストをクリーニング
        text1 = clean_ocr_text(text1)
        text2 = clean_ocr_text(text2)
        
        # 単語に分割
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        # 共通の単語数を計算
        common_words = words1.intersection(words2)
        
        # 類似度を計算
        if not words1 or not words2:
            return 0.0
        
        similarity = len(common_words) / max(len(words1), len(words2))
        return similarity
        
    except Exception as e:
        logger.error(f"Error calculating text similarity: {str(e)}")
        return 0.0 