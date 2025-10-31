"""
Chkara Agent - MCP統合AIチャットサーバー

FastMCPツールをPython Webサーバー内に統合し、
Gemini APIでメッセージ判定と画像分析を行うAIチャットアプリケーション
"""

import os
import base64
import logging
from pathlib import Path
from typing import Any, Optional
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
import cv2
from mcp.server.fastmcp import FastMCP

# ロギング設定（stderrに出力 - MCPのベストプラクティス）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数の読み込み（明示的にパスを指定）
env_path = Path(__file__).parent / '.env'
logger.info(f".envファイルのパス: {env_path}")
logger.info(f".envファイルが存在するか: {env_path.exists()}")

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logger.info(".envファイルを読み込みました。")
else:
    logger.warning(".envファイルが見つかりません。環境変数から直接読み込みます。")
    load_dotenv()  # 環境変数からも試行

# Flaskアプリケーションの初期化
app = Flask(__name__)
CORS(app)  # 開発環境用のCORS設定

# Gemini APIの設定
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEYが設定されていません。.envファイルを確認してください。")
    logger.error("環境変数の確認: GEMINI_API_KEY={}".format('設定されていません' if not GEMINI_API_KEY else '***（設定済み）'))
else:
    # APIキーの最初と最後の数文字だけをログに表示（セキュリティ）
    masked_key = GEMINI_API_KEY[:4] + "..." + GEMINI_API_KEY[-4:] if len(GEMINI_API_KEY) > 8 else "***"
    logger.info(f"Gemini APIキーを検出しました: {masked_key}")
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Gemini APIが初期化されました。")

# Geminiモデルの初期化（gemini-2.5-proを使用）
try:
    model = genai.GenerativeModel('gemini-2.5-pro')
    logger.info("Geminiモデル 'gemini-2.5-pro' が初期化されました。")
except Exception as e:
    logger.error(f"Geminiモデルの初期化に失敗しました: {e}")
    logger.error("モデル名 'gemini-2.5-pro' が利用できない場合、'gemini-1.5-flash' または 'gemini-1.5-pro' を試してください。")
    model = None

# FastMCPインスタンスの作成
# FastMCPは通常STDIOで動作しますが、ここではツール定義のみを使用します
mcp = FastMCP("chkara-agent")

# MCPツール: カメラで写真を撮影
@mcp.tool()
def capture_camera() -> dict[str, Any]:
    """
    カメラで写真を撮影し、Base64エンコードされた画像データを返します。
    
    Returns:
        dict: {
            'success': bool,
            'image': str (Base64エンコードされたJPEG画像) | None,
            'error': str | None
        }
    """
    try:
        logger.info("カメラにアクセス中...")
        
        # カメラを開く（0はデフォルトのカメラ）
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            error_msg = "カメラを開けませんでした。カメラが接続されているか確認してください。"
            logger.error(error_msg)
            return {
                'success': False,
                'image': None,
                'error': error_msg
            }
        
        # カメラの設定（解像度など）
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # フレームを読み込む（少し待ってから撮影することで、カメラが安定する）
        ret, frame = cap.read()
        
        # カメラを解放
        cap.release()
        
        if not ret or frame is None:
            error_msg = "画像を取得できませんでした。"
            logger.error(error_msg)
            return {
                'success': False,
                'image': None,
                'error': error_msg
            }
        
        # 画像をJPEG形式でエンコード
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        # Base64エンコード
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        logger.info("カメラ撮影が成功しました。")
        return {
            'success': True,
            'image': img_base64,
            'error': None
        }
        
    except Exception as e:
        error_msg = f"カメラ撮影中にエラーが発生しました: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'image': None,
            'error': error_msg
        }


def should_capture_camera(user_message: str) -> bool:
    """
    ユーザーメッセージをGemini APIに送信し、
    カメラ撮影が必要かどうかを判定します。
    
    Args:
        user_message: ユーザーが入力したメッセージ
        
    Returns:
        bool: カメラ撮影が必要な場合True
    """
    if not model:
        logger.error("Geminiモデルが初期化されていません。")
        return False
    
    try:
        # 判定用のプロンプト
        prompt = f"""以下のユーザーメッセージを分析して、カメラで写真を撮影する必要があるかどうかを判定してください。

ユーザーメッセージ: "{user_message}"

カメラ撮影が必要な例:
- 写真を撮って
- 今の顔を見て
- 私の表情を確認して
- カメラで撮影して
- 今の様子を見て

カメラ撮影が不要な例:
- こんにちは
- 天気は？
- 時間を教えて
- 一般的な質問

回答は「YES」または「NO」のみでお願いします。"""

        logger.info("Gemini APIでメッセージ判定中...")
        response = model.generate_content(prompt)
        result = response.text.strip().upper()
        
        logger.info(f"判定結果: {result}")
        return result == "YES"
        
    except Exception as e:
        logger.error(f"メッセージ判定中にエラーが発生しました: {e}", exc_info=True)
        # エラー時は安全のためFalseを返す
        return False


def analyze_image_with_gemini(image_base64: str, user_message: str) -> str:
    """
    撮影した画像をGemini Vision APIに送信して分析します。
    
    Args:
        image_base64: Base64エンコードされた画像データ
        user_message: ユーザーの元のメッセージ
        
    Returns:
        str: AIの分析結果
    """
    if not model:
        return "エラー: Geminiモデルが初期化されていません。"
    
    try:
        # Base64デコード
        image_bytes = base64.b64decode(image_base64)
        
        # プロンプトを作成
        prompt = f"""この画像を分析してください。ユーザーは「{user_message}」と言っています。

画像に写っている人の顔の表情、服装、背景、全体的な様子などを詳しく分析して、日本語で自然な会話形式で説明してください。"""

        logger.info("Gemini Vision APIで画像分析中...")
        
        # 画像とテキストを組み合わせて送信
        response = model.generate_content([
            {
                'mime_type': 'image/jpeg',
                'data': image_bytes
            },
            prompt
        ])
        
        result = response.text
        logger.info("画像分析が完了しました。")
        return result
        
    except Exception as e:
        error_msg = f"画像分析中にエラーが発生しました: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@app.route('/')
def index():
    """フロントエンドのHTMLファイルを返す"""
    return send_from_directory('.', 'index.html')


@app.route('/chat', methods=['POST'])
def chat():
    """
    チャットメッセージを処理するエンドポイント
    
    1. ユーザーメッセージをGeminiで判定（カメラ撮影が必要か？）
    2. 必要ならMCPツールでカメラ撮影
    3. 撮影した画像をGemini Vision APIで分析
    4. 結果を返す
    """
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'メッセージが提供されていません。'}), 400
        
        user_message = data['message']
        logger.info(f"ユーザーメッセージを受信: {user_message}")
        
        # 1. メッセージを判定（カメラ撮影が必要か？）
        needs_camera = should_capture_camera(user_message)
        
        if needs_camera:
            logger.info("カメラ撮影が必要と判定されました。")
            
            # 2. MCPツールでカメラ撮影
            capture_result = capture_camera()
            
            if not capture_result['success']:
                # 撮影失敗時の応答
                return jsonify({
                    'reply': f"申し訳ございません。{capture_result['error']}",
                    'image': None
                })
            
            # 3. 撮影した画像をGemini Vision APIで分析
            image_base64 = capture_result['image']
            analysis = analyze_image_with_gemini(image_base64, user_message)
            
            # 4. 結果を返す（画像データも含める）
            return jsonify({
                'reply': analysis,
                'image': image_base64
            })
        else:
            # カメラ撮影が不要な場合、通常のテキストチャット
            logger.info("通常のテキストチャットとして処理します。")
            
            if not model:
                return jsonify({
                    'reply': 'エラー: Geminiモデルが初期化されていません。',
                    'image': None
                })
            
            try:
                response = model.generate_content(user_message)
                return jsonify({
                    'reply': response.text,
                    'image': None
                })
            except Exception as e:
                logger.error(f"テキストチャット処理中にエラー: {e}", exc_info=True)
                return jsonify({
                    'reply': f'エラーが発生しました: {str(e)}',
                    'image': None
                })
                
    except Exception as e:
        logger.error(f"チャット処理中にエラー: {e}", exc_info=True)
        return jsonify({
            'error': f'サーバーエラーが発生しました: {str(e)}'
        }), 500


if __name__ == '__main__':
    # サーバー起動前のチェック
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEYが設定されていません。.envファイルを確認してください。")
        exit(1)
    
    if not model:
        logger.error("Geminiモデルが初期化できませんでした。")
        exit(1)
    
    logger.info("=" * 50)
    logger.info("Chkara Agent サーバーを起動します...")
    logger.info("http://localhost:5000 でアクセスできます")
    logger.info("=" * 50)
    
    # 開発サーバーとして起動（本番環境では適切なWSGIサーバーを使用）
    app.run(host='0.0.0.0', port=5000, debug=True)

