"""
MCP 天気予報サーバー - Hello World 的な実装例

このファイルは、Model Context Protocol (MCP) の基本的な使い方を理解するための
シンプルな天気予報サーバーの実装例です。

MCPとは:
- MCPは、AIアシスタント（Claude等）が外部のツールやリソースにアクセスするためのプロトコル
- サーバーは「ツール（Tools）」を提供し、AIがそれらを呼び出すことができる

この例では:
1. FastMCPクラスでMCPサーバーを初期化
2. @mcp.tool()デコレータでツールを定義
3. STDIO（標準入出力）経由でMCPクライアントと通信

参考: https://modelcontextprotocol.io/docs/develop/build-server#python
"""

from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# ============================================
# 1. FastMCPサーバーの初期化
# ============================================
# FastMCPクラスをインスタンス化します。
# 引数はサーバー名で、これはMCPクライアント（Claude Desktop等）で識別されます。
mcp = FastMCP("weather")

# ============================================
# 2. 定数の定義
# ============================================
# 天気予報APIのベースURLとユーザーエージェントを定義
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-mcp-app/1.0"


# ============================================
# 3. ヘルパー関数の定義
# ============================================
async def make_nws_request(url: str) -> dict[str, Any] | None:
    """
    National Weather Service APIにリクエストを送信するヘルパー関数
    
    Args:
        url: リクエスト先のURL
        
    Returns:
        APIレスポンスのJSONデータ、またはエラー時はNone
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    
    # httpxのAsyncClientを使用して非同期HTTPリクエストを実行
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()  # HTTPエラーがあれば例外を発生
            return response.json()
        except Exception:
            # エラー時はNoneを返す（呼び出し側でエラーハンドリング）
            return None


# ============================================
# 4. MCPツールの定義
# ============================================
# @mcp.tool()デコレータを使用すると、この関数がMCPツールとして登録されます。
# FastMCPは、関数の型ヒントとdocstringを自動的に読み取って、
# ツールの定義（パラメータ、説明など）を生成します。

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
    # ステップ1: 緯度・経度から「予報グリッドポイント」のURLを取得
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)
    
    if not points_data:
        return "天気予報データを取得できませんでした。"
    
    # ステップ2: 予報グリッドポイントのレスポンスから、実際の予報URLを取得
    forecast_url = points_data["properties"]["forecast"]
    
    # ステップ3: 実際の予報データを取得
    forecast_data = await make_nws_request(forecast_url)
    
    if not forecast_data:
        return "詳細な天気予報を取得できませんでした。"
    
    # ステップ4: 予報データをフォーマット
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    
    # 最初の5期間分の予報を表示
    for period in periods[:5]:
        forecast = f"""
{period['name']}:
気温: {period['temperature']}°{period['temperatureUnit']}
風: {period['windSpeed']} {period['windDirection']}
予報: {period['detailedForecast']}
"""
        forecasts.append(forecast)
    
    # 各予報を区切り線で結合して返す
    return "\n---\n".join(forecasts)


# ============================================
# 5. サーバーの起動
# ============================================
# mcp.run()を呼び出すと、MCPサーバーがSTDIO（標準入出力）経由で
# MCPクライアントからのメッセージを待ち受けます。
# 
# STDIOとは:
# - 標準入力（stdin）と標準出力（stdout）を使用した通信方式
# - MCPクライアントがこのPythonスクリプトを起動し、
#   標準入出力を通じてJSON-RPCメッセージを交換します
# 
# 注意: STDIOベースのサーバーでは、print()などのstdoutへの出力は
# JSON-RPCメッセージを壊すため使用できません。
# ログ出力にはloggingライブラリ（stderrに出力）を使用してください。

def main():
    """
    メイン関数: MCPサーバーを起動します
    """
    # STDIOトランスポートでサーバーを起動
    # これにより、MCPクライアント（Claude Desktop等）と通信可能になります
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()

