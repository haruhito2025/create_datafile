import logging
from typing import Dict, Any, List, Optional
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
import chromadb
from chromadb.config import Settings
import os
from pathlib import Path
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

class ChromaVectorStore:
    def __init__(self, persist_directory: str = "data/chroma"):
        """
        ChromaDBベクトルストアの初期化
        
        Args:
            persist_directory (str): データベースの保存ディレクトリ
        """
        try:
            self.persist_directory = Path(persist_directory)
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            
            # 埋め込みモデルの初期化
            self.embeddings = OpenAIEmbeddings()
            
            # ChromaDBの設定
            self.client = chromadb.Client(Settings(
                persist_directory=str(self.persist_directory),
                anonymized_telemetry=False
            ))
            
            # コレクションの作成または取得
            self.collection = self.client.get_or_create_collection(
                name="documents",
                metadata={"hnsw:space": "cosine"}
            )
            
            # LangChainのChromaインスタンスの作成
            self.vector_store = Chroma(
                client=self.client,
                collection_name="documents",
                embedding_function=self.embeddings
            )
            
            logger.info("ChromaVectorStore initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing ChromaVectorStore: {str(e)}")
            raise
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """
        ドキュメントをベクトルストアに追加
        
        Args:
            documents (List[Dict[str, Any]]): 追加するドキュメントのリスト
            
        Returns:
            bool: 追加が成功したかどうか
        """
        try:
            # ドキュメントの追加
            self.vector_store.add_documents(documents)
            
            # 変更を永続化
            self.client.persist()
            
            logger.info(f"Added {len(documents)} documents to vector store")
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            return False
    
    def search(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        類似ドキュメントの検索
        
        Args:
            query (str): 検索クエリ
            n_results (int): 取得する結果の数
            
        Returns:
            List[Dict[str, Any]]: 検索結果のリスト
        """
        try:
            # 類似ドキュメントの検索
            results = self.vector_store.similarity_search(
                query,
                k=n_results
            )
            
            # 結果の整形
            formatted_results = []
            for doc in results:
                formatted_results.append({
                    "text": doc.page_content,
                    "metadata": doc.metadata
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return []
    
    def delete_documents(self, document_ids: List[str]) -> bool:
        """
        ドキュメントの削除
        
        Args:
            document_ids (List[str]): 削除するドキュメントのIDリスト
            
        Returns:
            bool: 削除が成功したかどうか
        """
        try:
            # ドキュメントの削除
            self.collection.delete(ids=document_ids)
            
            # 変更を永続化
            self.client.persist()
            
            logger.info(f"Deleted {len(document_ids)} documents")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting documents: {str(e)}")
            return False
    
    def get_document_count(self) -> int:
        """
        保存されているドキュメントの数を取得
        
        Returns:
            int: ドキュメントの数
        """
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Error getting document count: {str(e)}")
            return 0
    
    def as_retriever(self, **kwargs):
        """
        LangChainのRetrieverインターフェースを提供
        
        Returns:
            Retriever: LangChainのRetrieverオブジェクト
        """
        try:
            return self.vector_store.as_retriever(**kwargs)
        except Exception as e:
            logger.error(f"Error creating retriever: {str(e)}")
            raise 