import os
import yfinance as yf
import requests

# --- 設定の読み込み ---
WEBHOOK_URL = os.getenv("MY_DISCORD_URL")

# 監視する銘柄と為替
STOCKS = ["NVDA", "MSFT", "6857.T", "6701.T", "7974.T"]
FX_SYMBOL = "JPY=X" # ドル円のシンボル

def get_fx_data():
    """ドル円の現在値と前日比を取得する"""
    try:
        ticker = yf.Ticker(FX_SYMBOL)
        data = ticker.history(period="2d")
        if len(data) < 2: return None
        
        current_rate = data['Close'].iloc[-1]
        prev_rate = data['Close'].iloc[-2]
        diff = current_rate - prev_rate
        diff_pct = (diff / prev_rate) * 100
        return current_rate, diff, diff_pct
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
        
        # 変動が0.1%未満なら通知しない
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
    if not WEBHOOK_URL:
        print("設定エラー: DiscordのURLがありません")
        return

    # 為替データの取得
    fx_info = get_fx_data()
    embed_fields = []
    
    if fx_info:
        rate, diff, pct = fx_info
        fx_mark = "円安" if diff > 0 else "円高"
        embed_fields.append({
            "name": f"💵 現在の為替 (USD/JPY)",
            "value": f"**1ドル = {rate:.2f}円** ({pct:+.2f}% / {fx_mark})",
            "inline": False
        })

    # 株価データの取得
    for symbol in STOCKS:
        field = check_stock(symbol)
        if field:
            embed_fields.append(field)

    if embed_fields:
        payload = {
            "content": "📊 **本日の市場モニタリング**",
            "embeds": [{
                "title": "為替・株価 リアルタイム報告",
                "color": 3447003,
                "fields": embed_fields,
                "footer": {"text": "yfinanceデータ使用"}
            }]
        }
        requests.post(WEBHOOK_URL, json=payload)
        print("通知を送信しました。")

if __name__ == "__main__":
    main()
