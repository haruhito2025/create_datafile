import json
from typing import Dict, List, Tuple, Set
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import difflib
from collections import Counter
import re

logger = logging.getLogger(__name__)

class OCRComparisonManager:
    def __init__(self):
        self.comparison_history = []
        
    def compare_ocr_results(self, 
                          easyocr_text: str, 
                          paddleocr_text: str) -> Dict:
        """OCR結果を比較し、差分を分析"""
        
        # テキストを単語に分割（改良版）
        easyocr_words = self._tokenize_text(easyocr_text)
        paddleocr_words = self._tokenize_text(paddleocr_text)
        
        # 差分の検出
        differences = self._find_differences(easyocr_words, paddleocr_words)
        
        # 一致率の計算
        matching_rate = self._calculate_matching_rate(easyocr_words, paddleocr_words)
        
        # 類似度スコアの計算
        similarity_score = self._calculate_similarity_score(easyocr_text, paddleocr_text)
        
        # 共通単語と固有単語の検出
        word_analysis = self._analyze_words(easyocr_words, paddleocr_words)
        
        # 差分HTMLの生成
        diff_html = self._generate_diff_html(easyocr_text, paddleocr_text)
        
        # 結果の保存
        comparison_result = {
            "document_info": {
                "timestamp": datetime.now().isoformat()
            },
            "ocr_results": {
                "easyocr": {
                    "text": easyocr_text,
                    "word_count": len(easyocr_words),
                    "char_count": len(easyocr_text)
                },
                "paddleocr": {
                    "text": paddleocr_text,
                    "word_count": len(paddleocr_words),
                    "char_count": len(paddleocr_text)
                }
            },
            "comparison": {
                "matching_rate": matching_rate,
                "similarity_score": similarity_score,
                "differences": differences,
                "common_words": word_analysis["common_words"],
                "unique_easy": word_analysis["unique_easy"],
                "unique_paddle": word_analysis["unique_paddle"],
                "diff_html": diff_html
            }
        }
        
        self.comparison_history.append(comparison_result)
        return comparison_result["comparison"]
    
    def _tokenize_text(self, text: str) -> List[str]:
        """テキストを適切にトークン化"""
        # 日本語と英語を考慮した単語分割
        words = re.findall(r'[\w]+', text)
        return [word for word in words if word.strip()]
    
    def _calculate_similarity_score(self, text1: str, text2: str) -> float:
        """テキスト間の類似度スコアを計算（0-1の範囲）"""
        if not text1 or not text2:
            return 0.0
        
        # difflib.SequenceMatcherを使用
        matcher = difflib.SequenceMatcher(None, text1, text2)
        return matcher.ratio()
    
    def _analyze_words(self, words1: List[str], words2: List[str]) -> Dict:
        """単語レベルの分析を実行"""
        set1 = set(words1)
        set2 = set(words2)
        
        common_words = list(set1 & set2)
        unique_easy = list(set1 - set2)
        unique_paddle = list(set2 - set1)
        
        return {
            "common_words": common_words,
            "unique_easy": unique_easy,
            "unique_paddle": unique_paddle
        }
    
    def _generate_diff_html(self, text1: str, text2: str) -> str:
        """HTML形式の差分表示を生成"""
        try:
            # 行ごとに分割して比較
            lines1 = text1.split('\n')
            lines2 = text2.split('\n')
            
            differ = difflib.HtmlDiff()
            html_diff = differ.make_table(
                lines1, lines2,
                fromdesc='EasyOCR',
                todesc='PaddleOCR',
                context=True,
                numlines=3
            )
            
            return html_diff
        except Exception as e:
            logger.error(f"HTML差分生成エラー: {e}")
            return ""
    
    def _find_differences(self, 
                         easyocr_words: List[str], 
                         paddleocr_words: List[str]) -> List[Dict]:
        """単語単位での差分を検出（改良版）"""
        differences = []
        
        # より詳細な差分検出のためのアルゴリズム
        matcher = difflib.SequenceMatcher(None, easyocr_words, paddleocr_words)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != 'equal':
                differences.append({
                    "type": tag,  # 'replace', 'delete', 'insert'
                    "easyocr_range": (i1, i2),
                    "paddleocr_range": (j1, j2),
                    "easyocr_words": easyocr_words[i1:i2],
                    "paddleocr_words": paddleocr_words[j1:j2]
                })
        
        return differences
    
    def _calculate_matching_rate(self, 
                               easyocr_words: List[str], 
                               paddleocr_words: List[str]) -> float:
        """一致率を計算（改良版）"""
        if not easyocr_words and not paddleocr_words:
            return 1.0
        elif not easyocr_words or not paddleocr_words:
            return 0.0
        
        # 順序を考慮した一致率計算
        matcher = difflib.SequenceMatcher(None, easyocr_words, paddleocr_words)
        return matcher.ratio()
    
    def export_comparison_results(self, output_path: str):
        """比較結果をJSONファイルとしてエクスポート"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.comparison_history, f, ensure_ascii=False, indent=2)
    
    def generate_statistics(self) -> Dict:
        """統計情報を生成"""
        if not self.comparison_history:
            return {}
            
        stats = {
            "total_pages": len(self.comparison_history),
            "average_matching_rate": np.mean([c["comparison"]["matching_rate"] 
                                            for c in self.comparison_history]),
            "total_differences": sum(len(c["comparison"]["differences"]) 
                                   for c in self.comparison_history),
            "word_counts": {
                "easyocr": [c["ocr_results"]["easyocr"]["word_count"] 
                           for c in self.comparison_history],
                "paddleocr": [c["ocr_results"]["paddleocr"]["word_count"] 
                             for c in self.comparison_history]
            }
        }
        return stats
    
    def create_comparison_visualization(self) -> Tuple[go.Figure, go.Figure]:
        """比較結果の可視化を作成"""
        if not self.comparison_history:
            return None, None
            
        # 一致率の推移グラフ
        matching_rates = [c["comparison"]["matching_rate"] 
                         for c in self.comparison_history]
        pages = list(range(1, len(matching_rates) + 1))
        
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=pages,
            y=matching_rates,
            mode='lines+markers',
            name='一致率'
        ))
        fig1.update_layout(
            title='ページごとのOCR一致率',
            xaxis_title='ページ番号',
            yaxis_title='一致率',
            yaxis_range=[0, 1]
        )
        
        # 単語数の比較グラフ
        word_counts = {
            'EasyOCR': [c["ocr_results"]["easyocr"]["word_count"] 
                        for c in self.comparison_history],
            'PaddleOCR': [c["ocr_results"]["paddleocr"]["word_count"] 
                         for c in self.comparison_history]
        }
        
        fig2 = go.Figure()
        for engine, counts in word_counts.items():
            fig2.add_trace(go.Bar(
                name=engine,
                x=pages,
                y=counts
            ))
        fig2.update_layout(
            title='エンジン別単語数比較',
            xaxis_title='ページ番号',
            yaxis_title='単語数',
            barmode='group'
        )
        
        return fig1, fig2
    
    def get_detailed_statistics(self) -> Dict:
        """詳細な統計情報を生成"""
        if not self.comparison_history:
            return {}
        
        comparisons = [c["comparison"] for c in self.comparison_history]
        
        stats = {
            "total_comparisons": len(self.comparison_history),
            "average_matching_rate": np.mean([c["matching_rate"] for c in comparisons]),
            "average_similarity_score": np.mean([c["similarity_score"] for c in comparisons]),
            "total_differences": sum(len(c["differences"]) for c in comparisons),
            "common_words_stats": {
                "average_count": np.mean([len(c["common_words"]) for c in comparisons]),
                "total_unique": len(set().union(*[c["common_words"] for c in comparisons]))
            },
            "unique_words_stats": {
                "easyocr_average": np.mean([len(c["unique_easy"]) for c in comparisons]),
                "paddleocr_average": np.mean([len(c["unique_paddle"]) for c in comparisons])
            }
        }
        
        return stats 