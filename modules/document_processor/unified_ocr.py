import easyocr
from paddleocr import PaddleOCR
from typing import Dict, Any
import logging
from pathlib import Path
import sys
import fitz  # PyMuPDF
import numpy as np
from PIL import Image
import io

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

class OCRFactory:
    @staticmethod
    def get_available_engines():
        return ['easyocr', 'paddle', 'multi']
    
    @staticmethod
    def create_engine(engine_name: str):
        if engine_name == 'easyocr':
            return EasyOCREngine()
        elif engine_name == 'paddle':
            return PaddleOCREngine()
        elif engine_name == 'multi':
            return MultiOCREngine()
        else:
            raise ValueError(f"Unknown OCR engine: {engine_name}")

class BaseOCREngine:
    def extract_text_from_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        raise NotImplementedError
    
    def pdf_to_images(self, pdf_path: Path) -> list:
        """PDFを画像に変換"""
        try:
            doc = fitz.open(pdf_path)
            images = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # 高解像度で画像に変換
                mat = fitz.Matrix(2.0, 2.0)  # 2倍スケール
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                images.append((page_num + 1, np.array(img)))
            
            doc.close()
            return images
        except Exception as e:
            logger.error(f"PDF to image conversion error: {str(e)}")
            raise

class EasyOCREngine(BaseOCREngine):
    def __init__(self):
        logger.info("EasyOCRエンジンを初期化中...")
        self.reader = easyocr.Reader(['ja', 'en'])
        logger.info("EasyOCRエンジンの初期化が完了しました")
    
    def process_document(self, pdf_path: Path) -> Dict[str, Any]:
        """
        ドキュメントを処理するための統一されたインターフェース。
        内部でextract_text_from_pdfを呼び出します。
        """
        return self.extract_text_from_pdf(pdf_path)

    def extract_text_from_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        try:
            logger.info(f"EasyOCRでPDF処理開始: {pdf_path}")
            images = self.pdf_to_images(pdf_path)
            all_text = []
            text_by_page = {}
            
            total_pages = len(images)
            logger.info(f"EasyOCR - 総ページ数: {total_pages}")
            
            for i, (page_num, image) in enumerate(images):
                logger.info(f"EasyOCR - ページ {page_num}/{total_pages} を処理中... ({((i+1)/total_pages)*100:.1f}%)")
                results = self.reader.readtext(image)
                page_text = []
                
                for (bbox, text, confidence) in results:
                    if confidence > 0.5:  # 信頼度フィルター
                        page_text.append(text)
                
                page_text_str = '\n'.join(page_text)
                text_by_page[page_num] = page_text_str
                all_text.append(page_text_str)
                logger.info(f"EasyOCR - ページ {page_num} 完了 (文字数: {len(page_text_str)})")
            
            final_text = '\n\n'.join(all_text)
            logger.info(f"EasyOCR - 全処理完了 (総文字数: {len(final_text)})")
            
            return {
                "success": True,
                "text": final_text,
                "text_by_page": text_by_page,
                "total_chars": len(final_text),
                "pages_processed": len(images)
            }
        except Exception as e:
            logger.error(f"EasyOCR error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "text_by_page": {},
                "total_chars": 0
            }

class PaddleOCREngine(BaseOCREngine):
    def __init__(self):
        logger.info("PaddleOCRエンジンを初期化中...")
        self.ocr = PaddleOCR(use_angle_cls=True, lang='japan')
        logger.info("PaddleOCRエンジンの初期化が完了しました")
    
    def process_document(self, pdf_path: Path) -> Dict[str, Any]:
        """
        ドキュメントを処理するための統一されたインターフェース。
        内部でextract_text_from_pdfを呼び出します。
        """
        return self.extract_text_from_pdf(pdf_path)

    def extract_text_from_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        try:
            logger.info(f"PaddleOCRでPDF処理開始: {pdf_path}")
            images = self.pdf_to_images(pdf_path)
            all_text = []
            text_by_page = {}
            
            total_pages = len(images)
            logger.info(f"PaddleOCR - 総ページ数: {total_pages}")
            
            for i, (page_num, image) in enumerate(images):
                logger.info(f"PaddleOCR - ページ {page_num}/{total_pages} を処理中... ({((i+1)/total_pages)*100:.1f}%)")
                results = self.ocr.ocr(image, cls=True)
                page_text = []
                
                if results[0]:  # 結果が存在する場合
                    for line in results[0]:
                        if len(line) >= 2 and line[1][1] > 0.5:  # 信頼度フィルター
                            page_text.append(line[1][0])
                
                page_text_str = '\n'.join(page_text)
                text_by_page[page_num] = page_text_str
                all_text.append(page_text_str)
                logger.info(f"PaddleOCR - ページ {page_num} 完了 (文字数: {len(page_text_str)})")
            
            final_text = '\n\n'.join(all_text)
            logger.info(f"PaddleOCR - 全処理完了 (総文字数: {len(final_text)})")
            
            return {
                "success": True,
                "text": final_text,
                "text_by_page": text_by_page,
                "total_chars": len(final_text),
                "pages_processed": len(images)
            }
        except Exception as e:
            logger.error(f"PaddleOCR error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "text_by_page": {},
                "total_chars": 0
            }

class MultiOCREngine(BaseOCREngine):
    def __init__(self):
        self.easyocr = EasyOCREngine()
        self.paddleocr = PaddleOCREngine()
    
    def extract_text_from_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        try:
            # 両方のエンジンで処理
            easy_result = self.easyocr.extract_text_from_pdf(pdf_path)
            paddle_result = self.paddleocr.extract_text_from_pdf(pdf_path)
            
            # 結果の統合
            combined_text_by_page = {}
            for page_num in easy_result.get('text_by_page', {}):
                easy_text = easy_result['text_by_page'].get(page_num, '')
                paddle_text = paddle_result['text_by_page'].get(page_num, '')
                combined_text_by_page[page_num] = f"EasyOCR:\n{easy_text}\n\nPaddleOCR:\n{paddle_text}"
            
            return {
                "success": True,
                "text": f"EasyOCR結果:\n{easy_result['text']}\n\nPaddleOCR結果:\n{paddle_result['text']}",
                "text_by_page": combined_text_by_page,
                "total_chars": easy_result['total_chars'] + paddle_result['total_chars'],
                "easy_result": easy_result,
                "paddle_result": paddle_result
            }
        except Exception as e:
            logger.error(f"MultiOCR error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            } 