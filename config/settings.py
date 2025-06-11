import os
from pathlib import Path

class Settings:
    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # OpenAI API設定
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        
        # Notion API設定
        self.notion_token = os.getenv("NOTION_TOKEN", "")
        
    def get_vector_store_config(self):
        return {
            "collection_name": "documents",
            "embedding_model": "text-embedding-ada-002",
            "chunk_size": 1000,
            "chunk_overlap": 200
        }
    
    def get_qa_config(self):
        return {
            "model": "gpt-3.5-turbo",
            "temperature": 0.1,
            "max_tokens": 1000
        }

settings = Settings() 