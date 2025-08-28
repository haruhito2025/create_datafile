import os
import json
import notion_client
import serpapi
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# --- 環境変数から設定を読み込み ---
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # 今後のステップで使用

# --- FlaskアプリケーションとNotionクライアントの初期化 ---
app = Flask(__name__)
notion = notion_client.Client(auth=NOTION_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)


def add_page_to_notion(title, content, url, query, category):
    """
    指定された内容でNotionデータベースに新しいページを追加する。
    """
    if not all([NOTION_API_KEY, NOTION_DATABASE_ID]):
        print("エラー: NotionのAPIキーまたはデータベースIDが設定されていません。")
        return None

    try:
        new_page = {
            "Title": {"title": [{"text": {"content": title}}]},
            "URL": {"url": url},
            "Content": {"rich_text": [{"text": {"content": content}}]},
            "Query": {"rich_text": [{"text": {"content": query}}]},
            "Category": {"multi_select": [{"name": category}]},
        }

        response = notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties=new_page
        )
        print("Notionにページが正常に追加されました。")
        return response
    except Exception as e:
        print(f"Notionへのページ追加中にエラーが発生しました: {e}")
        return None

@app.route('/')
def index():
    """
    フロントエンドのHTMLページを返す
    """
    return render_template('index.html')


# --- 検索・AI関連の関数 ---

# AIが分類を選ぶためのカテゴリリスト
CATEGORIES = ["仕事", "プログラミング", "趣味", "学習", "ニュース", "生活ハック", "その他"]

def search_with_google(query):
    """
    SerpApiを使用してGoogle検索を実行し、最初のオーガニック検索結果のスニペットとリンクを返す。
    """
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_key:
        return {"error": "SerpApiのAPIキーが設定されていません。"}, None

    params = {
        "q": query,
        "api_key": serpapi_key,
        "engine": "google",
        "hl": "ja",
        "gl": "jp",
    }
    search = serpapi.GoogleSearch(params)
    results = search.get_dict()

    if "organic_results" in results and results["organic_results"]:
        first_result = results["organic_results"][0]
        return first_result.get("snippet", "スニペットが見つかりません。"), first_result.get("link")
    return "検索結果が見つかりませんでした。", None

def search_with_chatgpt(query):
    """
    OpenAI APIを使用してChatGPTに質問し、回答を返す。
    """
    if not OPENAI_API_KEY:
        return {"error": "OpenAIのAPIキーが設定されていません。"}, None

    try:
        completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは優秀なアシスタントです。簡潔に、しかし分かりやすく回答してください。"},
                {"role": "user", "content": query}
            ]
        )
        content = completion.choices[0].message.content
        return content, "ChatGPT"
    except Exception as e:
        return f"ChatGPTからの回答取得中にエラー: {e}", "ChatGPT"

def get_category_suggestions(text):
    """
    与えられたテキストの内容を解釈し、定義済みのカテゴリリストから最も関連性の高いものを3つ提案する。
    """
    if not OPENAI_API_KEY:
        return ["エラー: OpenAIキー未設定"]

    prompt = f"""
    以下のテキスト内容を分析し、最も関連性が高いと思われるカテゴリを下記のリストから最大3つ選んでください。
    回答はカテゴリ名のリスト（例: ["カテゴリ1", "カテゴリ2"]）の形式で、JSON配列としてのみ返してください。他の言葉は一切含めないでください。

    ---
    テキスト内容:
    "{text}"
    ---
    カテゴリリスト:
    {CATEGORIES}
    ---
    """
    try:
        completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたはテキストを分類する専門家です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )
        response_text = completion.choices[0].message.content
        # AIの回答からJSONリストを抽出する
        suggested_categories = json.loads(response_text)
        return suggested_categories
    except Exception as e:
        print(f"カテゴリ分類中にエラー: {e}")
        # エラー時はデフォルトのカテゴリ候補を返す
        return ["仕事", "学習", "その他"]

# --- APIエンドポイント ---

@app.route("/api/save", methods=['POST'])
def api_save():
    """
    フロントエンドからデータを受け取り、Notionにページを追加する。
    """
    data = request.get_json()
    response = add_page_to_notion(
        title=data.get('title'),
        content=data.get('content'),
        url=data.get('url'),
        query=data.get('query'),
        category=data.get('category')
    )
    if response:
        return jsonify({"success": True, "page_id": response.get("id")})
    else:
        return jsonify({"success": False, "error": "Failed to save to Notion"}), 500

@app.route("/api/search", methods=['POST'])
def api_search():
    data = request.get_json()
    query = data.get('query')
    engine = data.get('engine')

    if not query or not engine:
        return jsonify({"error": "クエリとエンジンが必要です"}), 400

    content, source_url = "", ""
    if engine == 'google':
        content, source_url = search_with_google(query)
    elif engine == 'chatgpt':
        content, source_url = search_with_chatgpt(query)
    else:
        return jsonify({"error": "無効な検索エンジンです"}), 400

    if isinstance(content, dict) and "error" in content: # APIキーエラーなどをハンドリング
        return jsonify(content), 500

    suggestions = get_category_suggestions(f"クエリ: {query}\n内容: {content}")

    return jsonify({
        "content": content,
        "source_url": source_url,
        "suggestions": suggestions
    })


# --- メインの実行ブロック ---
if __name__ == '__main__':
    # サーバーを起動する前に、必要な環境変数が設定されているか確認
    if not all([NOTION_API_KEY, NOTION_DATABASE_ID]):
        print("警告: NOTION_API_KEY と NOTION_DATABASE_ID の両方を.envファイルに設定してください。")

    # ローカルネットワーク内の他のデバイス（iPhone等）からもアクセス可能にする
    app.run(debug=True, host='0.0.0.0', port=5001)
