# MCP動作の超詳細解説：「仙台の今の天気は？」から返答までの完全な流れ

このドキュメントでは、ユーザーが「仙台の今の天気は？」と質問してから、AIがMCPツールを使って天気予報を取得し、最終的にチャットで返答するまでの**すべてのステップ**を、初心者にも理解できるように詳しく説明します。

---

## 📋 目次

1. [全体像：何が起きているのか](#全体像)
2. [前提知識：MCPとは何か](#前提知識)
3. [ステップバイステップ：完全な動作フロー](#ステップバイステップ)
4. [技術的な詳細：各コンポーネントの役割](#技術的な詳細)
5. [実際のコード例：各ステップでのコード実行](#実際のコード例)

---

## 全体像 {#全体像}

```
ユーザー: 「仙台の今の天気は？」
    ↓
Claude Desktop (MCPクライアント)
    ↓
1. メッセージをClaude AIに送信
2. Claude AIが「天気予報ツールが必要」と判断
3. MCPプロトコルでweather_mcp.pyを呼び出し
4. weather_mcp.pyが天気APIからデータ取得
5. 結果をClaude AIに返す
6. Claude AIが自然な日本語で返答を生成
    ↓
ユーザー: 「仙台は現在、曇りで気温は15度です...」
```

---

## 前提知識：MCPとは何か {#前提知識}

### MCP（Model Context Protocol）とは？

**MCP**は、AIアシスタント（Claude等）が外部のツールやデータにアクセスするための**プロトコル（通信規約）**です。

### なぜMCPが必要なのか？

- AIは通常、**2024年4月までの知識**しか持っていません
- **リアルタイムの天気予報**や**最新のデータ**は取得できません
- しかし、MCPを使えば、AIが**外部のAPIやツールを呼び出せる**ようになります

### MCPの3つの主要コンポーネント

1. **MCPサーバー** (`weather_mcp.py`)
   - ツール（関数）を提供するプログラム
   - この例では「天気予報を取得する」ツールを提供

2. **MCPクライアント** (Claude Desktop)
   - サーバーとAIを仲介するプログラム
   - AIがツールを使いたい時に、サーバーを呼び出す

3. **AIモデル** (Claude)
   - ユーザーの質問を理解し、適切なツールを選択
   - ツールの結果を受け取って、自然な返答を生成

---

## ステップバイステップ：完全な動作フロー {#ステップバイステップ}

### 🔵 ステップ0：初期設定（サーバー起動前）

**何が起きているか：**
- `weather_mcp.py`が起動される準備をしています

**コードで何が起きているか：**

```python
# weather_mcp.py の冒頭部分

# 1. FastMCPサーバーを初期化
mcp = FastMCP("weather")
# → これは「weather」という名前のMCPサーバーを作成します
# → この時点ではまだツールは登録されていません

# 2. ツールを定義
@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """
    指定された緯度・経度の天気予報を取得します。
    
    この関数は、MCPクライアント（Claude等）から呼び出すことができます。
    AIが「サクラメントの天気は？」と聞くと、自動的にこのツールが呼ばれます。
    
    Args:
        latitude: 緯度（例: 38.5816）
        longitude: 経度（例: -121.4944）
        
    Returns:
        天気予報の文字列（フォーマット済み）
    """
    # ... 関数の実装
# → @mcp.tool()デコレータが関数を「ツール」として登録します
# → FastMCPが自動的に：
#    - パラメータ名（latitude, longitude）を検出
#    - 型（float）を検出
#    - docstring（三重クォートで囲まれた文字列）をdescriptionとして使用
#    - これらをJSON形式のツール定義に変換
```

**ツールのdescriptionはどこに書かれているか：**

ツールの説明（description）は、**関数のdocstring**（三重クォート `"""` で囲まれた文字列）に書かれています。

- **場所**: `weather_mcp.py`の76-88行目
- **形式**: 関数定義の直後に `"""` で始まる文字列
- **内容**: 
  - 最初の行がツールの説明として使用されます
  - `Args:` セクションでパラメータの説明
  - `Returns:` セクションで戻り値の説明

FastMCPは、このdocstringを自動的に読み取り、以下のようなJSON形式のツール定義に変換します：

```json
{
  "name": "get_forecast",
  "description": "指定された緯度・経度の天気予報を取得します。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "latitude": {
        "type": "number",
        "description": "緯度（例: 38.5816）"
      },
      "longitude": {
        "type": "number",
        "description": "経度（例: -121.4944）"
      }
    },
    "required": ["latitude", "longitude"]
  }
}
```

**重要なポイント：**
- docstringの**最初の行**がツールの主要な説明として使用されます
- `Args:` セクションの各パラメータの説明が、そのパラメータの説明として使用されます
- docstringを書かないと、descriptionが空になります（ツールは動作しますが、AIが理解しにくくなります）

**3. サーバーを起動**
```python
mcp.run(transport='stdio')
# → STDIO（標準入出力）でメッセージを待ち受けます
# → この時点で、サーバーは「リスニング状態」になります
```

**重要なポイント：**
- サーバーは**待機状態**に入ります
- STDIO（標準入力）からのJSON-RPCメッセージを待っています
- まだ何も処理していません

---

### 🔵 ステップ1：ユーザーが質問を入力

**ユーザーの行動：**
```
ユーザー: 「仙台の今の天気は？」
```

**何が起きているか：**
- Claude Desktopのチャット欄にメッセージが入力されます
- Claude Desktopがこのメッセージを**受信**します

**技術的な詳細：**
- まだMCPサーバーは呼び出されていません
- これは単純な「ユーザー入力の受信」です

---

### 🔵 ステップ2：Claude DesktopがメッセージをClaude AIに送信

**何が起きているか：**
- Claude Desktopがユーザーのメッセージを**Claude AI API**に送信します

**送信されるデータ：**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "仙台の今の天気は？"
    }
  ],
  "tools": [
    {
      "name": "get_forecast",
      "description": "指定された緯度・経度の天気予報を取得します。",
      "inputSchema": {
        "type": "object",
        "properties": {
          "latitude": {
            "type": "number",
            "description": "緯度（例: 38.5816）"
          },
          "longitude": {
            "type": "number",
            "description": "経度（例: -121.4944）"
          }
        },
        "required": ["latitude", "longitude"]
      }
    }
    // ... 他のMCPサーバーからのツールも含まれる
  ]
}
```

**重要なポイント：ツールリストは常に会話に含まれている**

- **ツールリストは会話の最初から含まれています**
  - Claude Desktopが起動時に、設定されているすべてのMCPサーバーからツールリストを取得
  - このツールリストは、**毎回のAPIリクエストに含まれます**
  - AIは常に利用可能なツールを「知っている」状態です

- **複数のMCPサーバーからのツール**
  - 複数のMCPサーバーが設定されている場合、すべてのツールが1つのリストにまとめられます
  - 例: `weather_mcp.py`の`get_forecast`と、別のMCPサーバーの`search_files`などが一緒に含まれます
  - AIは、どのツールがどのMCPサーバーから来たかを意識する必要はありません

- **ツールリストの更新タイミング**
  - MCPサーバーが起動した時: ツールリストが取得される
  - MCPサーバーが停止した時: そのツールがリストから削除される
  - 会話中に新しいMCPサーバーが追加された時: ツールリストが更新される

**Claude AIの処理：**
1. メッセージを受け取る
2. 意味を理解する：「仙台」「天気」「今」
3. **利用可能なツールリストを確認**
   - `tools`配列に含まれるすべてのツールとその説明を読み取る
   - 各ツールの`name`、`description`、`inputSchema`を理解する
4. **重要な判断：** 天気予報は**最新データが必要**だと認識
5. ツールリストの中から「天気予報を取得する」ツールを探す
6. `get_forecast`ツールを見つける

---

### 🔵 ステップ3：Claude AIがツールの必要性を判断

**Claude AIの思考プロセス（簡略化）：**

```
ユーザー: 「仙台の今の天気は？」

Claude AIの内部思考:
1. 「天気」というキーワードを検出
2. 「今の」= リアルタイムデータが必要
3. 私の知識には2024年4月までのデータしかない
4. → 最新の天気予報を取得するツールが必要
5. 利用可能なツールを確認...
6. 「get_forecast」というツールがある！
7. これは緯度・経度を受け取るツール
8. 「仙台」の緯度・経度が必要...
9. → 仙台の緯度・経度は 38.2682, 140.8694 だ（知識から）
10. → get_forecast(38.2682, 140.8694) を呼び出そう
```

**重要なポイント：**
- Claude AIは**自動的に**ツールが必要だと判断します
- ユーザーは「ツールを使って」と言う必要はありません
- AIが**文脈から判断**します

---

### 🔵 ステップ3.5：Claude AIがツール使用を表明する（重要：AIの「行動」）

**ここが最も重要な部分：AIはどのようにツールを使いたいと「伝える」のか**

Claude AIは、ツールを使いたい時、**通常のテキストレスポンスではなく、特別な形式のメッセージ**を返します。

**Claude AIからのレスポンス（実際の形式）：**

```json
{
  "id": "msg_abc123",
  "role": "assistant",
  "content": [
    {
      "type": "tool_use",
      "id": "toolu_xyz789",
      "name": "get_forecast",
      "input": {
        "latitude": 38.2682,
        "longitude": 140.8694
      }
    }
  ],
  "stop_reason": "tool_use"
}
```

**このメッセージの意味：**

1. **`role: "assistant"`**: これはAIからのメッセージです
2. **`content[0].type: "tool_use"`**: これは「ツールを使いたい」という表明です
   - 通常のテキストメッセージなら `type: "text"` になります
   - `type: "tool_use"` が含まれている = AIがツールを使いたい
3. **`content[0].name: "get_forecast"`**: 使用したいツールの名前
4. **`content[0].input`**: ツールに渡す引数（パラメータ）
   - `latitude: 38.2682` - 仙台の緯度
   - `longitude: 140.8694` - 仙台の経度
5. **`stop_reason: "tool_use"`**: AIは「ツールを使うために」レスポンスを停止しました
   - ツールの結果を待ってから、続きの返答を生成します

---

### 🔵 なぜAIはこの形式を知っているのか？（重要な仕組みの説明）

**よくある誤解：**
- 「AIが学習してこの形式を覚えた」と思われがちですが、**それは違います**

**実際の仕組み：**

1. **Claude APIの仕様として定義されている**
   - `tool_use`形式は、**Claude APIの公式仕様**として定義されています
   - これはAIモデルが学習したものではなく、**APIのプロトコル**です
   - 詳細は[Anthropic API Documentation](https://docs.anthropic.com/claude/reference/messages_post)で確認できます

2. **ツールリストが含まれると、ツール使用が可能になる**
   - Claude APIにリクエストを送る際、`tools`配列が含まれていると、AIはツールを使うことができます
   - `tools`配列が**ない**場合、AIはツールを使えません（通常のテキストチャットのみ）

3. **AIモデルの動作**
   - Claudeモデル自体は、API仕様に従って動作するように設計されています
   - ツールリストが提供されると、モデルは：
     - ツールの`description`を読んで、ツールの機能を理解する
     - ユーザーの質問に基づいて、適切なツールを選択する
     - API仕様に従って`tool_use`形式で返答する

**具体的な流れ：**

```
1. Claude DesktopがClaude APIにリクエストを送信
   ↓
   {
     "messages": [...],
     "tools": [
       {
         "name": "get_forecast",
         "description": "...",
         "inputSchema": {...}
       }
     ]
   }
   ↓
2. Claude APIがツールリストを受け取る
   ↓
3. Claudeモデルが以下を理解する：
   - 「tools配列がある = ツールが使える」
   - 「API仕様に従って、tool_use形式で返答できる」
   - 「ツールを使いたい時は、content配列にtool_useオブジェクトを含める」
   ↓
4. AIがツールを使いたいと判断
   ↓
5. API仕様に従って、tool_use形式で返答
   {
     "content": [{"type": "tool_use", ...}],
     "stop_reason": "tool_use"
   }
```

**重要なポイント：**

- **これは学習ではなく、API仕様**
  - AIが「覚えた」のではなく、Claude APIの仕様として決まっています
  - 他のLLM（GPT-4など）も同様に、それぞれのAPI仕様に従ってツールを呼び出します

- **ツールリストがない場合**
  - `tools`配列がリクエストに含まれていない場合、AIはツールを使えません
  - 通常のテキストチャットのみになります

- **ツールリストの形式も仕様**
  - ツールリストの形式（`name`、`description`、`inputSchema`など）も、Claude APIの仕様です
  - MCPは、この仕様に合わせてツール定義を変換します

**参考資料：**
- [Anthropic API Documentation - Tool Use](https://docs.anthropic.com/claude/reference/messages_post#tool-use)
- [Claude API - Tool Use Format](https://docs.anthropic.com/claude/docs/tool-use)

---

### 🔵 モデルごとの違い：Gemini、ChatGPT、Claudeでのツール使用の比較

**重要な質問：モデルごとにツールの使い方が違うのか？**

はい、**各モデルは異なるAPI仕様を持っています**。ただし、**概念は同じ**です：
- ツールリストを提供する
- AIがツールを選択する
- AIがツールを呼び出す
- 結果を受け取る

**各モデルの違い：**

#### 1. **Claude（Anthropic）**

**リクエスト形式：**
```json
{
  "model": "claude-3-5-sonnet-20241022",
  "messages": [
    {"role": "user", "content": "仙台の天気は？"}
  ],
  "tools": [
    {
      "name": "get_forecast",
      "description": "天気予報を取得します",
      "inputSchema": {
        "type": "object",
        "properties": {
          "latitude": {"type": "number"},
          "longitude": {"type": "number"}
        }
      }
    }
  ]
}
```

**ツール使用のレスポンス形式：**
```json
{
  "content": [
    {
      "type": "tool_use",
      "id": "toolu_xyz789",
      "name": "get_forecast",
      "input": {
        "latitude": 38.2682,
        "longitude": 140.8694
      }
    }
  ],
  "stop_reason": "tool_use"
}
```

**特徴：**
- `tools`配列でツールリストを提供
- `tool_use`形式でツール呼び出しを返す
- `stop_reason: "tool_use"`でツール使用を表明

---

#### 2. **ChatGPT（OpenAI GPT-4）**

**リクエスト形式：**
```json
{
  "model": "gpt-4",
  "messages": [
    {"role": "user", "content": "仙台の天気は？"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_forecast",
        "description": "天気予報を取得します",
        "parameters": {
          "type": "object",
          "properties": {
            "latitude": {"type": "number"},
            "longitude": {"type": "number"}
          },
          "required": ["latitude", "longitude"]
        }
      }
    }
  ]
}
```

**ツール使用のレスポンス形式：**
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "call_abc123",
          "type": "function",
          "function": {
            "name": "get_forecast",
            "arguments": "{\"latitude\": 38.2682, \"longitude\": 140.8694}"
          }
        }
      ]
    },
    "finish_reason": "tool_calls"
  }]
}
```

**特徴：**
- `tools`配列でツールリストを提供（`type: "function"`が必要）
- `tool_calls`配列でツール呼び出しを返す
- `finish_reason: "tool_calls"`でツール使用を表明
- `arguments`はJSON文字列形式

---

#### 3. **Gemini（Google）**

**リクエスト形式：**
```json
{
  "contents": [{
    "parts": [{
      "text": "仙台の天気は？"
    }]
  }],
  "tools": [{
    "functionDeclarations": [{
      "name": "get_forecast",
      "description": "天気予報を取得します",
      "parameters": {
        "type": "object",
        "properties": {
          "latitude": {"type": "number"},
          "longitude": {"type": "number"}
        },
        "required": ["latitude", "longitude"]
      }
    }]
  }]
}
```

**ツール使用のレスポンス形式：**
```json
{
  "candidates": [{
    "content": {
      "parts": [{
        "functionCall": {
          "name": "get_forecast",
          "args": {
            "latitude": 38.2682,
            "longitude": 140.8694
          }
        }
      }]
    },
    "finishReason": "FUNCTION_CALL"
  }]
}
```

**特徴：**
- `tools`配列でツールリストを提供（`functionDeclarations`を使用）
- `functionCall`オブジェクトでツール呼び出しを返す
- `finishReason: "FUNCTION_CALL"`でツール使用を表明
- `args`は直接オブジェクト形式

---

### 比較表

| 項目 | Claude | ChatGPT | Gemini |
|------|--------|---------|--------|
| **ツールリストの場所** | `tools`配列 | `tools`配列 | `tools[].functionDeclarations` |
| **ツール定義の構造** | `name`, `description`, `inputSchema` | `type: "function"`, `function.name`, `function.parameters` | `functionDeclarations[].name`, `functionDeclarations[].parameters` |
| **ツール呼び出しの形式** | `tool_use`オブジェクト | `tool_calls`配列 | `functionCall`オブジェクト |
| **停止理由** | `stop_reason: "tool_use"` | `finish_reason: "tool_calls"` | `finishReason: "FUNCTION_CALL"` |
| **引数の形式** | `input`オブジェクト | `arguments`（JSON文字列） | `args`オブジェクト |
| **ID管理** | `tool_use.id` | `tool_calls[].id` | なし（1ツールのみ） |

---

### 重要なポイント

1. **概念は同じ、形式が異なる**
   - すべてのモデルが「ツールリストを提供 → AIが選択 → ツール呼び出し」という流れ
   - しかし、API仕様（JSON構造）が異なる

2. **MCPの役割**
   - MCPは、これらの違いを抽象化します
   - MCPサーバーは標準的な形式でツールを提供
   - MCPクライアント（Claude Desktop等）が、各モデルのAPI仕様に合わせて変換します

3. **Claude Desktopでの処理**
   - Claude DesktopはClaude API専用なので、Claudeの形式しか使いません
   - もしGeminiやChatGPTでMCPを使う場合、それぞれのクライアントが適切な変換を行う必要があります

4. **開発者の視点**
   - MCPサーバーを作る時は、モデルに依存しない標準形式で作成
   - 各モデル用のクライアントが、適切な形式に変換してくれる

---

### 具体例：同じツールを異なるモデルで使う場合

**MCPサーバー側（共通）：**
```python
@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """天気予報を取得します"""
    # ... 実装
```

**Claude用の変換：**
```python
# MCPツール定義 → Claude形式
claude_tool = {
    "name": "get_forecast",
    "description": "天気予報を取得します",
    "inputSchema": {
        "type": "object",
        "properties": {
            "latitude": {"type": "number"},
            "longitude": {"type": "number"}
        }
    }
}
```

**ChatGPT用の変換：**
```python
# MCPツール定義 → ChatGPT形式
chatgpt_tool = {
    "type": "function",
    "function": {
        "name": "get_forecast",
        "description": "天気予報を取得します",
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"}
            },
            "required": ["latitude", "longitude"]
        }
    }
}
```

**Gemini用の変換：**
```python
# MCPツール定義 → Gemini形式
gemini_tool = {
    "functionDeclarations": [{
        "name": "get_forecast",
        "description": "天気予報を取得します",
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"}
            },
            "required": ["latitude", "longitude"]
        }
    }]
}
```

---

### まとめ

- **各モデルは異なるAPI仕様を持っている**
- **ツール使用の概念は同じだが、JSON構造が異なる**
- **MCPはこの違いを抽象化する役割**
- **MCPサーバーは標準形式で作成し、クライアントが各モデル用に変換する**

**AIが実際に行うこと：**

AIは以下のような「思考プロセス」を行います：

```
1. ユーザーの質問を分析
   → 「仙台の今の天気は？」= リアルタイムデータが必要

2. 利用可能なツールリストを確認
   → tools配列に含まれるすべてのツールを読む
   → "get_forecast" ツールを見つける
   → description: "指定された緯度・経度の天気予報を取得します。"
   → inputSchema: latitude (number), longitude (number) が必要

3. ツールを使用する決定
   → このツールが最適だと判断
   → パラメータを準備:
      - latitude: 仙台の緯度（知識から） = 38.2682
      - longitude: 仙台の経度（知識から） = 140.8694

4. ツール使用メッセージを生成
   → JSON形式で tool_use メッセージを作成
   → 通常のテキストではなく、tool_use を返す
   → stop_reason を "tool_use" に設定
```

**重要なポイント：**

- AIは**自動的に**ツール使用メッセージを生成します
- これは**AIの内部的な判断**です（ユーザーは何も指示していません）
- AIは**ツールリストを読んで**、適切なツールを選択します
- AIは**知識ベースから**緯度・経度などの情報を取得します

**視覚的な表現：**

```
Claude AIの内部処理:
┌─────────────────────────────────────┐
│ 1. ユーザーメッセージを分析          │
│    「仙台の今の天気は？」            │
│                                      │
│ 2. ツールリストを確認                │
│    [get_forecast, read_file, ...]   │
│                                      │
│ 3. 最適なツールを選択                │
│    → get_forecast が最適            │
│                                      │
│ 4. パラメータを準備                  │
│    latitude: 38.2682                 │
│    longitude: 140.8694                │
│                                      │
│ 5. tool_use メッセージを生成         │
│    ↓                                 │
│    {                                 │
│      "type": "tool_use",             │
│      "name": "get_forecast",         │
│      "input": {                      │
│        "latitude": 38.2682,          │
│        "longitude": 140.8694         │
│      }                               │
│    }                                 │
└─────────────────────────────────────┘
```

---

### 🔵 ステップ3.6：Claude Desktopがツール使用メッセージを受信して解釈

**何が起きているか：**

Claude Desktopが、Claude AIからの`tool_use`メッセージを受け取ります。

**Claude Desktop内部の処理（概念的なコード）：**

```python
# Claude Desktop内部のコード（概念的なもの）

# Claude AIからのレスポンスを受信
ai_response = {
    "role": "assistant",
    "content": [
        {
            "type": "tool_use",
            "id": "toolu_xyz789",
            "name": "get_forecast",
            "input": {
                "latitude": 38.2682,
                "longitude": 140.8694
            }
        }
    ],
    "stop_reason": "tool_use"
}

# tool_useメッセージを検出
if ai_response["stop_reason"] == "tool_use":
    # content配列から tool_use オブジェクトを取得
    for item in ai_response["content"]:
        if item["type"] == "tool_use":
            tool_name = item["name"]  # "get_forecast"
            tool_input = item["input"]  # {"latitude": 38.2682, "longitude": 140.8694}
            tool_use_id = item["id"]  # "toolu_xyz789"（後で結果と対応付けるため）
            
            # このツールがどのMCPサーバーから来たかを特定
            # （Claude Desktopは内部的にツール名とMCPサーバーのマッピングを持っている）
            mcp_server = find_mcp_server_for_tool(tool_name)
            # → "weather_mcp.py" のプロセスを見つける
            
            # MCPサーバーにツール呼び出しをリクエスト（次のステップ4へ）
            call_mcp_tool(mcp_server, tool_name, tool_input, tool_use_id)
```

**重要なポイント：**

- Claude Desktopは`tool_use`メッセージを**自動的に検出**します
- `stop_reason: "tool_use"`を見て、「ツールの結果を待つ必要がある」と判断します
- ツール名（`get_forecast`）から、どのMCPサーバーにリクエストを送るかを決定します
- `tool_use_id`は、後でツールの結果と対応付けるために使用されます

---

### 🔵 ステップ4：MCPクライアントがツール呼び出しリクエストを送信

**何が起きているか：**
- Claude Desktop（MCPクライアント）が、AIの`tool_use`メッセージに基づいて**MCPサーバー**にツール呼び出しをリクエストします

**変換プロセス：AIのtool_use → MCPのtools/call**

Claude Desktopは、Claude AIの`tool_use`メッセージを、MCPプロトコルの`tools/call`メッセージに変換します：

**変換前（Claude AI形式）：**
```json
{
  "type": "tool_use",
  "id": "toolu_xyz789",
  "name": "get_forecast",
  "input": {
    "latitude": 38.2682,
    "longitude": 140.8694
  }
}
```

**変換後（MCP JSON-RPC形式）：**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_forecast",
    "arguments": {
      "latitude": 38.2682,
      "longitude": 140.8694
    }
  }
}
```

**変換処理の詳細（Claude Desktop内部）：**

```python
# Claude Desktop内部のコード（概念的なもの）

def convert_tool_use_to_mcp_request(tool_use_message, request_id):
    """
    Claude AIのtool_useメッセージをMCPのtools/callリクエストに変換
    """
    return {
        "jsonrpc": "2.0",
        "id": request_id,  # MCPリクエスト用のID
        "method": "tools/call",
        "params": {
            "name": tool_use_message["name"],  # "get_forecast"
            "arguments": tool_use_message["input"]  # {"latitude": 38.2682, "longitude": 140.8694}
        }
    }

# 実際の変換処理
tool_use = ai_response["content"][0]  # tool_useメッセージ
mcp_request = convert_tool_use_to_mcp_request(tool_use, request_id=1)

# MCPサーバーのプロセスに送信
weather_process.stdin.write(json.dumps(mcp_request) + "\n")
weather_process.stdin.flush()
```

**このメッセージの意味：**
- `jsonrpc: "2.0"`: JSON-RPCプロトコルのバージョン
- `id: 1`: リクエストのID（後でレスポンスと対応付けます）
- `method: "tools/call"`: 「ツールを呼び出す」というメソッド
- `params.name: "get_forecast"`: 呼び出すツールの名前（AIの`tool_use.name`から）
- `params.arguments`: ツールに渡す引数（AIの`tool_use.input`から）

**メッセージの送信方法：**
- STDIO（標準入力）を通じて送信されます
- `weather_mcp.py`の`mcp.run(transport='stdio')`がこのメッセージを受信します

**重要なポイント：**

1. **AIのtool_useメッセージが起点**
   - AIが`tool_use`メッセージを返すことで、ツール呼び出しが開始されます
   - これはAIの**能動的な判断**です

2. **自動的な変換**
   - Claude Desktopが自動的に`tool_use`を`tools/call`に変換します
   - 開発者やユーザーは何もする必要がありません

3. **プロトコルの違い**
   - Claude API: `tool_use`形式（AI用）
   - MCP: `tools/call`形式（MCPサーバー用）
   - Claude Desktopが両者の橋渡しをします

---

### 🔵 ステップ5：MCPサーバーがリクエストを受信して処理開始

**何が起きているか：**
- `weather_mcp.py`のFastMCPライブラリがJSON-RPCメッセージを受信します
- メッセージを解析して、`get_forecast`ツールを呼び出すことを理解します

**コードの実行フロー：**

```python
# FastMCPライブラリ内部（簡略化）

# 1. STDIOからJSON-RPCメッセージを受信
message = read_from_stdin()
# → ステップ4で送信されたJSONメッセージが入ります

# 2. メッセージを解析
if message["method"] == "tools/call":
    tool_name = message["params"]["name"]  # "get_forecast"
    arguments = message["params"]["arguments"]  # {"latitude": 38.2682, "longitude": 140.8694}
    
    # 3. 登録されているツールを検索
    tool_function = find_tool(tool_name)  # get_forecast関数を見つける
    
    # 4. ツール関数を呼び出し
    result = await tool_function(**arguments)
    # → get_forecast(latitude=38.2682, longitude=140.8694) が実行されます
```

**重要なポイント：**
- FastMCPライブラリが**自動的に**メッセージを解析します
- ツール関数を**自動的に**呼び出します
- 開発者は`@mcp.tool()`デコレータだけで登録すればOKです

---

### 🔵 ステップ6：get_forecast関数が実行される

**コードの実行：**

```python
@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    # 引数が渡される：
    # latitude = 38.2682  (仙台の緯度)
    # longitude = 140.8694  (仙台の経度)
    
    # ステップ6-1: 予報グリッドポイントのURLを構築
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    # → "https://api.weather.gov/points/38.2682,140.8694"
    
    # ステップ6-2: APIにリクエストを送信
    points_data = await make_nws_request(points_url)
    # → HTTP GETリクエストが送信されます
    # → レスポンス例:
    # {
    #   "properties": {
    #     "forecast": "https://api.weather.gov/gridpoints/.../forecast"
    #   }
    # }
    
    # ステップ6-3: 予報URLを取得
    forecast_url = points_data["properties"]["forecast"]
    # → "https://api.weather.gov/gridpoints/REH/33,34/forecast"
    
    # ステップ6-4: 実際の予報データを取得
    forecast_data = await make_nws_request(forecast_url)
    # → 天気予報の詳細データが取得されます
    # → レスポンス例:
    # {
    #   "properties": {
    #     "periods": [
    #       {
    #         "name": "今日",
    #         "temperature": 15,
    #         "temperatureUnit": "C",
    #         "windSpeed": "10 km/h",
    #         "windDirection": "北",
    #         "detailedForecast": "曇り。最高気温15度..."
    #       },
    #       ...
    #     ]
    #   }
    # }
    
    # ステップ6-5: データをフォーマット
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    
    for period in periods[:5]:  # 最初の5期間
        forecast = f"""
{period['name']}:
気温: {period['temperature']}°{period['temperatureUnit']}
風: {period['windSpeed']} {period['windDirection']}
予報: {period['detailedForecast']}
"""
        forecasts.append(forecast)
    
    # ステップ6-6: 結果を返す
    return "\n---\n".join(forecasts)
    # → フォーマットされた文字列が返されます
    # → 例:
    # """
    # 今日:
    # 気温: 15°C
    # 風: 10 km/h 北
    # 予報: 曇り。最高気温15度...
    # ---
    # 今夜:
    # ...
    # """
```

**重要なポイント：**
- この関数は**非同期（async）**です
- `await`キーワードでHTTPリクエストを待ちます
- 2回のAPI呼び出しを行います（ポイント取得 → 予報取得）

---

### 🔵 ステップ7：MCPサーバーが結果をJSON-RPCレスポンスとして返す

**何が起きているか：**
- `get_forecast`関数の戻り値が、JSON-RPCレスポンスに変換されます

**送信されるJSON-RPCメッセージ：**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "\n今日:\n気温: 15°C\n風: 10 km/h 北\n予報: 曇り。最高気温15度...\n---\n今夜:\n..."
      }
    ]
  }
}
```

**このメッセージの意味：**
- `id: 1`: ステップ4のリクエストIDと同じ（対応付け）
- `result`: ツールの実行結果
- `result.content[0].text`: ツールが返した文字列

**メッセージの送信方法：**
- STDIO（標準出力）を通じて送信されます
- Claude Desktopがこのメッセージを受信します

---

### 🔵 ステップ8：Claude Desktopが結果をClaude AIに渡す

**何が起きているか：**
- Claude DesktopがMCPサーバーからのレスポンスを受け取ります
- この結果を**Claude AI**に渡します

**変換プロセス：MCPのresult → Claude AIのtool_result**

Claude Desktopは、MCPサーバーからの結果を、Claude AIが理解できる`tool_result`形式に変換します：

**変換前（MCP JSON-RPC形式）：**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "\n今日:\n気温: 15°C\n風: 10 km/h 北\n予報: 曇り。最高気温15度...\n---\n..."
      }
    ]
  }
}
```

**変換後（Claude AI形式）：**
```json
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_xyz789",
      "content": "\n今日:\n気温: 15°C\n風: 10 km/h 北\n予報: 曇り。最高気温15度...\n---\n..."
    }
  ]
}
```

**変換処理の詳細（Claude Desktop内部）：**

```python
# Claude Desktop内部のコード（概念的なもの）

def convert_mcp_result_to_tool_result(mcp_response, tool_use_id):
    """
    MCPサーバーからの結果をClaude AIのtool_result形式に変換
    """
    # MCPレスポンスからテキストを抽出
    text_content = mcp_response["result"]["content"][0]["text"]
    
    return {
        "role": "user",  # tool_resultはuserロールとして送信される
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_use_id,  # 元のtool_useメッセージのID
                "content": text_content  # ツールの実行結果
            }
        ]
    }

# 実際の変換処理
mcp_response = json.loads(weather_process.stdout.readline())
tool_result = convert_mcp_result_to_tool_result(
    mcp_response, 
    tool_use_id="toolu_xyz789"  # ステップ3.5で保存したID
)

# 会話履歴に追加してClaude AIに送信
conversation_history.append({
    "role": "user",
    "content": "仙台の今の天気は？"
})
conversation_history.append({
    "role": "assistant",
    "content": [
        {
            "type": "tool_use",
            "id": "toolu_xyz789",
            "name": "get_forecast",
            "input": {"latitude": 38.2682, "longitude": 140.8694}
        }
    ]
})
conversation_history.append(tool_result)  # ツールの結果を追加

# Claude AIに送信（続きの返答を生成してもらう）
next_response = claude_api.generate(conversation_history)
```

**Claude AIに送信される完全なデータ：**

```json
{
  "messages": [
    {
      "role": "user",
      "content": "仙台の今の天気は？"
    },
    {
      "role": "assistant",
      "content": [
        {
          "type": "tool_use",
          "id": "toolu_xyz789",
          "name": "get_forecast",
          "input": {
            "latitude": 38.2682,
            "longitude": 140.8694
          }
        }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "tool_result",
          "tool_use_id": "toolu_xyz789",
          "content": "\n今日:\n気温: 15°C\n風: 10 km/h 北\n予報: 曇り。最高気温15度...\n---\n..."
        }
      ]
    }
  ]
}
```

**このデータの意味：**
- **会話の履歴**が含まれています：
  1. ユーザーの質問
  2. AIがツールを使った記録（`tool_use`）
  3. ツールの結果（`tool_result`）
- **`tool_use_id`の対応付け**：
  - `tool_result.tool_use_id`が`tool_use.id`と一致することで、どのツール呼び出しの結果かを識別します
- **`role: "user"`の理由**：
  - `tool_result`は`user`ロールとして送信されます
  - これは「ツールの結果という新しい情報がユーザーから提供された」という意味です
  - AIは、この情報を使って続きの返答を生成します

**重要なポイント：**

1. **会話履歴の管理**
   - Claude Desktopは会話の全履歴を保持しています
   - ツール呼び出しと結果の両方が履歴に含まれます

2. **IDによる対応付け**
   - `tool_use_id`を使って、ツール呼び出しと結果を対応付けます
   - 複数のツールを同時に呼び出す場合でも、正しく対応付けられます

3. **AIへの再送信**
   - ツールの結果を含む会話履歴を、Claude AIに再送信します
   - AIは「ツールの結果を見た上で」続きの返答を生成します

---

### 🔵 ステップ9：Claude AIが結果を理解して自然な返答を生成

**Claude AIの処理：**

```
受け取ったデータ:
- ユーザーの質問: 「仙台の今の天気は？」
- ツールの結果: 「今日: 気温15°C、風10 km/h 北、予報: 曇り...」

Claude AIの思考プロセス:
1. ツールの結果を読み取る
2. 「今日」「気温15°C」「曇り」などの情報を抽出
3. ユーザーが聞いたのは「今の天気」
4. → 「今日」の情報が「今の天気」に該当
5. 自然な日本語で返答を生成

生成される返答:
「仙台の現在の天気は曇りで、気温は15度です。
風は北向きに10 km/h吹いています。
今日は一日中曇りがちで、最高気温は15度の見込みです。」
```

**重要なポイント：**
- Claude AIは**生のデータ**を受け取ります
- それを**自然な日本語**に変換します
- ユーザーは生データではなく、**理解しやすい返答**を受け取ります

---

### 🔵 ステップ10：ユーザーに返答が表示される

**最終的な結果：**

```
ユーザー: 「仙台の今の天気は？」

Claude: 「仙台の現在の天気は曇りで、気温は15度です。
        風は北向きに10 km/h吹いています。
        今日は一日中曇りがちで、最高気温は15度の見込みです。」
```

**何が起きているか：**
- Claude DesktopがClaude AIの返答を受信
- チャット欄に表示
- ユーザーが結果を確認

---

## 技術的な詳細：各コンポーネントの役割 {#技術的な詳細}

### 1. JSON-RPCプロトコル

**JSON-RPCとは：**
- リモートプロシージャコール（RPC）のためのプロトコル
- JSON形式でメッセージを交換します

**なぜJSON-RPCを使うのか：**
- **標準化**: どの言語でも同じ形式で通信できます
- **シンプル**: HTTPより軽量で、STDIOでも使えます
- **型安全**: リクエストとレスポンスの構造が明確です

### 2. STDIO（標準入出力）通信

**STDIOとは：**
- **標準入力（stdin）**: プログラムに入力データを送る
- **標準出力（stdout）**: プログラムから出力データを受け取る
- **標準エラー出力（stderr）**: エラーメッセージ用

**なぜSTDIOを使うのか：**
- **シンプル**: ネットワーク設定が不要
- **セキュア**: ローカルマシン内での通信
- **軽量**: HTTPサーバーを起動する必要がない

**実際の動作：**
```
Claude Desktop
    ↓ (stdinにJSON-RPCメッセージを書き込む)
weather_mcp.py
    ↓ (stdoutにJSON-RPCレスポンスを書き込む)
Claude Desktop
```

### 3. FastMCPライブラリの役割

**FastMCPが自動的に行うこと：**

1. **ツール定義の自動生成**
   ```python
   @mcp.tool()
   async def get_forecast(latitude: float, longitude: float) -> str:
       """
       指定された緯度・経度の天気予報を取得します。
       
       Args:
           latitude: 緯度（例: 38.5816）
           longitude: 経度（例: -121.4944）
       """
   ```
   → これを自動的に以下のようなJSONに変換：
   ```json
   {
     "name": "get_forecast",
     "description": "指定された緯度・経度の天気予報を取得します。",
     "inputSchema": {
       "type": "object",
       "properties": {
         "latitude": {
           "type": "number",
           "description": "緯度（例: 38.5816）"
         },
         "longitude": {
           "type": "number",
           "description": "経度（例: -121.4944）"
         }
       },
       "required": ["latitude", "longitude"]
     }
   }
   ```
   
   **descriptionの抽出方法：**
   - docstringの**最初の行**（空行まで）が`description`として使用されます
   - `Args:` セクションの各パラメータの説明が、`inputSchema.properties[パラメータ名].description`として使用されます
   - docstringがない場合、`description`は空文字列になります

2. **ツールリストの提供（MCPプロトコル）**
   - MCPクライアントが`tools/list`メソッドを呼び出すと、登録されているすべてのツールのリストを返します
   - このリストは、AIがツールを選択する際に使用されます

3. **JSON-RPCメッセージの処理**
   - 受信したJSON-RPCメッセージを解析
   - 適切なツール関数を呼び出し
   - 結果をJSON-RPCレスポンスに変換

4. **エラーハンドリング**
   - ツール実行中のエラーを捕捉
   - 適切なエラーレスポンスを返す

---

## ツールリストがAIに渡される仕組み {#ツールリストの仕組み}

### ツールリストの取得と管理

**ステップ0.5: MCPサーバー起動時のツールリスト取得**

MCPサーバーが起動すると、MCPクライアント（Claude Desktop）は以下の手順でツールリストを取得します：

1. **MCPサーバーへの接続**
   ```python
   # Claude Desktop内部（概念的なコード）
   
   # MCPサーバーを起動
   process = subprocess.Popen(["python", "weather_mcp.py"], ...)
   
   # ツールリストを取得するリクエストを送信
   request = {
       "jsonrpc": "2.0",
       "id": 1,
       "method": "tools/list"
   }
   process.stdin.write(json.dumps(request) + "\n")
   ```

2. **MCPサーバーからのレスポンス**
   ```json
   {
     "jsonrpc": "2.0",
     "id": 1,
     "result": {
       "tools": [
         {
           "name": "get_forecast",
           "description": "指定された緯度・経度の天気予報を取得します。",
           "inputSchema": {
             "type": "object",
             "properties": {
               "latitude": {"type": "number", "description": "緯度（例: 38.5816）"},
               "longitude": {"type": "number", "description": "経度（例: -121.4944）"}
             },
             "required": ["latitude", "longitude"]
           }
         }
       ]
     }
   }
   ```

3. **ツールリストの統合**
   - Claude Desktopは、すべてのMCPサーバーから取得したツールリストを1つにまとめます
   - 例: `weather_mcp.py`から`get_forecast`、`file_mcp.py`から`read_file`など

### AIへのツールリストの渡し方

**重要：ツールリストは常に会話に含まれている**

AI（Claude）に送信されるリクエストには、**必ず**利用可能なツールのリストが含まれています：

```json
{
  "messages": [
    {
      "role": "user",
      "content": "仙台の今の天気は？"
    }
  ],
  "tools": [
    {
      "name": "get_forecast",
      "description": "指定された緯度・経度の天気予報を取得します。",
      "inputSchema": {
        "type": "object",
        "properties": {
          "latitude": {"type": "number"},
          "longitude": {"type": "number"}
        },
        "required": ["latitude", "longitude"]
      }
    },
    {
      "name": "read_file",
      "description": "ファイルの内容を読み取ります。",
      "inputSchema": {
        "type": "object",
        "properties": {
          "path": {"type": "string", "description": "ファイルパス"}
        },
        "required": ["path"]
      }
    }
    // ... 他のMCPサーバーからのツールも含まれる
  ]
}
```

**なぜツールリストを常に含めるのか：**

1. **AIが適切なツールを選択できる**
   - AIは、ユーザーの質問を理解した後、利用可能なツールの中から最適なものを選択します
   - ツールリストがないと、AIはツールの存在を知らないため、使用できません

2. **複数のMCPサーバーからのツールを統合**
   - 複数のMCPサーバーが設定されている場合、すべてのツールが1つのリストにまとめられます
   - AIは、どのツールがどのMCPサーバーから来たかを意識する必要はありません

3. **ツールの説明（description）が重要**
   - AIは、各ツールの`description`を読んで、そのツールが何をするかを理解します
   - 良い`description`を書くことで、AIが適切にツールを選択できます

**ツールリストの更新タイミング：**

- **MCPサーバー起動時**: ツールリストが取得され、AIに渡される
- **MCPサーバー停止時**: そのツールがリストから削除される
- **会話中**: ツールリストは変更されません（会話が終了するまで同じリストが使用される）
- **新しい会話開始時**: 最新のツールリストが取得される

---

## 実際のコード例：各ステップでのコード実行 {#実際のコード例}

### ステップ0.5: ツールリストの取得

**MCPクライアント側（Claude Desktop内部、簡略化）：**

```python
# Claude Desktop内部のコード（概念的なもの）

import subprocess
import json

# すべてのMCPサーバーからツールリストを取得
all_tools = []

# weather_mcp.pyからツールリストを取得
weather_process = subprocess.Popen(["python", "weather_mcp.py"], ...)
weather_tools_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
}
weather_process.stdin.write(json.dumps(weather_tools_request) + "\n")
weather_response = json.loads(weather_process.stdout.readline())
all_tools.extend(weather_response["result"]["tools"])

# 他のMCPサーバーからも同様に取得...
# file_mcp.pyからツールリストを取得
# ...

# すべてのツールを1つのリストにまとめる
# このリストが、AIへのすべてのリクエストに含まれる
```

### ステップ4-5: MCPクライアント → MCPサーバー

**MCPクライアント側（Claude Desktop内部、簡略化）：**

```python
# Claude Desktop内部のコード（概念的なもの）

import subprocess
import json

# MCPサーバーを起動
process = subprocess.Popen(
    ["python", "weather_mcp.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# JSON-RPCリクエストを作成
request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "get_forecast",
        "arguments": {
            "latitude": 38.2682,
            "longitude": 140.8694
        }
    }
}

# リクエストを送信（stdinに書き込む）
process.stdin.write(json.dumps(request) + "\n")
process.stdin.flush()

# レスポンスを待つ（stdoutから読み取る）
response_line = process.stdout.readline()
response = json.loads(response_line)

# 結果を取得
result = response["result"]["content"][0]["text"]
```

**MCPサーバー側（weather_mcp.py）：**

```python
# FastMCPライブラリ内部（簡略化）

# STDIOから読み取る
request_line = sys.stdin.readline()
request = json.loads(request_line)

# ツールを呼び出す
if request["method"] == "tools/call":
    tool_name = request["params"]["name"]
    arguments = request["params"]["arguments"]
    
    # 登録されているツールを検索
    tool_func = registered_tools[tool_name]
    
    # 実行（非同期関数なのでawaitが必要）
    result = await tool_func(**arguments)
    
    # レスポンスを作成
    response = {
        "jsonrpc": "2.0",
        "id": request["id"],
        "result": {
            "content": [{"type": "text", "text": result}]
        }
    }
    
    # レスポンスを送信（stdoutに書き込む）
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()
```

---

## 🎯 まとめ：全体の流れを再確認

1. **ユーザー**: 「仙台の今の天気は？」と質問
2. **Claude Desktop**: メッセージをClaude AIに送信
3. **Claude AI**: 天気予報ツールが必要だと判断
4. **Claude Desktop**: MCPサーバーにツール呼び出しリクエストを送信（JSON-RPC）
5. **weather_mcp.py**: リクエストを受信し、`get_forecast`関数を実行
6. **get_forecast関数**: 天気APIからデータを取得し、フォーマット
7. **weather_mcp.py**: 結果をJSON-RPCレスポンスとして返す
8. **Claude Desktop**: 結果をClaude AIに渡す
9. **Claude AI**: 結果を理解し、自然な日本語で返答を生成
10. **ユーザー**: 理解しやすい返答を受け取る

---

## 📚 さらに学ぶために

- [MCP公式ドキュメント](https://modelcontextprotocol.io/docs/develop/build-server#python)
- [JSON-RPC仕様](https://www.jsonrpc.org/specification)
- [FastMCP GitHub](https://github.com/modelcontextprotocol/python-sdk)

---

**このドキュメントで理解できたこと：**
- MCPの全体像と動作フロー
- JSON-RPCプロトコルの役割
- STDIO通信の仕組み
- FastMCPライブラリの自動処理
- AIがツールを自動判断する仕組み
- **ツールのdescriptionはdocstringに書かれる**
- **ツールリストは常にAIに渡されている**
- **複数のMCPサーバーからのツールが統合される仕組み**

**次のステップ：**
- 独自のMCPツールを作成してみる
- 複数のツールを持つMCPサーバーを作成する
- エラーハンドリングを追加する
- 良いdescriptionを書く練習をする

