import os
import yfinance as yf
import requests
import pandas as pd

# --- 設定 ---
WEBHOOK_URL = os.getenv("MY_DISCORD_URL")
USD_BUY_THRESHOLD = 145.0
RSI_PERIOD = 14

# 監視リスト
INDICES = {
    "^N225": "日経平均",
    "^GSPC": "S&P 500",
    "^SOX": "SOX指数(半導体)"
}
STOCKS = ["NVDA", "MSFT", "6857.T", "6701.T", "7974.T"]
COMMODITIES = {
    "GC=F": "金 (Gold)",
    "HG=F": "銅 (Copper)",
    "TIO=F": "鉄鉱石 (Iron)",
    "PL=F": "プラチナ (Pt)"
}
FX_SYMBOL = "JPY=X"

def calculate_rsi(ticker_symbol):
    """RSIを計算して売買の過熱感を判定する"""
    try:
        data = yf.download(ticker_symbol, period="1mo", interval="1d", progress=False)
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1].item()
    except:
        return None

def get_data(symbol, name=None):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="2d")
        if len(data) < 2: return None
        current = data['Close'].iloc[-1]
        prev = data['Close'].iloc[-2]
        diff_pct = ((current - prev) / prev) * 100
        return {"name": name if name else symbol, "price": current, "pct": diff_pct}
    except:
        return None

def main():
    if not WEBHOOK_URL: return
    embed_fields = []
    
    # 1. 為替チェック
    fx = get_data(FX_SYMBOL, "ドル円 (USD/JPY)")
    if fx:
        status = "【🔥 買い時】" if fx['price'] <= USD_BUY_THRESHOLD else "【通常】"
        embed_fields.append({
            "name": f"💵 1. 為替状況 {status}",
            "value": f"**1ドル = {fx['price']:.2f}円** ({fx['pct']:+.2f}%)",
            "inline": False
        })

    # 2. 指数チェック（追加：市場全体の要約）
    index_text = ""
    for sym, label in INDICES.items():
        res = get_data(sym, label)
        if res:
            mark = "📈" if res['pct'] > 0 else "📉"
            index_text += f"{mark} {res['name']}: **{res['price']:,.1f}** ({res['pct']:+.2f}%)\n"
    if index_text:
        embed_fields.append({"name": "🌍 2. 市場全体（指数）の要約", "value": index_text, "inline": False})

    # 3. 材料価格（材料工学視点）
    commodity_text = ""
    copper_up = False
    for sym, label in COMMODITIES.items():
        res = get_data(sym, label)
        if res:
            if "Copper" in label and res['pct'] > 0.5: copper_up = True
            mark = "🏗️" if res['pct'] > 0 else "🧱"
            commodity_text += f"{mark} {res['name']}: **{res['price']:,.1f}** ({res['pct']:+.2f}%)\n"
    if commodity_text:
        embed_fields.append({"name": "⚒️ 3. 主要材料・資源価格", "value": commodity_text, "inline": False})

    # 4. 個別株 + RSI分析（稼ぐための判断材料）
    for symbol in STOCKS:
        res = get_data(symbol)
        rsi = calculate_rsi(symbol)
        if res:
            rsi_msg = f" (RSI:{rsi:.1f})" if rsi else ""
            mark = "🚀" if res['pct'] > 1.0 else ("📉" if res['pct'] < -1.0 else "➖")
            # RSIによるチャンス示唆
            opportunity = " 💡買い場?" if rsi and rsi < 35 else (" ⚠️過熱気味" if rsi and rsi > 70 else "")
            
            embed_fields.append({
                "name": f"{mark} {res['name']}",
                "value": f"**{res['price']:,.1f}** ({res['pct']:+.2f}%){rsi_msg}{opportunity}",
                "inline": True
            })

    # 特記事項：銅と半導体の相関アラート
    note = ""
    if copper_up:
        note = "\n💡 **【分析】銅価格が上昇中。半導体セクターへの追い風を確認してください。**"

    # Discord送信
    payload = {
        "content": f"📊 **市場モニタリング報告** {note}",
        "embeds": [{
            "title": "為替・指数・材料・株価 総合監視",
            "color": 0x1E90FF,
            "fields": embed_fields,
            "footer": {"text": "理科大 材料工学専攻 投資戦略ボット v2.0"}
        }]
    }
    requests.post(WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    main()
