import os
import yfinance as yf
import requests
import pandas as pd

# --- 設定 ---
# GitHub ActionsのSecretsに登録したURLを読み込みます
WEBHOOK_URL = os.getenv("MY_DISCORD_URL")

# 初心者向けの判断基準設定
USD_BUY_THRESHOLD = 145.0  # 145円以下なら「買いチャンス」と教える
RSI_PERIOD = 14            # RSIの計算期間（一般的に14日）

# --- 1. 教育用データベース（商品化の核となる部分） ---
# 初心者が指標の意味を理解できるようにするための「教材辞書」です。
KNOWLEDGE_BASE = {
    "MARKET": "🌍 **市場全体**: 個別株の動きは、まず市場全体の波に左右されます。波が良い時に買うのが基本です。",
    "HG=F": "🏗️ **銅（材料）**: 『ドクター・コッパー』と呼ばれ、景気の先行指標です。半導体やEVに必須の材料。価格上昇は産業の活発化を意味します。",
    "^SOX": "💻 **SOX指数**: 半導体企業の株価指数。材料（銅など）の価格と連動することが多く、ハイテク株の未来を占います。",
    "RSI": "📊 **RSI**: 0-100で『買われすぎ(70以上)』『売られすぎ(30以下)』を示します。初心者は『安すぎる』時に注目しましょう。",
    "FX": "💵 **為替**: 140円台など円高に振れると、米国株やドルの仕込み時になります。"
}

# --- 2. 監視ターゲット ---
# 指数（市場全体）
INDICES = {
    "^N225": "日経平均",
    "^GSPC": "S&P 500",
    "^SOX": "SOX指数(半導体)"
}
# 材料・コモディティ
COMMODITIES = {
    "GC=F": "金 (Gold)",
    "HG=F": "銅 (Copper)",
    "TIO=F": "鉄鉱石 (Iron Ore)"
}
# 個別株
STOCKS = ["NVDA", "MSFT", "6857.T", "6701.T", "7974.T"]
FX_SYMBOL = "JPY=X"

def calculate_rsi(ticker_symbol):
    """テクニカル指標RSIを計算（投資判断の根拠となる数値）"""
    try:
        data = yf.download(ticker_symbol, period="1mo", interval="1d", progress=False)
        if data.empty: return None
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1].item()
    except:
        return None

def get_data(symbol, name=None):
    """株価・為替・材料データを取得"""
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
    if not WEBHOOK_URL:
        print("Error: WEBHOOK_URL is not set.")
        return

    fields = []
    
    # --- 3. セクション分けしたデータ構築 ---
    
    # セクション1: 為替（ドルの買い時教育）
    fx = get_data(FX_SYMBOL, "ドル円 (USD/JPY)")
    if fx:
        is_chance = fx['price'] <= USD_BUY_THRESHOLD
        status = "【🔥 買い時チャンス】" if is_chance else "【通常】"
        lesson = f"\n└ *{KNOWLEDGE_BASE['FX']}*"
        fields.append({
            "name": f"💵 1. 為替状況 {status}",
            "value": f"**1ドル = {fx['price']:.2f}円** ({fx['pct']:+.2f}%){lesson}",
            "inline": False
        })

    # セクション2: 市場全体（指数）の要約
    index_text = ""
    for sym, label in INDICES.items():
        res = get_data(sym, label)
        if res:
            mark = "📈" if res['pct'] > 0 else "📉"
            index_text += f"{mark} {res['name']}: **{res['price']:,.1f}** ({res['pct']:+.2f}%)\n"
    if index_text:
        index_text += f"*Advice: {KNOWLEDGE_BASE['MARKET']}*"
        fields.append({"name": "🌍 2. 市場全体（指数）の要約", "value": index_text, "inline": False})

    # セクション3: 材料工学視点の分析（商品化の強み）
    commodity_text = ""
    copper_surging = False
    for sym, label in COMMODITIES.items():
        res = get_data(sym, label)
        if res:
            if "Copper" in label and res['pct'] > 0.3: copper_surging = True
            mark = "⚒️" if res['pct'] > 0 else "🧱"
            commodity_text += f"{mark} {res['name']}: **{res['price']:,.1f}** ({res['pct']:+.2f}%)\n"
    
    if commodity_text:
        analysis = f"\n💡 **材料分析**: {KNOWLEDGE_BASE['HG=F']}"
        if copper_surging:
            analysis += "\n⚠️ **注目**: 銅価格が上昇中。半導体セクターに追い風の可能性があります。"
        fields.append({"name": "🏗️ 3. 材料・資源価格と分析", "value": commodity_text + analysis, "inline": False})

    # セクション4: 個別株監視 + RSI教育
    for symbol in STOCKS:
        res = get_data(symbol)
        rsi = calculate_rsi(symbol)
        if res:
            mark = "🚀" if res['pct'] > 1.0 else ("📉" if res['pct'] < -1.0 else "➖")
            rsi_info = f"RSI: {rsi:.1f}" if rsi else "RSI: --"
            opportunity = " 💡買い場?" if rsi and rsi < 35 else (" ⚠️過熱気味" if rsi and rsi > 70 else "")
            
            fields.append({
                "name": f"{mark} {res['name']}",
                "value": f"**{res['price']:,.1f}** ({res['pct']:+.2f}%)\n`{rsi_info}`{opportunity}",
                "inline": True
            })

    # --- 4. Discord送信 ---
    payload = {
        "content": "🎓 **投資
