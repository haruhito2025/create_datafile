from typing import Dict, Any, List
import logging
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from .unified_ocr import OCRFactory

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        ドキュメント処理クラスの初期化
        """
        self.ocr_factory = OCRFactory()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    
    def process_text(self, text: str, document_name: str) -> List[Document]:
        """
        OCR済みのテキストを受け取り、チャンクに分割します。

        Args:
            text (str): OCRで抽出された全文。
            document_name (str): 元のドキュメント名。

        Returns:
            List[Document]: LangChainのDocumentオブジェクトのリスト。
        """
        if not text:
            return []
        
        # テキストをチャンクに分割
        chunks = self.text_splitter.split_text(text)
        
        # 各チャンクをDocumentオブジェクトに変換
        documents = []
        for i, chunk_text in enumerate(chunks):
            metadata = {
                "source": document_name,
                "chunk_number": i
            }
            doc = Document(page_content=chunk_text, metadata=metadata)
            documents.append(doc)
            
        logger.info(f"'{document_name}' から {len(documents)}個のチャンクを作成しました。")
        return documents

    def process_document(self, file_path: str, ocr_engine: str = 'multi') -> Dict[str, Any]:
        """
        ドキュメントを処理し、テキストを抽出
        
        Args:
            file_path (str): 処理するファイルのパス
            ocr_engine (str): 使用するOCRエンジン（'easyocr', 'paddle', 'multi'）
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        try:
            # OCRエンジンの取得
            ocr_engine = self.ocr_factory.create_engine(ocr_engine)
            
            # ファイルパスの検証
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # OCR処理の実行
            result = ocr_engine.extract_text_from_pdf(file_path)
            
            if not result["success"]:
                raise Exception(f"OCR processing failed: {result.get('error', 'Unknown error')}")
            
            return {
                "success": True,
                "text": result["text_by_page"],
                "total_chars": result["total_chars"],
                "metadata": {
                    "file_name": file_path.name,
                    "file_size": file_path.stat().st_size,
                    "ocr_engine": ocr_engine.__class__.__name__
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def batch_process_documents(self, file_paths: List[str], ocr_engine: str = 'multi') -> List[Dict[str, Any]]:
        """
        複数のドキュメントを一括処理
        
        Args:
            file_paths (List[str]): 処理するファイルのパスのリスト
            ocr_engine (str): 使用するOCRエンジン
            
        Returns:
            List[Dict[str, Any]]: 各ドキュメントの処理結果のリスト
        """
        results = []
        for file_path in file_paths:
            result = self.process_document(file_path, ocr_engine)
            results.append(result)
        return results 