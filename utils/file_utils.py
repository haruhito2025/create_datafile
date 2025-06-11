import os
from pathlib import Path
import shutil
from typing import Dict, Any
import PyPDF2
import logging
import time
from PyPDF2 import PdfReader

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ファイルハンドラの設定
file_handler = logging.FileHandler('app.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)

# フォーマッタの設定
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# ハンドラの追加
logger.addHandler(file_handler)

class FileManager:
    def __init__(self, data_dir: str = "data"):
        """
        ファイル管理クラスの初期化
        
        Args:
            data_dir (str): データ保存ディレクトリ
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir = self.data_dir / "uploads"
        self.processed_dir = self.data_dir / "processed"
        
        # ディレクトリの作成
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    def save_uploaded_file(self, file_content: bytes, filename: str) -> Path:
        """
        アップロードされたファイルを保存
        
        Args:
            file_content (bytes): ファイルの内容
            filename (str): ファイル名
            
        Returns:
            Path: 保存されたファイルのパス
        """
        try:
            # ファイル名から拡張子を取得
            ext = Path(filename).suffix
            
            # 一意のファイル名を生成
            timestamp = int(time.time())
            new_filename = f"{timestamp}_{filename}"
            
            # ファイルを保存
            file_path = self.upload_dir / new_filename
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            logger.info(f"File saved: {str(file_path)}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise
    
    def move_to_processed(self, file_path: Path) -> Path:
        """
        ファイルを処理済みディレクトリに移動
        
        Args:
            file_path (Path): 移動するファイルのパス
            
        Returns:
            Path: 移動後のファイルパス
        """
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # 処理済みディレクトリに移動
            new_path = self.processed_dir / file_path.name
            file_path.rename(new_path)
            
            logger.info(f"File moved to processed: {str(new_path)}")
            return new_path
            
        except Exception as e:
            logger.error(f"Error moving file: {str(e)}")
            raise
    
    def get_file_list(self) -> list[Dict[str, Any]]:
        """
        保存されているファイルのリストを取得
        
        Returns:
            list[Dict[str, Any]]: ファイル情報のリスト
        """
        try:
            files = []
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False

def validate_pdf_file(file_path: Path) -> Dict[str, Any]:
    """
    PDFファイルを検証
    
    Args:
        file_path (Path): 検証するPDFファイルのパス
        
    Returns:
        Dict[str, Any]: 検証結果
    """
    try:
        # ファイルの存在確認
        if not file_path.exists():
            return {
                "valid": False,
                "error": "File not found"
            }
        
        # ファイルサイズの確認（50MB以下）
        if file_path.stat().st_size > 50 * 1024 * 1024:
            return {
                "valid": False,
                "error": "File size exceeds 50MB limit"
            }
        
        # PDFの読み込みと検証
        with open(file_path, "rb") as f:
            pdf = PdfReader(f)
            
            # ページ数の確認（300ページ以下）
            if len(pdf.pages) > 300:
                return {
                    "valid": False,
                    "error": "PDF exceeds 300 pages limit"
                }
            
            # 各ページの検証
            for i, page in enumerate(pdf.pages):
                try:
                    # テキスト抽出のテスト
                    page.extract_text()
                except Exception as e:
                    return {
                        "valid": False,
                        "error": f"Error on page {i+1}: {str(e)}"
                    }
        
        return {
            "valid": True,
            "pages": len(pdf.pages),
            "size": file_path.stat().st_size
        }
        
    except Exception as e:
        logger.error(f"Error validating PDF: {str(e)}")
        return {
            "valid": False,
            "error": str(e)
        } 