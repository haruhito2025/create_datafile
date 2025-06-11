from typing import Dict, Any, List, Optional
import logging
from pathlib import Path
from modules.vector_store.chroma_store import ChromaVectorStore
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.llms import OpenAI
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
import json
import os
from datetime import datetime
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

class RetrievalQAInterface:
    def __init__(self, vector_store: Chroma):
        """
        初期化
        
        Args:
            vector_store (Chroma): ベクトルストア
        """
        self.vector_store = vector_store
        self.qa_chain = None
        self._initialize_qa_chain()
    
    def _initialize_qa_chain(self):
        """QAチェーンの初期化"""
        try:
            # プロンプトテンプレートの設定
            template = """
            以下の文脈を使用して、質問に答えてください。
            文脈から答えられない場合は、正直に「わかりません」と答えてください。
            
            文脈:
            {context}
            
            質問: {question}
            
            回答:
            """
            
            prompt = PromptTemplate(
                template=template,
                input_variables=["context", "question"]
            )
            
            # LLMの初期化
            llm = OpenAI(
                temperature=0,
                model_name="gpt-3.5-turbo"
            )
            
            # QAチェーンの作成
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=self.vector_store.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": 3}
                ),
                chain_type_kwargs={"prompt": prompt}
            )
            
            logger.info("QA chain initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing QA chain: {str(e)}")
            raise
    
    def get_answer(self, question: str) -> Dict[str, Any]:
        """
        質問に対する回答を取得
        
        Args:
            question (str): 質問文
            
        Returns:
            Dict[str, Any]: 回答と関連情報
        """
        try:
            if not self.qa_chain:
                raise ValueError("QA chain not initialized")
            
            # 回答の取得
            result = self.qa_chain({"query": question})
            
            # 関連ドキュメントの取得
            docs = self.vector_store.similarity_search(question, k=3)
            sources = [doc.metadata for doc in docs]
            
            return {
                "answer": result["result"],
                "sources": sources,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting answer: {str(e)}")
            return {
                "answer": "申し訳ありません。エラーが発生しました。",
                "sources": [],
                "timestamp": datetime.now().isoformat()
            }

class EnhancedQAInterface:
    def __init__(self, vector_store: Chroma):
        """
        初期化
        
        Args:
            vector_store (Chroma): ベクトルストア
        """
        self.vector_store = vector_store
        self.qa_chain = None
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        self._initialize_qa_chain()
    
    def _initialize_qa_chain(self):
        """QAチェーンの初期化"""
        try:
            # プロンプトテンプレートの設定
            template = """
            以下の会話履歴と文脈を使用して、質問に答えてください。
            文脈から答えられない場合は、正直に「わかりません」と答えてください。
            
            会話履歴:
            {chat_history}
            
            文脈:
            {context}
            
            質問: {question}
            
            回答:
            """
            
            prompt = PromptTemplate(
                template=template,
                input_variables=["chat_history", "context", "question"]
            )
            
            # LLMの初期化
            llm = OpenAI(
                temperature=0,
                model_name="gpt-3.5-turbo"
            )
            
            # QAチェーンの作成
            self.qa_chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=self.vector_store.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": 3}
                ),
                memory=self.memory,
                combine_docs_chain_kwargs={"prompt": prompt}
            )
            
            logger.info("Enhanced QA chain initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing enhanced QA chain: {str(e)}")
            raise
    
    def get_answer(self, question: str) -> Dict[str, Any]:
        """
        質問に対する回答を取得
        
        Args:
            question (str): 質問文
            
        Returns:
            Dict[str, Any]: 回答と関連情報
        """
        try:
            if not self.qa_chain:
                raise ValueError("QA chain not initialized")
            
            # 回答の取得
            result = self.qa_chain({"question": question})
            
            # 関連ドキュメントの取得
            docs = self.vector_store.similarity_search(question, k=3)
            sources = [doc.metadata for doc in docs]
            
            return {
                "answer": result["answer"],
                "sources": sources,
                "chat_history": result["chat_history"],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting answer: {str(e)}")
            return {
                "answer": "申し訳ありません。エラーが発生しました。",
                "sources": [],
                "chat_history": [],
                "timestamp": datetime.now().isoformat()
            }
    
    def clear_history(self):
        """会話履歴のクリア"""
        try:
            self.memory.clear()
            logger.info("Chat history cleared")
        except Exception as e:
            logger.error(f"Error clearing chat history: {str(e)}")
            raise 