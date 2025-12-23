import os
import yfinance as yf
import requests

# 1. 秘密のURL（GitHubから読み込む用）
WEBHOOK_URL = os.getenv("MY_DISCORD_URL")

# 2. 監視したい銘柄のリスト（好きなだけ増やせます！）
# 日本株は「コード.T」、米国株はそのまま（例: AAPL）書きます
WATCH_LIST = ["7203.T", "7974.T", "9984.T", "AAPL", "TSLA", "NVDA", "MSFT", "6857.T", "6701.T"]

def check_stock(symbol):
    """特定の1銘柄をチェックして、必要ならDiscordに送る関数"""
    stock = yf.Ticker(symbol)
    data = stock.history(period="2d")
    
    if len(data) < 2:
        return f"【{symbol}】データ取得失敗"

    latest_price = data['Close'].iloc[-1]
    old_price = data['Close'].iloc[-2]
    diff = ((latest_price - old_price) / old_price) * 100
    
    # メッセージの作成
    # 変化率がプラスなら「▲」、マイナスなら「▼」を表示する工夫
    mark = "▲" if diff > 0 else "▼"
    return f"【{symbol}】 {latest_price:,.1f}円 ({mark}{abs(diff):.2f}%)"

def main():
    if not WEBHOOK_URL:
        print("エラー: URLが設定されていません")
        return

    results = []
    # 3. リストの中身を1つずつループで処理
    for symbol in WATCH_LIST:
        print(f"{symbol} をチェック中...")
        result_text = check_stock(symbol)
        results.append(result_text) # 結果を溜める
    
    # 4. 全銘柄の結果を1つのメッセージにまとめて送信
    final_message = "📢 **本日の株価一斉チェック**\n" + "\n".join(results)
    
    payload = {"content": final_message}
    requests.post(WEBHOOK_URL, json=payload)
    print("一括送信が完了しました！")

if __name__ == "__main__":
    main()


