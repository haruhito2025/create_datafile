# DocuMind AI - OCR比較・文書処理システム

PDFドキュメントのOCR処理と質問応答を行うStreamlitアプリケーションです。複数のOCRエンジンによる結果比較機能と、ページ別詳細確認機能を提供します。

## 🌟 主な機能

### 📄 OCR処理機能
- **EasyOCR**: 高精度な日本語・英語OCR
- **PaddleOCR**: 多言語対応OCR
- **比較モード**: 両エンジンの結果を並列比較

### 🔍 ページ別確認機能
- **1ページずつ詳細確認**: 元PDFとOCR結果を並べて表示
- **ナビゲーション**: ボタン・スライダー・直接入力でのページ移動
- **3つの表示モード**: PDF画像+OCR結果、OCR結果のみ、PDF画像のみ

### 📊 詳細比較分析
- **一致率計算**: 2つのOCRエンジンの結果比較
- **類似度スコア**: テキスト全体の類似度分析
- **共通・固有単語検出**: エンジン別の特徴分析
- **差分表示**: HTML形式での詳細差分

### 💬 質問応答システム
- **ベクトル検索**: ChromaDBによる高速検索
- **AI回答生成**: OpenAI GPTによる自然言語回答
- **参照元表示**: 回答の根拠となるドキュメント箇所を表示

## 🚀 セットアップ

### 前提条件
- Python 3.8以上
- OpenAI APIキー

### インストール

1. リポジトリをクローン
```bash
git clone <repository-url>
cd create_datefile
```

2. 依存関係をインストール
```bash
pip install -r requirements.txt
```

3. 環境変数の設定
`.env`ファイルを作成し、以下を設定：
```
OPENAI_API_KEY=your_openai_api_key_here
```

4. アプリケーションを起動
```bash
streamlit run main.py
```

## 📁 プロジェクト構造

```
create_datefile/
├── main.py                     # メインアプリケーション
├── requirements.txt            # 依存関係
├── config/
│   └── settings.py            # 設定ファイル
├── modules/
│   ├── document_processor/    # ドキュメント処理
│   │   ├── unified_ocr.py    # OCRエンジン統合
│   │   └── document_processor.py
│   ├── ocr_comparison/        # OCR比較機能
│   │   └── comparison_manager.py
│   ├── vector_store/          # ベクトルストア
│   │   └── chroma_store.py
│   ├── qa_interface/          # 質問応答インターフェース
│   │   └── retrieval_qa.py
│   └── integrations/          # 外部サービス連携
│       └── notion_client.py
├── utils/                     # ユーティリティ
│   ├── file_utils.py
│   └── text_processing.py
├── data/                      # データディレクトリ
│   ├── uploads/               # アップロード済みファイル
│   ├── processed/             # 処理済みファイル
│   └── chroma/                # ベクトルDB
└── models/                    # OCRモデル
```

## 🎮 使用方法

### 1. PDF処理
1. PDFファイルをアップロード
2. OCRエンジンを選択（EasyOCR / PaddleOCR / 両方）
3. 処理開始ボタンをクリック
4. 結果を確認

### 2. ページ別確認
1. 「ページ別確認」タブを選択
2. ナビゲーションボタンでページ移動
3. 表示モードを選択
4. 元PDFとOCR結果を比較

### 3. 質問応答
1. 「質問応答」ページに移動
2. ドキュメントに関する質問を入力
3. AI生成の回答と参照元を確認

## 🔧 技術仕様

### 使用技術
- **フロントエンド**: Streamlit
- **OCRエンジン**: EasyOCR, PaddleOCR
- **PDF処理**: PyMuPDF (fitz)
- **ベクトルDB**: ChromaDB
- **AI**: OpenAI GPT
- **言語処理**: LangChain

### 主要ライブラリ
- `streamlit`: WebUIフレームワーク
- `easyocr`: OCRエンジン
- `paddleocr`: OCRエンジン
- `PyMuPDF`: PDF処理
- `chromadb`: ベクトルデータベース
- `openai`: AI言語モデル
- `langchain`: LLMアプリケーションフレームワーク

## 📊 パフォーマンス

### OCR処理速度
- **EasyOCR**: 約2-3秒/ページ（日本語）
- **PaddleOCR**: 約1-2秒/ページ（日本語）

### 比較分析
- **一致率計算**: リアルタイム
- **類似度スコア**: 高精度difflib使用
- **差分表示**: HTML形式で詳細表示

## 🤝 貢献

プルリクエストやイシューの報告を歓迎します。

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🎯 今後の予定

- [ ] 他言語OCRエンジンの追加
- [ ] バッチ処理機能
- [ ] API提供
- [ ] Docker対応
- [ ] クラウドデプロイ 