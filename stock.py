import os
import yfinance as yf
import requests

WEBHOOK_URL = os.getenv("MY_DISCORD_URL")
WATCH_LIST = ["NVDA", "MSFT", "6857.T", "6701.T", "7974.T"]
ALERT_THRESHOLD = 0.1 # テスト用

def check_stock(symbol):
    stock = yf.Ticker(symbol)
    data = stock.history(period="2d")
    if len(data) < 2: return None

    # 最新データと前日データの取得
    latest = data.iloc[-1]
    prev_close = data['Close'].iloc[-2]
    
    current_price = latest['Close']
    high_price = latest['High']
    low_price = latest['Low']
    volume = latest['Volume'] # 出来高（取引された株の数）
    
    diff = ((current_price - prev_close) / prev_close) * 100
    if abs(diff) < ALERT_THRESHOLD: return None

    color = 3066993 if diff > 0 else 15158332
    mark = "🚀 急騰" if diff > 0 else "📉 急落"
    
    # リンク作成
    url = f"https://finance.yahoo.co.jp/quote/{symbol.replace('.T', '')}" if ".T" in symbol else f"https://finance.yahoo.com/quote/{symbol}"

    # --- リッチ化ポイント：より詳細な情報の追加 ---
    embed = {
        "title": f"{mark} {symbol}",
        "url": url,
        "color": color,
        "fields": [
            {"name": "現在値", "value": f"**{current_price:,.1f}円**", "inline": True},
            {"name": "前日比", "value": f"**{diff:+.2f}%**", "inline": True},
            {"name": "‎", "value": "‎", "inline": False}, # 改行用の空フィールド
            {"name": "当日の最高値", "value": f"{high_price:,.1f}円", "inline": True},
            {"name": "当日の最安値", "value": f"{low_price:,.1f}円", "inline": True},
            {"name": "出来高", "value": f"{volume:,.0f} 株", "inline": True}
        ],
        "footer": {"text": f"取得時刻: {latest.name.strftime('%Y-%m-%d %H:%M')}"}
    }
    return embed

def main():
    if not WEBHOOK_URL: return
    embeds = []
    for symbol in WATCH_LIST:
        print(f"{symbol} をチェック中...")
        embed_data = check_stock(symbol)
        if embed_data: embeds.append(embed_data)
    
    if embeds:
        payload = {"content": "⚠️ **【プロ仕様】株価モメンタム監視報告**", "embeds": embeds}
        requests.post(WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    main()
