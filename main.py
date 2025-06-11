import streamlit as st
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import time
from dotenv import load_dotenv
import base64
from PyPDF2 import PdfReader
from datetime import datetime
import sys
import fitz  # PyMuPDF for PDF display

# 文字エンコーディングの設定
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except TypeError:
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr)

# .envファイルから環境変数を読み込む (これがAPIキーを読み込みます)
load_dotenv()

# Streamlitのページ設定
st.set_page_config(
    page_title="DocuMind AI",
    page_icon="📄",
    layout="wide"
)

# --- モジュールのインポート ---
# load_dotenv() の後にインポートするのが安全です
from config.settings import settings
from modules.document_processor.unified_ocr import OCRFactory
from modules.document_processor import DocumentProcessor
from modules.vector_store.chroma_store import ChromaVectorStore
from modules.qa_interface.retrieval_qa import RetrievalQAInterface, EnhancedQAInterface
from modules.integrations.notion_client import FeedbackManager
from modules.ocr_comparison.comparison_manager import OCRComparisonManager
from utils.file_utils import FileManager, validate_pdf_file
from utils.text_processing import clean_ocr_text, format_text_for_display

# --- ロギング設定 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@st.cache_resource
def initialize_components():
    """
    アプリケーションのコンポーネントを初期化します。
    st.cache_resourceでキャッシュすることで、再実行時のパフォーマンスを向上させます。
    """
    try:
        components = {}
        components['file_manager'] = FileManager()
        components['ocr_factory'] = OCRFactory()
        components['easy_ocr'] = components['ocr_factory'].create_engine("easyocr")
        
        try:
            logger.info("PaddleOCRの初期化を開始します...")
            components['paddle_ocr'] = components['ocr_factory'].create_engine("paddle")
            logger.info("PaddleOCRは正常に初期化されました。")
        except Exception as e:
            logger.warning(f"PaddleOCRの初期化に失敗しました。PaddleOCRなしで続行します。エラー: {e}", exc_info=True)
            st.toast(f"注意: PaddleOCRの初期化に失敗しました。詳細はログを確認してください。", icon="⚠️")
            st.warning("PaddleOCRが利用できないため、EasyOCRのみ使用可能です。OCRの比較機能は無効になります。")
            components['paddle_ocr'] = None

        components['vector_store'] = ChromaVectorStore()
        components['qa_interface'] = RetrievalQAInterface(components['vector_store'])
        components['enhanced_qa'] = EnhancedQAInterface(components['vector_store'])
        components['comparison_manager'] = OCRComparisonManager()
        components['notion_client'] = FeedbackManager()
        
        logger.info("全てのコンポーネントが正常に初期化されました。")
        return components

    except Exception as e:
        logger.error(f"コンポーネントの初期化中に致命的なエラーが発生しました: {e}")
        st.error("アプリケーションの初期化中に致命的なエラーが発生しました。")
        st.error("OpenAIのAPIキーが正しく設定されているか、.envファイルを確認してください。")
        st.exception(e)
        return None

def show_pdf_processing_page(components):
    """PDF処理ページの表示"""
    st.header("📄 PDF処理とベクトル化")
    
    uploaded_file = st.file_uploader("PDFファイルをアップロード", type=["pdf"])
    
    if uploaded_file is None:
        return

    try:
        file_path = components['file_manager'].save_uploaded_file(uploaded_file.getvalue(), uploaded_file.name)
        if not validate_pdf_file(file_path)["valid"]:
            st.error("ファイルの検証に失敗しました。")
            return
        
        # PDFの基本情報を表示
        page_count = get_pdf_page_count(file_path)
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"📄 ファイル名: {uploaded_file.name}")
        with col2:
            st.info(f"📖 ページ数: {page_count}ページ")
        
        # PDF表示機能
        with st.expander("📖 元のPDFを表示", expanded=False):
            pdf_display_url = display_pdf(file_path)
            if pdf_display_url:
                st.markdown(f'<iframe src="{pdf_display_url}" width="100%" height="600px"></iframe>', 
                           unsafe_allow_html=True)
            else:
                st.error("PDFの表示に失敗しました。")
        
        ocr_options = ["EasyOCR"]
        if components.get("paddle_ocr"):
            ocr_options.extend(["PaddleOCR", "両方"])

        ocr_engine_choice = st.radio("OCRエンジンを選択", ocr_options, horizontal=True)
        
        if not st.button("🚀 OCR処理とベクトル化を開始", type="primary"):
            return
            
        # プログレス表示の準備
        progress_container, progress_bar, status_text, detailed_status = create_progress_container()
        
        if ocr_engine_choice == "両方":
            # EasyOCR処理
            update_progress(progress_bar, status_text, detailed_status, 
                           0.1, "EasyOCR初期化中...", "EasyOCRエンジンを準備しています")
            
            update_progress(progress_bar, status_text, detailed_status, 
                           0.2, "EasyOCR処理中...", f"PDFを画像に変換中... ({page_count}ページ)")
            
            easy_result = components['easy_ocr'].process_document(file_path)
            
            if not easy_result.get('success', False):
                st.error(f"EasyOCRでエラーが発生しました: {easy_result.get('error', '不明なエラー')}")
                return
            
            easy_result_text = easy_result.get('text', '')
            update_progress(progress_bar, status_text, detailed_status, 
                           0.4, "EasyOCR完了", f"文字数: {len(easy_result_text)} 文字")
            
            # PaddleOCR処理
            update_progress(progress_bar, status_text, detailed_status, 
                           0.5, "PaddleOCR処理中...", f"PDFを画像に変換中... ({page_count}ページ)")
            
            paddle_result = components['paddle_ocr'].process_document(file_path)
            
            if not paddle_result.get('success', False):
                st.error(f"PaddleOCRでエラーが発生しました: {paddle_result.get('error', '不明なエラー')}")
                return
            
            paddle_result_text = paddle_result.get('text', '')
            update_progress(progress_bar, status_text, detailed_status, 
                           0.7, "PaddleOCR完了", f"文字数: {len(paddle_result_text)} 文字")

            # 比較処理
            update_progress(progress_bar, status_text, detailed_status, 
                           0.8, "結果比較中...", "OCR結果の詳細分析を実行中")
            comparison = components['comparison_manager'].compare_ocr_results(easy_result_text, paddle_result_text)
            
            update_progress(progress_bar, status_text, detailed_status, 
                           0.9, "比較完了", "比較結果を表示します")
            
            # 基本的な比較結果表示
            st.subheader("📊 OCR結果比較")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("EasyOCR文字数", easy_result.get('total_chars', 0))
            with col2:
                st.metric("PaddleOCR文字数", paddle_result.get('total_chars', 0))
            with col3:
                st.metric("一致率", f"{comparison['matching_rate']:.2%}")
            
            # タブによる詳細比較表示
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 全体比較", "📄 ページ別比較", "📈 詳細分析", "🔍 差分表示", "👁️ PDF対比"])
            
            with tab1:
                st.subheader("全体のOCR結果比較")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**EasyOCR 結果**")
                    st.text_area("EasyOCR結果", easy_result_text, height=400, key="easy_full")
                with col2:
                    st.markdown("**PaddleOCR 結果**")
                    st.text_area("PaddleOCR結果", paddle_result_text, height=400, key="paddle_full")
            
            with tab2:
                st.subheader("ページ別結果比較")
                easy_pages = easy_result.get('text_by_page', {})
                paddle_pages = paddle_result.get('text_by_page', {})
                all_pages = set(easy_pages.keys()) | set(paddle_pages.keys())
                
                if all_pages:
                    display_page_comparison(get_all_pdf_pages_as_images(file_path), easy_pages, paddle_pages, 1, "both")
            
            with tab3:
                st.subheader("詳細分析結果")
                analysis_col1, analysis_col2 = st.columns(2)
                
                with analysis_col1:
                    st.markdown("**処理統計情報**")
                    st.write(f"- EasyOCR処理ページ数: {easy_result.get('pages_processed', '不明')}")
                    st.write(f"- PaddleOCR処理ページ数: {paddle_result.get('pages_processed', '不明')}")
                    st.write(f"- 文字数差異: {abs(easy_result.get('total_chars', 0) - paddle_result.get('total_chars', 0))}")
                
                with analysis_col2:
                    st.markdown("**比較メトリクス**")
                    if 'similarity_score' in comparison:
                        st.write(f"- 類似度スコア: {comparison['similarity_score']:.3f}")
                    if 'common_words' in comparison:
                        st.write(f"- 共通単語数: {len(comparison['common_words'])}")
                    if 'unique_easy' in comparison:
                        st.write(f"- EasyOCR固有単語: {len(comparison['unique_easy'])}")
                    if 'unique_paddle' in comparison:
                        st.write(f"- PaddleOCR固有単語: {len(comparison['unique_paddle'])}")
            
            with tab4:
                st.subheader("差分表示")
                st.info("赤: EasyOCRのみ, 青: PaddleOCRのみ, 緑: 共通")
                
                # 簡単な差分表示（実装可能であれば）
                if comparison.get('diff_html'):
                    st.markdown(comparison['diff_html'], unsafe_allow_html=True)
                else:
                    st.write("詳細な差分表示は実装中です。")
            
            with tab5:
                st.subheader("PDF原本との対比")
                pdf_col, ocr_col = st.columns([1, 1])
                
                with pdf_col:
                    st.markdown("**📄 元のPDF**")
                    pdf_display_url = display_pdf(file_path)
                    if pdf_display_url:
                        st.markdown(f'<iframe src="{pdf_display_url}" width="100%" height="500px"></iframe>', 
                                   unsafe_allow_html=True)
                    else:
                        st.error("PDFの表示に失敗しました。")
                
                with ocr_col:
                    st.markdown("**📝 OCR結果比較**")
                    ocr_view_option = st.radio("表示するOCR結果", ["EasyOCR", "PaddleOCR"], horizontal=True)
                    
                    if ocr_view_option == "EasyOCR":
                        st.text_area("EasyOCR結果（PDF対比用）", easy_result_text, height=500, key="pdf_compare_easy")
                    else:
                        st.text_area("PaddleOCR結果（PDF対比用）", paddle_result_text, height=500, key="pdf_compare_paddle")

            # ユーザーにどちらのテキストを使用するか選択させる
            st.subheader("🎯 ベクトル化に使用するテキストの選択")
            chosen_text = st.radio("ベクトル化に使用するテキストを選択:", ("EasyOCR", "PaddleOCR", "両方を結合"))
            
            if chosen_text == "EasyOCR":
                final_text = easy_result_text
            elif chosen_text == "PaddleOCR":
                final_text = paddle_result_text
            else:
                final_text = f"=== EasyOCR結果 ===\n{easy_result_text}\n\n=== PaddleOCR結果 ===\n{paddle_result_text}"

        elif ocr_engine_choice == "EasyOCR":
            update_progress(progress_bar, status_text, detailed_status, 
                           0.2, "EasyOCR処理中...", f"PDFを画像に変換中... ({page_count}ページ)")
            
            easy_result = components['easy_ocr'].process_document(file_path)
            if not easy_result.get('success', False):
                st.error(f"EasyOCRでエラーが発生しました: {easy_result.get('error', '不明なエラー')}")
                return
            final_text = easy_result.get('text', '')
            
            update_progress(progress_bar, status_text, detailed_status, 
                           0.8, "EasyOCR完了", f"文字数: {len(final_text)} 文字")
            
            st.subheader("📄 EasyOCR抽出結果")
            
            # タブで詳細表示とページ別表示を提供
            tab1, tab2 = st.tabs(["📋 全体結果", "📄 ページ別確認"])
            
            with tab1:
                # PDF対比表示
                pdf_col, ocr_col = st.columns([1, 1])
                with pdf_col:
                    st.markdown("**📄 元のPDF**")
                    pdf_display_url = display_pdf(file_path)
                    if pdf_display_url:
                        st.markdown(f'<iframe src="{pdf_display_url}" width="100%" height="500px"></iframe>', 
                                   unsafe_allow_html=True)
                
                with ocr_col:
                    st.markdown("**📝 EasyOCR結果**")
                    st.text_area("抽出結果", final_text, height=500)
            
            with tab2:
                # ページ別確認
                display_page_comparison(get_all_pdf_pages_as_images(file_path), easy_result.get('text_by_page', {}), {}, 1, "easy")
            
            # 処理統計の表示
            col1, col2 = st.columns(2)
            with col1:
                st.metric("文字数", easy_result.get('total_chars', 0))
            with col2:
                st.metric("処理ページ数", easy_result.get('pages_processed', 0))

        elif ocr_engine_choice == "PaddleOCR":
            update_progress(progress_bar, status_text, detailed_status, 
                           0.2, "PaddleOCR処理中...", f"PDFを画像に変換中... ({page_count}ページ)")
            
            paddle_result = components['paddle_ocr'].process_document(file_path)
            if not paddle_result.get('success', False):
                st.error(f"PaddleOCRでエラーが発生しました: {paddle_result.get('error', '不明なエラー')}")
                return
            final_text = paddle_result.get('text', '')
            
            update_progress(progress_bar, status_text, detailed_status, 
                           0.8, "PaddleOCR完了", f"文字数: {len(final_text)} 文字")
            
            st.subheader("📄 PaddleOCR抽出結果")
            
            # タブで詳細表示とページ別表示を提供
            tab1, tab2 = st.tabs(["📋 全体結果", "📄 ページ別確認"])
            
            with tab1:
                # PDF対比表示
                pdf_col, ocr_col = st.columns([1, 1])
                with pdf_col:
                    st.markdown("**📄 元のPDF**")
                    pdf_display_url = display_pdf(file_path)
                    if pdf_display_url:
                        st.markdown(f'<iframe src="{pdf_display_url}" width="100%" height="500px"></iframe>', 
                                   unsafe_allow_html=True)
                
                with ocr_col:
                    st.markdown("**📝 PaddleOCR結果**")
                    st.text_area("抽出結果", final_text, height=500)
            
            with tab2:
                # ページ別確認
                display_page_comparison(get_all_pdf_pages_as_images(file_path), {}, paddle_result.get('text_by_page', {}), 1, "paddle")
            
            # 処理統計の表示
            col1, col2 = st.columns(2)
            with col1:
                st.metric("文字数", paddle_result.get('total_chars', 0))
            with col2:
                st.metric("処理ページ数", paddle_result.get('pages_processed', 0))

        # ベクトル化処理
        update_progress(progress_bar, status_text, detailed_status, 
                       0.9, "ベクトル化処理中...", "テキストチャンクを生成中")
        
        doc_processor = DocumentProcessor()
        chunks = doc_processor.process_text(final_text, document_name=file_path.name)
        if chunks:
            components['vector_store'].add_documents(chunks)
            update_progress(progress_bar, status_text, detailed_status, 
                           1.0, "処理完了", f"{len(chunks)}個のテキストチャンクがベクトルストアに追加されました")
            st.success(f"処理が完了し、{len(chunks)}個のテキストチャンクがベクトルストアに追加されました。")
        else:
            st.warning("テキストからチャンクを生成できませんでした。")

        components['file_manager'].move_to_processed(file_path)

    except Exception as e:
        logger.error(f"PDF処理中にエラーが発生しました: {e}")
        st.error(f"PDFの処理中にエラーが発生しました: {e}")
        st.exception(e)


def show_qa_page(components):
    """質問応答ページの表示"""
    st.header("💬 質問応答システム")
    
    if components['vector_store'].get_document_count() == 0:
        st.warning("ベクトルストアにドキュメントがありません。まずPDFを処理してください。")
        return

    question = st.text_input("ドキュメントに関する質問を入力してください:", placeholder="この文書の主な目的は何ですか？")
    
    if question:
        with st.spinner("回答を生成中..."):
            try:
                result = components['qa_interface'].get_answer(question)
                st.write("### 回答")
                st.markdown(result["answer"])
                
                if result["sources"]:
                    with st.expander("参照元ドキュメント"):
                        for source in result["sources"]:
                            st.info(f"**ファイル:** {source.get('source', '不明')}, **ページ:** {source.get('page', '不明')}")
                            st.caption(f"> {source.get('text', '')[:200]}...")
            except Exception as e:
                logger.error(f"回答生成中にエラー: {e}")
                st.error("回答の生成中にエラーが発生しました。")
                st.exception(e)

def show_feedback_page(components):
    """フィードバックページの表示"""
    st.header("📝 フィードバック")
    
    with st.form("feedback_form"):
        feedback_type = st.selectbox("フィードバックの種類", ["回答の質", "UI/UX", "バグ報告", "その他"])
        feedback_text = st.text_area("フィードバック内容を自由にご記入ください。")
        submitted = st.form_submit_button("フィードバックを送信")
        
        if submitted and feedback_text:
            try:
                components['notion_client'].save_feedback({
                    "type": feedback_type,
                    "text": feedback_text,
                    "timestamp": datetime.now().isoformat()
                })
                st.success("貴重なフィードバックをありがとうございました！")
            except Exception as e:
                logger.error(f"フィードバックの送信に失敗しました: {e}")
                st.error("フィードバックの送信中にエラーが発生しました。")

def display_pdf(pdf_path: Path) -> str:
    """PDFをbase64エンコードして表示用URLを生成"""
    try:
        with open(pdf_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        return f"data:application/pdf;base64,{base64_pdf}"
    except Exception as e:
        logger.error(f"PDF表示エラー: {e}")
        return ""

def get_pdf_page_count(pdf_path: Path) -> int:
    """PDFのページ数を取得"""
    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()
        return page_count
    except Exception as e:
        logger.error(f"ページ数取得エラー: {e}")
        return 0

def get_pdf_page_as_image(pdf_path: Path, page_num: int) -> str:
    """指定したページを画像として取得し、base64エンコードして返す"""
    try:
        doc = fitz.open(pdf_path)
        if page_num < 1 or page_num > len(doc):
            return ""
        
        page = doc.load_page(page_num - 1)  # 0-indexed
        # 高解像度で画像に変換
        mat = fitz.Matrix(2.0, 2.0)  # 2倍スケール
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        doc.close()
        
        # base64エンコード
        import base64
        base64_img = base64.b64encode(img_data).decode('utf-8')
        return f"data:image/png;base64,{base64_img}"
    except Exception as e:
        logger.error(f"ページ画像取得エラー: {e}")
        return ""

def get_all_pdf_pages_as_images(pdf_path: Path) -> Dict[int, str]:
    """全ページを画像として取得"""
    try:
        doc = fitz.open(pdf_path)
        page_images = {}
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            import base64
            base64_img = base64.b64encode(img_data).decode('utf-8')
            page_images[page_num + 1] = f"data:image/png;base64,{base64_img}"
        
        doc.close()
        return page_images
    except Exception as e:
        logger.error(f"全ページ画像取得エラー: {e}")
        return {}

def display_page_comparison(page_images: Dict[int, str], easy_pages: Dict, paddle_pages: Dict, 
                           selected_page: int, comparison_mode: str = "both"):
    """ページごとの比較表示"""
    
    max_page = max(page_images.keys()) if page_images else 1
    
    # セッション状態の初期化
    session_key = f'selected_page_{comparison_mode}'
    if session_key not in st.session_state:
        st.session_state[session_key] = 1
    
    # 現在のページ番号を取得
    current_page = st.session_state[session_key]
    
    # ページが範囲外の場合は調整
    if current_page < 1:
        current_page = 1
        st.session_state[session_key] = 1
    elif current_page > max_page:
        current_page = max_page
        st.session_state[session_key] = max_page
    
    st.subheader(f"📄 ページ {current_page} の詳細比較")
    
    # ページナビゲーション - コールバック関数を使用
    def go_to_first():
        st.session_state[session_key] = 1
    
    def go_to_prev():
        st.session_state[session_key] = max(1, current_page - 1)
    
    def go_to_next():
        st.session_state[session_key] = min(max_page, current_page + 1)
    
    def go_to_last():
        st.session_state[session_key] = max_page
    
    # ナビゲーションボタン
    nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns([1, 1, 2, 1, 1])
    
    with nav_col1:
        st.button(
            "⏮️ 最初", 
            disabled=current_page <= 1, 
            key=f"nav_first_{comparison_mode}",
            on_click=go_to_first
        )
    
    with nav_col2:
        st.button(
            "⬅️ 前", 
            disabled=current_page <= 1, 
            key=f"nav_prev_{comparison_mode}",
            on_click=go_to_prev
        )
    
    with nav_col3:
        st.markdown(f"<div style='text-align: center; padding: 8px;'><strong>ページ {current_page} / {max_page}</strong></div>", 
                   unsafe_allow_html=True)
    
    with nav_col4:
        st.button(
            "➡️ 次", 
            disabled=current_page >= max_page, 
            key=f"nav_next_{comparison_mode}",
            on_click=go_to_next
        )
    
    with nav_col5:
        st.button(
            "⏭️ 最後", 
            disabled=current_page >= max_page, 
            key=f"nav_last_{comparison_mode}",
            on_click=go_to_last
        )
    
    # ページ選択スライダー
    slider_col1, slider_col2 = st.columns([3, 1])
    
    with slider_col1:
        # スライダーのコールバック関数
        def update_page_from_slider():
            st.session_state[session_key] = st.session_state[f"page_slider_{comparison_mode}"]
        
        slider_key = f"page_slider_{comparison_mode}"
        st.slider(
            "ページを選択", 
            1, max_page, current_page, 
            key=slider_key,
            help="スライダーを動かしてページを選択",
            on_change=update_page_from_slider
        )
    
    with slider_col2:
        # 現在のページを強制的に再読み込み
        if st.button("🔄 更新", key=f"refresh_{comparison_mode}", help="現在のページを再読み込み"):
            pass  # 何もしない、自然に再描画される
    
    # 直接ページ番号入力
    with st.expander("📝 ページ番号を直接入力"):
        input_col1, input_col2 = st.columns([2, 1])
        
        with input_col1:
            direct_page_key = f"direct_page_{comparison_mode}"
            direct_page = st.number_input(
                "ページ番号", 
                min_value=1, 
                max_value=max_page, 
                value=current_page,
                key=direct_page_key,
                help=f"1から{max_page}までのページ番号を入力"
            )
        
        with input_col2:
            def go_to_direct_page():
                st.session_state[session_key] = st.session_state[direct_page_key]
            
            st.button(
                "移動", 
                key=f"goto_page_{comparison_mode}",
                on_click=go_to_direct_page
            )
    
    # 表示モード選択
    display_mode = st.radio(
        "表示モード", 
        ["PDF画像とOCR結果", "OCR結果のみ比較", "PDF画像のみ"], 
        horizontal=True,
        key=f"display_mode_{comparison_mode}",
        help="表示したい内容を選択してください"
    )
    
    # 区切り線
    st.markdown("---")
    
    # 現在のページでコンテンツを表示
    if display_mode == "PDF画像とOCR結果":
        if comparison_mode == "both":
            # 3列レイアウト: PDF | EasyOCR | PaddleOCR
            pdf_col, easy_col, paddle_col = st.columns([1, 1, 1])
            
            with pdf_col:
                st.markdown("**📄 元のPDF**")
                if current_page in page_images:
                    st.markdown(
                        f'<img src="{page_images[current_page]}" style="width: 100%; border: 1px solid #ddd; border-radius: 4px;">', 
                        unsafe_allow_html=True
                    )
                else:
                    st.error(f"ページ {current_page} の画像が見つかりません")
            
            with easy_col:
                st.markdown("**📝 EasyOCR結果**")
                easy_text = easy_pages.get(current_page, "このページは処理されませんでした")
                st.text_area(
                    "EasyOCR", 
                    easy_text, 
                    height=400, 
                    key=f"easy_page_detail_{current_page}_{comparison_mode}",
                    help="EasyOCRで認識されたテキスト"
                )
                st.info(f"文字数: {len(easy_text)}")
            
            with paddle_col:
                st.markdown("**📝 PaddleOCR結果**")
                paddle_text = paddle_pages.get(current_page, "このページは処理されませんでした")
                st.text_area(
                    "PaddleOCR", 
                    paddle_text, 
                    height=400, 
                    key=f"paddle_page_detail_{current_page}_{comparison_mode}",
                    help="PaddleOCRで認識されたテキスト"
                )
                st.info(f"文字数: {len(paddle_text)}")
        
        else:
            # 2列レイアウト: PDF | OCR結果
            pdf_col, ocr_col = st.columns([1, 1])
            
            with pdf_col:
                st.markdown("**📄 元のPDF**")
                if current_page in page_images:
                    st.markdown(
                        f'<img src="{page_images[current_page]}" style="width: 100%; border: 1px solid #ddd; border-radius: 4px;">', 
                        unsafe_allow_html=True
                    )
                else:
                    st.error(f"ページ {current_page} の画像が見つかりません")
            
            with ocr_col:
                if comparison_mode == "easy":
                    st.markdown("**📝 EasyOCR結果**")
                    ocr_text = easy_pages.get(current_page, "このページは処理されませんでした")
                    engine_name = "EasyOCR"
                elif comparison_mode == "paddle":
                    st.markdown("**📝 PaddleOCR結果**")
                    ocr_text = paddle_pages.get(current_page, "このページは処理されませんでした")
                    engine_name = "PaddleOCR"
                
                st.text_area(
                    f"{engine_name}結果", 
                    ocr_text, 
                    height=400, 
                    key=f"{comparison_mode}_only_detail_{current_page}",
                    help=f"{engine_name}で認識されたテキスト"
                )
                st.info(f"文字数: {len(ocr_text)}")
    
    elif display_mode == "OCR結果のみ比較":
        if comparison_mode == "both":
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📝 EasyOCR結果**")
                easy_text = easy_pages.get(current_page, "このページは処理されませんでした")
                st.text_area(
                    "EasyOCR", 
                    easy_text, 
                    height=500, 
                    key=f"easy_ocr_only_{current_page}_{comparison_mode}",
                    help="EasyOCRで認識されたテキスト"
                )
                st.info(f"文字数: {len(easy_text)}")
            
            with col2:
                st.markdown("**📝 PaddleOCR結果**")
                paddle_text = paddle_pages.get(current_page, "このページは処理されませんでした")
                st.text_area(
                    "PaddleOCR", 
                    paddle_text, 
                    height=500, 
                    key=f"paddle_ocr_only_{current_page}_{comparison_mode}",
                    help="PaddleOCRで認識されたテキスト"
                )
                st.info(f"文字数: {len(paddle_text)}")
        else:
            if comparison_mode == "easy":
                st.markdown("**📝 EasyOCR結果**")
                ocr_text = easy_pages.get(current_page, "このページは処理されませんでした")
                engine_name = "EasyOCR"
            elif comparison_mode == "paddle":
                st.markdown("**📝 PaddleOCR結果**")
                ocr_text = paddle_pages.get(current_page, "このページは処理されませんでした")
                engine_name = "PaddleOCR"
            
            st.text_area(
                f"{engine_name}結果", 
                ocr_text, 
                height=500, 
                key=f"single_ocr_only_{current_page}_{comparison_mode}",
                help=f"{engine_name}で認識されたテキスト"
            )
            st.info(f"文字数: {len(ocr_text)}")
    
    elif display_mode == "PDF画像のみ":
        st.markdown("**📄 元のPDF**")
        if current_page in page_images:
            st.markdown(
                f'<div style="text-align: center; margin: 20px 0;"><img src="{page_images[current_page]}" style="max-width: 90%; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"></div>', 
                unsafe_allow_html=True
            )
        else:
            st.error(f"ページ {current_page} の画像が見つかりません")
    
    # ページ情報の表示
    st.markdown("---")
    
    info_col1, info_col2, info_col3 = st.columns(3)
    
    with info_col1:
        st.metric("現在のページ", f"{current_page}", delta=f"/ {max_page}")
    
    with info_col2:
        if comparison_mode == "both" or comparison_mode == "easy":
            easy_chars = len(easy_pages.get(current_page, ""))
            st.metric("EasyOCR文字数", easy_chars)
        elif comparison_mode == "paddle":
            paddle_chars = len(paddle_pages.get(current_page, ""))
            st.metric("PaddleOCR文字数", paddle_chars)
    
    with info_col3:
        if comparison_mode == "both":
            paddle_chars = len(paddle_pages.get(current_page, ""))
            st.metric("PaddleOCR文字数", paddle_chars)
        else:
            # 操作ヒント
            st.info("💡 ナビゲーションボタンでページ移動")
    
    # ページナビゲーションのヒント
    st.markdown("**📋 操作方法:**")
    hint_col1, hint_col2 = st.columns(2)
    with hint_col1:
        st.caption("• ナビゲーションボタン: ⏮️ ⬅️ ➡️ ⏭️")
        st.caption("• スライダー: ドラッグして移動")
    with hint_col2:
        st.caption("• 直接入力: エクスパンダーで数値指定")
        st.caption("• 表示モード: 3つのモードから選択")
    
    # デバッグ情報（問題解決用）
    if st.checkbox("🔧 デバッグ情報を表示", key=f"debug_{comparison_mode}"):
        st.write("**セッション状態:**")
        debug_col1, debug_col2 = st.columns(2)
        with debug_col1:
            st.write(f"- セッションキー: `{session_key}`")
            st.write(f"- 現在のページ: {current_page}")
            st.write(f"- 最大ページ: {max_page}")
            st.write(f"- 比較モード: {comparison_mode}")
        with debug_col2:
            st.write(f"- 利用可能なページ画像: {list(page_images.keys())}")
            st.write(f"- EasyOCRページ: {list(easy_pages.keys()) if easy_pages else '無し'}")
            st.write(f"- PaddleOCRページ: {list(paddle_pages.keys()) if paddle_pages else '無し'}")
            st.write(f"- セッション状態値: {st.session_state.get(session_key, '未設定')}")

def create_progress_container():
    """プログレス表示用のコンテナを作成"""
    progress_container = st.container()
    with progress_container:
        st.subheader("🔄 処理進捗")
        progress_bar = st.progress(0)
        status_text = st.empty()
        detailed_status = st.empty()
    
    return progress_container, progress_bar, status_text, detailed_status

def update_progress(progress_bar, status_text, detailed_status, 
                   progress: float, main_status: str, detail_status: str = ""):
    """プログレスバーとステータステキストを更新"""
    progress_bar.progress(progress)
    status_text.markdown(f"**{main_status}**")
    if detail_status:
        detailed_status.info(detail_status)

def main():
    """メインアプリケーション"""
    st.title("📄 DocuMind AI")
    st.markdown("PDFをアップロードし、内容について質問できるアプリケーションです。")

    components = initialize_components()
    if components is None:
        st.warning("アプリケーションのコンポーネントを初期化できませんでした。ログを確認してください。")
        st.stop()
    
    # サイドバーナビゲーション状態の保持
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "PDF処理"
    
    with st.sidebar:
        st.header("ナビゲーション")
        page_options = ["PDF処理", "質問応答", "フィードバック"]
        
        # ラジオボタンでページ選択（セッション状態を使用）
        def update_page():
            st.session_state.current_page = st.session_state.page_selector
        
        page = st.radio(
            "ページを選択", 
            page_options, 
            index=page_options.index(st.session_state.current_page),
            key="page_selector",
            on_change=update_page
        )
        
        # 現在選択されているページを取得
        page = st.session_state.current_page
    
    if page == "PDF処理":
        show_pdf_processing_page(components)
    elif page == "質問応答":
        show_qa_page(components)
    elif page == "フィードバック":
        show_feedback_page(components)


if __name__ == "__main__":
    main()
