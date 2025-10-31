# Chkara Agent - MCP統合AIチャット

Gemini APIを使用し、メッセージ内容を自動判定してカメラ撮影と画像分析を行うシンプルなAIチャットアプリケーションです。

## 機能

- AIチャット機能（Gemini API使用）
- メッセージ内容の自動判定（カメラ撮影が必要か自動判断）
- MCPツールによるカメラ撮影
- 撮影した画像のAI分析（顔の表情など）

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example` を `.env` にコピーし、Gemini APIキーを設定してください：

```bash
cp .env.example .env
```

`.env` ファイルを編集して、実際のAPIキーを設定：

```
GEMINI_API_KEY=your_actual_api_key_here
```

Gemini APIキーは [Google AI Studio](https://makersuite.google.com/app/apikey) で取得できます。

### 3. サーバーの起動

```bash
python server.py
```

### 4. ブラウザでアクセス

ブラウザで `http://localhost:5000` にアクセスしてチャットを開始してください。

## 使い方

1. チャット欄にメッセージを入力
2. 「写真を撮って」「今の顔を見て」など、カメラ撮影が必要なメッセージを送信
3. AIが自動でカメラ撮影を判断し、撮影を実行
4. 撮影した画像をAIが分析し、結果をチャット欄に表示

## アーキテクチャ

```
HTML/JS フロントエンド (index.html)
    ↓ HTTP POST /chat
Python Webサーバー (server.py)
    ├─ Gemini API (メッセージ判定: カメラ撮影が必要か？)
    ├─ FastMCPツール (capture_camera) - カメラ撮影
    └─ Gemini API (画像分析: 顔の表情など)
```

## MCPの動作理解ポイント

1. **FastMCPツール定義**: `@mcp.tool()` デコレータでツールを定義
2. **ツール呼び出し**: Webサーバー内から直接関数として呼び出し可能
3. **データフロー**: カメラ → OpenCV → Base64 → Gemini API → レスポンス

## 注意事項

- 初回実行時にカメラへのアクセス許可が求められる場合があります
- Windowsの場合、カメラのインデックスが0でない可能性があります（server.pyの`cv2.VideoCapture(0)`を調整してください）

