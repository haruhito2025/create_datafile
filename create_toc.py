import os
import logging
from pathlib import Path
from typing import Dict, List
import easyocr
from PyPDF2 import PdfReader
import re
from pdf2image import convert_from_path
import tempfile
import numpy as np
from PIL import Image
import cv2

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self, pdf_folder: str = "pdf_folder"):
        self.pdf_folder = Path(pdf_folder)
        # OCRの設定を最適化
        self.reader = easyocr.Reader(
            ['ja', 'en'],
            gpu=False,
            model_storage_directory='./models',
            download_enabled=True,
            recog_network='japanese_g2'
        )
        
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """画像の前処理を行う"""
        # グレースケール変換
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # ノイズ除去
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # コントラスト強調
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # 二値化
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
        
    def postprocess_text(self, text: str) -> str:
        """テキストの後処理を行う"""
        # 一般的なOCRの誤認識パターンを修正
        corrections = {
            '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
            '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
            '．': '.', '，': ',', '：': ':', '；': ';',
            '（': '(', '）': ')', '［': '[', '］': ']',
            '｛': '{', '｝': '}', '＜': '<', '＞': '>',
            '　': ' ', 'ー': '-', '～': '~'
        }
        
        # 文字の置換
        for wrong, correct in corrections.items():
            text = text.replace(wrong, correct)
        
        # 連続する空白を1つに
        text = re.sub(r'\s+', ' ', text)
        
        # 行頭・行末の空白を削除
        text = text.strip()
        
        return text
        
    def process_pdf(self, pdf_path: Path) -> Dict:
        """PDFファイルを処理し、テキストと目次を抽出"""
        try:
            # PDFの読み込み
            pdf = PdfReader(str(pdf_path))
            total_pages = len(pdf.pages)
            
            # 結果を格納する辞書
            result = {
                "filename": pdf_path.name,
                "total_pages": total_pages,
                "text_by_page": {},
                "toc": []
            }
            
            # PDFを画像に変換（DPIを上げて精度を向上）
            images = convert_from_path(
                str(pdf_path),
                dpi=300,
                grayscale=False
            )
            
            # 各ページの処理
            for page_num in range(total_pages):
                logger.info(f"ページ {page_num + 1}/{total_pages} を処理中...")
                
                # OCR処理
                image = images[page_num]
                # PILイメージをnumpy配列に変換
                image_np = np.array(image)
                
                # 画像の前処理
                processed_image = self.preprocess_image(image_np)
                
                # OCR実行（詳細な設定を追加）
                text = self.reader.readtext(
                    processed_image,
                    detail=1,
                    paragraph=True,
                    contrast_ths=0.1,
                    adjust_contrast=0.5,
                    text_threshold=0.7,
                    link_threshold=0.4,
                    low_text=0.4,
                    canvas_size=1280,
                    mag_ratio=1.5
                )
                
                # テキストの抽出と後処理
                page_text = " ".join([self.postprocess_text(t[1]) for t in text])
                
                # テキスト抽出も試みる
                try:
                    pdf_text = pdf.pages[page_num].extract_text()
                    if pdf_text and len(pdf_text) > len(page_text):
                        page_text = pdf_text
                except:
                    pass
                
                result["text_by_page"][page_num + 1] = page_text
                
                # 目次候補の抽出（見出しらしき行を探す）
                lines = page_text.split("\n")
                for line in lines:
                    if self._is_heading(line):
                        result["toc"].append({
                            "page": page_num + 1,
                            "text": line.strip()
                        })
            
            return result
            
        except Exception as e:
            logger.error(f"PDF処理エラー: {str(e)}")
            raise
    
    def _is_heading(self, text: str) -> bool:
        """テキストが見出しかどうかを判定"""
        # 見出しの特徴を判定する条件
        conditions = [
            len(text) < 100,  # 短いテキスト
            bool(re.match(r'^[0-9\.]+', text)),  # 数字で始まる
            bool(re.match(r'^[第章節]', text)),  # 章、節などで始まる
            text.isupper(),  # すべて大文字
        ]
        return any(conditions)
    
    def save_result(self, result: Dict, output_dir: str = "output"):
        """処理結果をファイルに保存"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # テキストファイルとして保存
        text_file = output_path / f"{result['filename']}_text.txt"
        with open(text_file, "w", encoding="utf-8") as f:
            # 目次を書き出し
            f.write("=== 目次 ===\n")
            for item in result["toc"]:
                f.write(f"ページ {item['page']}: {item['text']}\n")
            
            f.write("\n=== 本文 ===\n")
            for page_num, text in result["text_by_page"].items():
                f.write(f"\n--- ページ {page_num} ---\n")
                f.write(text)
                f.write("\n")
        
        logger.info(f"結果を保存しました: {text_file}")
        return text_file

def main():
    # PDFフォルダの確認
    pdf_folder = Path("pdf_folder")
    if not pdf_folder.exists():
        logger.error("pdf_folderが見つかりません")
        return
    
    # 出力フォルダの作成
    output_folder = Path("output")
    output_folder.mkdir(exist_ok=True)
    
    # PDFファイルの処理
    processor = PDFProcessor()
    
    for pdf_file in pdf_folder.glob("*.pdf"):
        try:
            logger.info(f"処理開始: {pdf_file.name}")
            result = processor.process_pdf(pdf_file)
            output_file = processor.save_result(result)
            logger.info(f"処理完了: {output_file}")
        except Exception as e:
            logger.error(f"エラー: {pdf_file.name} - {str(e)}")

if __name__ == "__main__":
    main() 