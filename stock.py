import os
import yfinance as yf
import requests

WEBHOOK_URL = os.getenv("MY_DISCORD_URL")
# 監視銘柄（AI関連 + 以前のもの）
WATCH_LIST = ["NVDA", "MSFT", "6857.T", "6701.T", "7974.T"]
ALERT_THRESHOLD = 0.1 # テスト用に低めに設定

def check_stock(symbol):
    stock = yf.Ticker(symbol)
    data = stock.history(period="2d")
    if len(data) < 2: return None

    latest_price = data['Close'].iloc[-1]
    old_price = data['Close'].iloc[-2]
    diff = ((latest_price - old_price) / old_price) * 100
    
    if abs(diff) < ALERT_THRESHOLD: return None

    # --- リッチ化ポイント：色の設定 ---
    # 16進数のカラーコードを整数に変換（緑: 3066993, 赤: 15158332）
    color = 3066993 if diff > 0 else 15158332
    mark = "🚀 急騰" if diff > 0 else "📉 急落"
    
    # --- リッチ化ポイント：Yahoo!ファイナンスへのリンク作成 ---
    # 日本株(末尾.T)と米国株でURLを分ける
    if ".T" in symbol:
        url = f"https://finance.yahoo.co.jp/quote/{symbol.replace('.T', '')}"
    else:
        url = f"https://finance.yahoo.com/quote/{symbol}"

    # Discordの「Embed」形式のデータを作成
    embed = {
        "title": f"{mark} {symbol}",
        "url": url,
        "color": color,
        "fields": [
            {"name": "現在値", "value": f"{latest_price:,.1f}円", "inline": True},
            {"name": "前日比", "value": f"{diff:+.2f}%", "inline": True}
        ],
        "footer": {"text": "Yahoo! Financeデータ"}
    }
    return embed

def main():
    if not WEBHOOK_URL: return

    embeds = []
    for symbol in WATCH_LIST:
        print(f"{symbol} をチェック中...")
        embed_data = check_stock(symbol)
        if embed_data:
            embeds.append(embed_data)
    
    if embeds:
        # Discordに「embeds」として送信
        payload = {
            "content": "⚠️ **株価急変アラート**",
            "embeds": embeds
        }
        requests.post(WEBHOOK_URL, json=payload)
        print("リッチな通知を送信しました！")

if __name__ == "__main__":
    main()
