from typing import Dict, Any, List, Optional
import logging
from pathlib import Path
import os
from notion_client import Client
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

class FeedbackManager:
    def __init__(self, database_id: Optional[str] = None):
        """
        フィードバック管理クラスの初期化
        
        Args:
            database_id (Optional[str]): NotionデータベースのID
        """
        self.notion = Client(auth=os.getenv("NOTION_TOKEN"))
        self.database_id = database_id or os.getenv("NOTION_DATABASE_ID")
        
        if not self.database_id:
            logger.warning("Notion database ID not set. Feedback will be stored locally only.")
    
    def save_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        フィードバックを保存
        
        Args:
            feedback_data (Dict[str, Any]): 保存するフィードバックデータ
                必要なキー:
                - question: 質問内容
                - answer: 回答内容
                - rating: 評価（1-5）
                - comment: コメント（オプション）
                
        Returns:
            Dict[str, Any]: 保存結果
        """
        try:
            if not self.database_id:
                return self._save_feedback_locally(feedback_data)
            
            # Notionに保存
            response = self.notion.pages.create(
                parent={"database_id": self.database_id},
                properties={
                    "Question": {
                        "title": [
                            {
                                "text": {
                                    "content": feedback_data["question"]
                                }
                            }
                        ]
                    },
                    "Rating": {
                        "number": feedback_data["rating"]
                    },
                    "Date": {
                        "date": {
                            "start": datetime.now().isoformat()
                        }
                    }
                },
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": f"Answer: {feedback_data['answer']}"
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": f"Comment: {feedback_data.get('comment', '')}"
                                    }
                                }
                            ]
                        }
                    }
                ]
            )
            
            return {
                "success": True,
                "notion_page_id": response["id"]
            }
            
        except Exception as e:
            logger.error(f"Error saving feedback to Notion: {str(e)}")
            return self._save_feedback_locally(feedback_data)
    
    def _save_feedback_locally(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        フィードバックをローカルに保存
        
        Args:
            feedback_data (Dict[str, Any]): 保存するフィードバックデータ
            
        Returns:
            Dict[str, Any]: 保存結果
        """
        try:
            feedback_dir = Path("feedback")
            feedback_dir.mkdir(exist_ok=True)
            
            feedback_file = feedback_dir / f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(feedback_file, "w", encoding="utf-8") as f:
                import json
                json.dump(feedback_data, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "local_file": str(feedback_file)
            }
            
        except Exception as e:
            logger.error(f"Error saving feedback locally: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_feedback_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        フィードバック履歴を取得
        
        Args:
            limit (int): 取得する履歴の最大数
            
        Returns:
            List[Dict[str, Any]]: フィードバック履歴のリスト
        """
        try:
            if not self.database_id:
                return self._get_local_feedback_history(limit)
            
            # Notionから履歴を取得
            response = self.notion.databases.query(
                database_id=self.database_id,
                page_size=limit,
                sorts=[
                    {
                        "property": "Date",
                        "direction": "descending"
                    }
                ]
            )
            
            feedback_history = []
            for page in response["results"]:
                properties = page["properties"]
                feedback_history.append({
                    "question": properties["Question"]["title"][0]["text"]["content"],
                    "rating": properties["Rating"]["number"],
                    "date": properties["Date"]["date"]["start"],
                    "page_id": page["id"]
                })
            
            return feedback_history
            
        except Exception as e:
            logger.error(f"Error getting feedback history from Notion: {str(e)}")
            return self._get_local_feedback_history(limit)
    
    def _get_local_feedback_history(self, limit: int) -> List[Dict[str, Any]]:
        """
        ローカルのフィードバック履歴を取得
        
        Args:
            limit (int): 取得する履歴の最大数
            
        Returns:
            List[Dict[str, Any]]: フィードバック履歴のリスト
        """
        try:
            feedback_dir = Path("feedback")
            if not feedback_dir.exists():
                return []
            
            feedback_files = sorted(
                feedback_dir.glob("feedback_*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )[:limit]
            
            feedback_history = []
            for file in feedback_files:
                with open(file, "r", encoding="utf-8") as f:
                    import json
                    feedback_data = json.load(f)
                    feedback_history.append(feedback_data)
            
            return feedback_history
            
        except Exception as e:
            logger.error(f"Error getting local feedback history: {str(e)}")
            return [] 