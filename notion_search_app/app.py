import os
import json
import notion_client
import serpapi
from openai import OpenAI, APIStatusError, APIConnectionError
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
CATEGORIES_STR = os.getenv("CATEGORIES", "仕事,プログラミング,趣味,学習,ニュース,生活ハック,その他")
CATEGORIES = [category.strip() for category in CATEGORIES_STR.split(',')]

app = Flask(__name__)
notion = notion_client.Client(auth=NOTION_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def add_page_to_notion(title, content, url, query, category):
    if not all([NOTION_API_KEY, NOTION_DATABASE_ID]):
        return None, {"error": "Notion API Key or Database ID is not configured."}
    try:
        new_page = {
            "Title": {"title": [{"text": {"content": title}}]},
            "URL": {"url": url},
            "Content": {"rich_text": [{"text": {"content": content}}]},
            "Query": {"rich_text": [{"text": {"content": query}}]},
            "Category": {"multi_select": [{"name": category}]},
        }
        response = notion.pages.create(parent={"database_id": NOTION_DATABASE_ID}, properties=new_page)
        return response, None
    except notion_client.errors.APIResponseError as e:
        return None, {"error": "Notion API Error", "details": str(e)}
    except Exception as e:
        return None, {"error": "An unexpected error occurred while saving to Notion", "details": str(e)}

def search_with_google(query):
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_key:
        return None, {"error": "SerpApi API Key is not configured."}
    try:
        params = {"q": query, "api_key": serpapi_key, "engine": "google", "hl": "ja", "gl": "jp"}
        search = serpapi.GoogleSearch(params)
        results = search.get_dict()
        if "error" in results:
             return None, {"error": "SerpApi Error", "details": results["error"]}
        if "organic_results" in results and results["organic_results"]:
            first_result = results["organic_results"][0]
            return (first_result.get("snippet", "Snippet not found."), first_result.get("link")), None
        return ("No results found.", None), None
    except Exception as e:
        return None, {"error": "An unexpected error occurred with SerpApi", "details": str(e)}

def search_with_chatgpt(query):
    if not OPENAI_API_KEY:
        return None, {"error": "OpenAI API Key is not configured."}
    try:
        completion = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Please provide concise and clear answers."},
                {"role": "user", "content": query}
            ]
        )
        content = completion.choices[0].message.content
        return (content, "ChatGPT"), None
    except (APIStatusError, APIConnectionError) as e:
        return None, {"error": "OpenAI API Error", "details": str(e)}
    except Exception as e:
        return None, {"error": "An unexpected error occurred with OpenAI", "details": str(e)}

def get_category_suggestions(text):
    if not OPENAI_API_KEY:
        return None, {"error": "OpenAI API Key is not configured."}
    prompt = f"""Analyze the following text and suggest up to 3 relevant categories from the list below.
    Respond ONLY with a JSON array of strings (e.g., ["Category1", "Category2"]). Do not include any other text.
    ---
    Text: "{text}"
    ---
    Category List: {CATEGORIES}
    ---
    """
    try:
        completion = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert text classifier."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        response_text = completion.choices[0].message.content
        response_data = json.loads(response_text)
        if isinstance(response_data, dict):
            for key, value in response_data.items():
                if isinstance(value, list):
                    return value, None
            return None, {"error": "Could not find a list of categories in AI response."}
        elif isinstance(response_data, list):
             return response_data, None
        else:
             return None, {"error": "AI returned an unexpected format for categories."}
    except (APIStatusError, APIConnectionError) as e:
        return None, {"error": "OpenAI API Error during categorization", "details": str(e)}
    except Exception as e:
        return None, {"error": "An unexpected error occurred during categorization", "details": str(e)}

@app.route('/')
def index():
    # This will be created in a later step
    return "<h1>Notion Search App</h1><p>Frontend will be here.</p>"

@app.route("/api/save", methods=['POST'])
def api_save():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    response, error = add_page_to_notion(
        title=data.get('title'),
        content=data.get('content'),
        url=data.get('url'),
        query=data.get('query'),
        category=data.get('category')
    )
    if error:
        return jsonify(error), 500
    return jsonify({"success": True, "page_id": response.get("id")})

@app.route("/api/search", methods=['POST'])
def api_search():
    data = request.get_json()
    if not data or not data.get('query') or not data.get('engine'):
        return jsonify({"error": "Request must include 'query' and 'engine'"}), 400
    query = data['query']
    engine = data['engine']
    result, error = None, None
    if engine == 'google':
        result, error = search_with_google(query)
    elif engine == 'chatgpt':
        result, error = search_with_chatgpt(query)
    else:
        return jsonify({"error": "Invalid search engine specified"}), 400
    if error:
        return jsonify(error), 502
    content, source_url = result
    suggestions, cat_error = get_category_suggestions(f"Query: {query}\nContent: {content}")
    if cat_error:
        print(f"Categorization failed: {cat_error}")
        suggestions = ["その他"]
    return jsonify({"content": content, "source_url": source_url, "suggestions": suggestions})

if __name__ == '__main__':
    if not all([NOTION_API_KEY, NOTION_DATABASE_ID]):
        print("WARNING: NOTION_API_KEY and NOTION_DATABASE_ID must be set in .env file.")
    app.run(debug=True, port=5000)
