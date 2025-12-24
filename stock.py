import os
import yfinance as yf
import requests

# --- 1. 設定：ここを好きな数字に変えてください ---
WEBHOOK_URL = os.getenv("MY_DISCORD_URL")
USD_BUY_THRESHOLD = 145.0  # 145円以下になったら「買いチャンス」と通知

# 監視銘柄
STOCKS = ["NVDA", "MSFT", "6857.T", "6701.T", "7974.T"]
FX_SYMBOL = "JPY=X"

def get_fx_data():
    """ドル円のデータを取得し、チャンス判定を行う"""
    try:
        ticker = yf.Ticker(FX_SYMBOL)
        data = ticker.history(period="2d")
        if len(data) < 2: return None
        
        current_rate = data['Close'].iloc[-1]
        prev_rate = data['Close'].iloc[-2]
        diff = current_rate - prev_rate
        diff_pct = (diff / prev_rate) * 100
        
        # ドル買いチャンス判定
        is_chance = current_rate <= USD_BUY_THRESHOLD
        
        return current_rate, diff_pct, is_chance
    except:
        return None

def check_stock(symbol):
    """株価を取得してDiscord用のデータを作る"""
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="2d")
        if len(data) < 2: return None

        latest = data.iloc[-1]
        prev_close = data['Close'].iloc[-2]
        current_price = latest['Close']
        diff_pct = ((current_price - prev_close) / prev_close) * 100
        
        if abs(diff_pct) < 0.1: return None

        color = 3066993 if diff_pct > 0 else 15158332
        mark = "🚀" if diff_pct > 0 else "📉"
        
        return {
            "name": f"{mark} {symbol}",
            "value": f"**{current_price:,.1f}** ({diff_pct:+.2f}%)",
            "inline": True
        }
    except:
        return None

def main():
    if not WEBHOOK_URL: return

    # 1. 為替チェック
    fx_info = get_fx_data()
    embed_fields = []
    alert_msg = ""
    
    if fx_info:
        rate, pct, is_chance = fx_info
        status = "【🔥 ドル買いチャンス！】" if is_chance else "【通常】"
        if is_chance:
            alert_msg = f"📢 **久田さん、1ドル {rate:.2f}円 です！ドル転の検討タイミングです。**"
        
        embed_fields.append({
            "name": f"💵 為替状況 {status}",
            "value": f"**1ドル = {rate:.2f}円** ({pct:+.2f}%)",
            "inline": False
        })

    # 2. 株価チェック
    for symbol in STOCKS:
        field = check_stock(symbol)
        if field: embed_fields.append(field)

    if embed_fields:
        payload = {
            "content": f"📊 **市場モニタリング報告**\n{alert_msg}",
            "embeds": [{
                "title": "為替・株価 リアルタイム監視",
                "color": 15105570 if alert_msg else 3447003, # チャンス時はオレンジ色に
                "fields": embed_fields,
                "footer": {"text": f"判定しきい値: {USD_BUY_THRESHOLD}円"}
            }]
        }
        requests.post(WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    main()
