import os
import yfinance as yf
import requests
import google.generativeai as genai

# --- 設定の読み込み ---
WEBHOOK_URL = os.getenv("MY_DISCORD_URL")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# --- AIの設定 ---
genai.configure(api_key=GEMINI_KEY)

# 404エラー対策：モデル名の前に 'models/' を明記して、安定版ルートを指定します
model = genai.GenerativeModel('models/gemini-1.5-flash')

WATCH_LIST = ["NVDA", "MSFT", "6857.T", "6701.T", "7974.T"]
ALERT_THRESHOLD = 0.1 

def get_ai_analysis(symbol, diff, price):
    prompt = f"銘柄{symbol}が前日比{diff:.2f}%の{price:,.1f}円になりました。1行で投資家向けの短いコメントを書いてください。"
    try:
        # シンプルに呼び出し（余計な設定を排除）
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"DEBUG Error: {e}")
        return "分析データを取得できませんでした"

def check_stock(symbol):
    stock = yf.Ticker(symbol)
    data = stock.history(period="2d")
    if len(data) < 2: return None

    latest = data.iloc[-1]
    prev_close = data['Close'].iloc[-2]
    current_price = latest['Close']
    diff = ((current_price - prev_close) / prev_close) * 100
    
    if abs(diff) < ALERT_THRESHOLD: return None

    ai_comment = get_ai_analysis(symbol, diff, current_price)

    color = 3066993 if diff > 0 else 15158332
    mark = "🚀 急騰" if diff > 0 else "📉 急落"
    
    embed = {
        "title": f"{mark} {symbol}",
        "color": color,
        "fields": [
            {"name": "現在値", "value": f"**{current_price:,.1f}円**", "inline": True},
            {"name": "前日比", "value": f"**{diff:+.2f}%**", "inline": True},
            {"name": "🤖 AIミニ分析", "value": f"```{ai_comment}```", "inline": False}
        ],
        "footer": {"text": f"取得時刻: {latest.name.strftime('%Y-%m-%d %H:%M')}"}
    }
    return embed

def main():
    if not WEBHOOK_URL or not GEMINI_KEY: return
    
    embeds = []
    for symbol in WATCH_LIST:
        print(f"{symbol} をチェック中...")
        embed_data = check_stock(symbol)
        if embed_data: embeds.append(embed_data)
    
    if embeds:
        payload = {"content": "⚠️ **株価リアルタイム監視（AI分析付）**", "embeds": embeds}
        requests.post(WEBHOOK_URL, json=payload)
        print("通知を送信しました。")

if __name__ == "__main__":
    main()
