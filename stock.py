import os
import yfinance as yf
import requests
import google.generativeai as genai

# 設定の読み込み
WEBHOOK_URL = os.getenv("MY_DISCORD_URL")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# AIの設定
genai.configure(api_key=GEMINI_KEY)
# 10行目付近：モデル名を最新の安定版指定に変更します
# もしこれでもダメな場合は "gemini-1.5-pro" に変えてみてください
model = genai.GenerativeModel(model_name='gemini-1.5-flash')

# ---
# get_ai_analysis 関数の中のプロンプトを少し調整
def get_ai_analysis(symbol, diff, price):
    # (省略)
    try:
        # 安全のために、引数名を明示して呼び出します
        response = model.generate_content(contents=prompt)
        # (以下同じ)
        
        # 安全性フィルターなどで回答が空の場合のチェック
        if response.parts:
            return response.text.strip()
        else:
            print(f"AI警告: {symbol} の回答が空でした（安全性フィルターの可能性があります）")
            return "分析不可"
            
    except Exception as e:
        # ここが重要！エラーの正体をログに出力します
        print(f"AI通信エラー詳細 ({symbol}): {e}")
        return "分析エラー"

def check_stock(symbol):
    stock = yf.Ticker(symbol)
    data = stock.history(period="2d")
    if len(data) < 2: return None

    latest = data.iloc[-1]
    prev_close = data['Close'].iloc[-2]
    current_price = latest['Close']
    diff = ((current_price - prev_close) / prev_close) * 100
    
    if abs(diff) < ALERT_THRESHOLD: return None

    # --- AIミニ分析の実行 ---
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
            {"name": "🤖 AIミニ分析", "value": ai_comment, "inline": False} # AIのコメントを追加
        ],
        "footer": {"text": f"取得時刻: {latest.name.strftime('%Y-%m-%d %H:%M')}"}
    }
    return embed

def main():
    if not WEBHOOK_URL or not GEMINI_KEY:
        print("設定エラー: APIキーが足りません")
        return
    
    embeds = []
    for symbol in WATCH_LIST:
        print(f"{symbol} をチェック中...")
        embed_data = check_stock(symbol)
        if embed_data: embeds.append(embed_data)
    
    if embeds:
        payload = {"content": "⚠️ **【AI分析付】株価リアルタイム監視**", "embeds": embeds}
        requests.post(WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    main()


