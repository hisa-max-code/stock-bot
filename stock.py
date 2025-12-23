import os
import yfinance as yf
import requests

# 1. 秘密のURL
WEBHOOK_URL = os.getenv("MY_DISCORD_URL")

# 2. 監視銘柄リスト
WATCH_LIST = ["NVDA", "MSFT", "6857.T", "6701.T"]

# 3. 【ここが重要】通知する条件（％）
# 2.0に設定すると、±2%以上の変動があった時だけ通知します
ALERT_THRESHOLD = 2.0

def check_stock(symbol):
    stock = yf.Ticker(symbol)
    data = stock.history(period="2d")
    
    if len(data) < 2:
        return None

    latest_price = data['Close'].iloc[-1]
    old_price = data['Close'].iloc[-2]
    diff = ((latest_price - old_price) / old_price) * 100
    
    # 【判定】絶対値(abs)がしきい値より小さい場合は、何も返さない（無視する）
    if abs(diff) < ALERT_THRESHOLD:
        return None
    
    mark = "🚀 急騰" if diff > 0 else "📉 急落"
    return f"{mark} 【{symbol}】 {latest_price:,.1f}円 ({diff:+.2f}%)"

def main():
    if not WEBHOOK_URL:
        print("エラー: URLが設定されていません")
        return

    results = []
    for symbol in WATCH_LIST:
        print(f"{symbol} をチェック中...")
        result_text = check_stock(symbol)
        if result_text: # 値動きがあった場合だけリストに追加
            results.append(result_text)
    
    # 4. 大きく動いた銘柄がある場合のみDiscordに送る
    if results:
        final_message = "⚠️ **株価アラート（大幅な値動きを検知）**\n" + "\n".join(results)
        payload = {"content": final_message}
        requests.post(WEBHOOK_URL, json=payload)
        print(f"{len(results)} 件の急変を通知しました。")
    else:
        # 動いた銘柄がゼロなら、Discordには送らずログだけ残す
        print("大きな値動きはありませんでした。")

if __name__ == "__main__":
    main()
