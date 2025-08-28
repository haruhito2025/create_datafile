# Notion統合検索アプリケーション

## 概要

このWebアプリケーションは、GoogleまたはChatGPT（GPT-4o-mini等）を使用して情報を検索し、その結果をNotionデータベースに自動で保存・整理するためのツールです。調べ物や情報収集の効率を上げることを目的としています。

## 主な機能

-   **マルチエンジン検索**: 1つの画面からGoogleとChatGPTを切り替えて検索できます。
-   **AIによる自動カテゴリ分類**: 検索結果の内容をAIが解釈し、予め定義されたカテゴリリストから最適なものをいくつか提案します。
-   **Notionへのワンクリック保存**: 検索結果と選択したカテゴリを、ワンクリックで指定のNotionデータベースに保存できます。
-   **柔軟な設定**: OpenAIのモデル名やカテゴリリストは、`.env`ファイルで簡単に変更可能です。

## 必要なもの

-   Python 3.7以上
-   Notionアカウント
-   OpenAI APIキー
-   SerpApi APIキー

## セットアップ手順

1.  **リポジトリのクローン**
    ```bash
    git clone <repository_url>
    cd notion_search_app
    ```

2.  **仮想環境の作成と有効化**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **依存ライブラリのインストール**
    ```bash
    pip install -r requirements.txt
    ```

4.  **`.env`ファイルの作成**
    -   `notion_search_app` ディレクトリ内に `.env` という名前のファイルを作成します。
    -   以下の「`.env`ファイルの内容」セクションを参考に、ご自身のAPIキーなどを設定してください。

5.  **Notionデータベースの準備**
    -   以下の「Notionデータベースのセットアップ」セクションを参考に、結果を保存するためのデータベースを準備してください。

## `.env`ファイルの内容

`.env`ファイルに以下の内容をコピーし、`=`の右側をご自身の情報に書き換えてください。

```plaintext
# --- API Keys (Required) ---
NOTION_API_KEY=Your_Notion_API_Key_Here
NOTION_DATABASE_ID=Your_Notion_Database_ID_Here
OPENAI_API_KEY=Your_OpenAI_API_Key_Here
SERPAPI_API_KEY=Your_SerpApi_API_Key_Here

# --- Flexible Configurations (Optional) ---
OPENAI_MODEL=gpt-4o-mini
CATEGORIES=仕事,プログラミング,趣味,学習,ニュース,生活ハック,その他
```

-   `NOTION_DATABASE_ID`: NotionデータベースのURLから32文字のID部分をコピーします。
-   `CATEGORIES`: AIに提案させたいカテゴリをカンマ区切りで指定します。

## Notionデータベースのセットアップ

1.  Notionで新しいデータベースを作成します（フルページ推奨）。
2.  以下の5つのプロパティを、**指定された名前と種類で**作成・設定してください（大文字・小文字も区別されます）。

| プロパティ名 | 種類 (Type)         |
| :----------- | :------------------ |
| `Title`      | `タイトル` (Title)  |
| `URL`        | `URL`               |
| `Content`    | `テキスト` (Text)   |
| `Query`      | `テキスト` (Text)   |
| `Category`   | `マルチセレクト` (Multi-select) |

3.  Notionの[インテグレーション管理ページ](https://www.notion.so/my-integrations)で新しいインテグレーションを作成し、「シークレット」をコピーして`NOTION_API_KEY`に設定します。
4.  作成したデータベースの「...」メニューから「コネクトの追加」を選び、作成したインテグレーションを連携させます。

## アプリケーションの実行

セットアップが完了したら、以下のコマンドでWebサーバーを起動します。

```bash
cd notion_search_app
source venv/bin/activate
flask run
```
