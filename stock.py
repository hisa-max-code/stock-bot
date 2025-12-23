import os
import yfinance as yf
import requests
import google.generativeai as genai

# --- 1. 設定の読み込み ---
WEBHOOK_URL = os.getenv("MY_DISCORD_URL")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# --- 2. AIの設定（404エラー対策） ---
genai.configure(api_key=GEMINI_KEY)

# 'gemini-1.5-flash' ではなく 'models/gemini-1.5-flash' と明示するのが最新の正解です
model = genai.GenerativeModel('models/gemini-1.5-flash')

WATCH_LIST = ["NVDA", "MSFT", "6857.T", "6701.T", "7974.T"]
ALERT_THRESHOLD = 0.1 

def get_ai_analysis(symbol, diff, price):
    """AIに株価の動きを分析してもらう"""
    prompt = f"銘柄{symbol}が前日比{diff:.2f}%の{price:,.1f}円になりました。この動きに対する短いコメントを1行（30文字以内）で書いてください。"
    try:
        # 通信エラーを避けるための最新の書き方
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        # 通信失敗時はログにエラー内容を出して、分析エラーと返す
        print(f"DEBUG: {symbol} 分析失敗: {e}")
        return "分析データを取得できませんでした"

def check_stock(symbol):
    stock = yf.Ticker(symbol)
    data = stock.history(period="2d")
    if len(data) < 2: return None

    latest = data.iloc[-1]
    prev_close = data['Close'].iloc[-2]
    current_price = latest['Close']
    high_price = latest['High']
    low_price = latest['Low']
    volume = latest['Volume']
    
    diff = ((current_price - prev_close) / prev_close) * 100
    
    if abs(diff) < ALERT_THRESHOLD: return None

    # AI分析の実行
    ai_comment = get_ai_analysis(symbol, diff, current_price)

    color = 3066993 if diff > 0 else 15158332
    mark = "🚀 急騰" if diff > 0 else "📉 急落"
    url = f"https://finance.yahoo.co.jp/quote/{symbol.replace('.T', '')}" if ".T" in symbol else f"https://finance.yahoo.com/quote/{symbol}"

    embed = {
        "title": f"{mark} {symbol}",
        "url": url,
        "color": color,
        "fields": [
            {"name": "現在値", "value": f"**{current_price:,.1f}円**", "inline": True},
            {"name": "前日比", "value": f"**{diff:+.2f}%**", "inline": True},
            {"name": "🤖 AIミニ分析", "value": f"```{ai_comment}```", "inline": False},
            {"name": "高値/安値", "value": f"{high_price:,.1f} / {low_price:,.1f}", "inline": True},
            {"name": "出来高", "value": f"{volume:,.0f}", "inline": True}
        ],
        "footer": {"text": f"取得時刻: {latest.name.strftime('%Y-%m-%d %H:%M')}"}
    }
    return embed

def main():
    if not WEBHOOK_URL or not GEMINI_KEY:
        print("設定エラー: APIキーがありません")
        return
    
    embeds = []
    for symbol in WATCH_LIST:
        print(f"{symbol} をチェック中...")
        embed_data = check_stock(symbol)
        if embed_data: embeds.append(embed_data)
    
    if embeds:
        payload = {"content": "⚠️ **【AI分析付】株価リアルタイム監視報告**", "embeds": embeds}
        requests.post(WEBHOOK_URL, json=payload)
        print("通知を送信しました。")
    else:
        print("大きな値動きはありませんでした。")

if __name__ == "__main__":
    main()
