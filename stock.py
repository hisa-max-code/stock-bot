import os
import yfinance as yf
import requests

# --- 設定 ---
WEBHOOK_URL = os.getenv("MY_DISCORD_URL")
USD_BUY_THRESHOLD = 145.0  # ドル買いチャンスのしきい値

# 監視リスト
STOCKS = ["NVDA", "MSFT", "6857.T", "6701.T", "7974.T"]
# 材料・コモディティのリスト（yfinanceの先物シンボル）
COMMODITIES = {
    "GC=F": "金 (Gold)",
    "HG=F": "銅 (Copper)",
    "TIO=F": "鉄鉱石 (Iron Ore)",
    "PL=F": "プラチナ (Pt)"
}
FX_SYMBOL = "JPY=X"

def get_data(symbol, name=None):
    """株価・為替・材料のデータを一括で取得する関数"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="2d")
        if len(data) < 2: return None

        current = data['Close'].iloc[-1]
        prev = data['Close'].iloc[-2]
        diff_pct = ((current - prev) / prev) * 100
        
        display_name = name if name else symbol
        return {"name": display_name, "price": current, "pct": diff_pct}
    except:
        return None

def main():
    if not WEBHOOK_URL: return

    embed_fields = []
    
    # 1. 為替チェック
    fx = get_data(FX_SYMBOL, "ドル円 (USD/JPY)")
    alert_msg = ""
    if fx:
        is_chance = fx['price'] <= USD_BUY_THRESHOLD
        status = "【🔥 チャンス】" if is_chance else "【通常】"
        if is_chance:
            alert_msg = f"📢 **ドル安（円高）です！ドル転を検討してください。**"
        
        embed_fields.append({
            "name": f"💵 為替 {status}",
            "value": f"**1ドル = {fx['price']:.2f}円** ({fx['pct']:+.2f}%)",
            "inline": False
        })

    # 2. 材料価格の取得（New!）
    commodity_text = ""
    for sym, label in COMMODITIES.items():
        res = get_data(sym, label)
        if res:
            mark = "📈" if res['pct'] > 0 else "📉"
            commodity_text += f"{mark} {res['name']}: **{res['price']:,.1f}** ({res['pct']:+.2f}%)\n"
    
    if commodity_text:
        embed_fields.append({
            "name": "🏗️ 主要材料・資源価格",
            "value": commodity_text,
            "inline": False
        })

    # 3. 個別株チェック
    for symbol in STOCKS:
        res = get_data(symbol)
        if res and abs(res['pct']) >= 0.1:
            mark = "🚀" if res['pct'] > 0 else "📉"
            embed_fields.append({
                "name": f"{mark} {res['name']}",
                "value": f"**{res['price']:,.1f}** ({res['pct']:+.2f}%)",
                "inline": True
            })

    if embed_fields:
        payload = {
            "content": f"📊 **市場モニタリング報告**\n{alert_msg}",
            "embeds": [{
                "title": "為替・材料・株価 リアルタイム監視",
                "color": 3447003,
                "fields": embed_fields,
                "footer": {"text": "理科大 材料工学専攻 監視ボット"}
            }]
        }
        requests.post(WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    main()
