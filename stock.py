import os
import yfinance as yf
import requests
import pandas as pd
import random

# --- 設定 ---
WEBHOOK_URL = os.getenv("MY_DISCORD_URL")

# 判断基準
USD_BUY_THRESHOLD = 145.0
RSI_PERIOD = 14

# --- 1. 教育用データベース（商品化の核） ---
KNOWLEDGE_BASE = {
    "MARKET": "🌍 **市場全体**: 個別株の動きは、まず市場全体の波に左右されます。波が良い時に買うのが基本です。",
    "HG=F": "🏗️ **銅（材料）**: 『ドクター・コッパー』と呼ばれ、景気の先行指標。AIサーバーやEVに必須の材料です。",
    "^SOX": "💻 **SOX指数**: 半導体企業の株価指数。材料の価格と連動しやすく、ハイテク株の未来を占います。",
    "RSI": "📊 **RSI**: 0-100で過熱感を示します。初心者は30以下の『安すぎる』時に注目しましょう。"
}

# 追加機能2: 材料工学ミニ講義（ランダムに表示）
MATERIALS_LESSONS = [
    "【材料知識】銅配線はアルミニウムより電気抵抗が低く、半導体の高速化に貢献しました。銅価格はハイテクのコストに直結します。",
    "【材料知識】EV（電気自動車）はガソリン車の約3〜4倍の銅を使用します。脱炭素化は銅の需要を爆発させています。",
    "【材料知識】半導体露光装置に使われるレンズやミラーの材料、実は日本の化学メーカーが世界トップシェアを握っていることが多いです。",
    "【材料知識】次世代パワー半導体（SiCやGaN）は、省エネの鍵。これらを扱う企業の株価はエネルギー効率の需要と連動します。",
    "【材料知識】金(Gold)は腐食しにくいため、スマホの基板の接点に使われます。有事の安全資産だけでなく、ハイテク材料の側面もあります。"
]

# --- 2. 監視ターゲット ---
INDICES = {"^N225": "日経平均", "^GSPC": "S&P 500", "^SOX": "SOX指数"}
COMMODITIES = {"GC=F": "金 (Gold)", "HG=F": "銅 (Copper)"}
STOCKS = ["NVDA", "MSFT", "6857.T", "6701.T", "7974.T"]
FX_SYMBOL = "JPY=X"

def calculate_rsi(ticker_symbol):
    try:
        data = yf.download(ticker_symbol, period="1mo", interval="1d", progress=False)
        if data.empty: return None
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1].item()
    except: return None

def get_data(symbol, name=None):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="2d")
        if len(data) < 2: return None
        current = data['Close'].iloc[-1]
        prev = data['Close'].iloc[-2]
        diff_pct = ((current - prev) / prev) * 100
        return {"name": name if name else symbol, "price": current, "pct": diff_pct}
    except: return None

# 追加機能1: 市場スコアリングロジック
def calculate_market_score(fx, indices, commodities):
    score = 50 # 基準点
    # 為替: 円高ならプラス（米国株が安く買える）
    if fx and fx['price'] <= USD_BUY_THRESHOLD: score += 15
    # 指数: S&P500などが上昇していればプラス
    for idx in indices:
        if idx and idx['pct'] > 0: score += 5
    # 銅: 上昇していれば景気良しとしてプラス
    for com in commodities:
        if "Copper" in com['name'] and com['pct'] > 0: score += 10
    return min(max(score, 0), 100) # 0-100の間に収める

def main():
    if not WEBHOOK_URL: return

    fields = []
    
    # データ収集
    fx = get_data(FX_SYMBOL, "ドル円")
    index_results = [get_data(sym, label) for sym, label in INDICES.items()]
    commodity_results = [get_data(sym, label) for sym, label in COMMODITIES.items()]
    
    # スコア計算
    market_score = calculate_market_score(fx, index_results, commodity_results)
    score_comment = "💎 絶好の仕込み時かも" if market_score >= 70 else ("⚖️ 慎重に見守りましょう" if market_score >= 40 else "⚠️ 今は様子見が賢明です")

    # セクション1: 本日の市場スコア
    fields.append({
        "name": f"📈 本日の投資チャンス指数： {market_score}点",
        "value": f"**診断: {score_comment}**\n*※為替、銅価格、主要指数から算出した初心者向け指標です*",
        "inline": False
    })

    # セクション2: 市場要約
    index_text = ""
    for res in index_results:
        if res:
            mark = "📈" if res['pct'] > 0 else "📉"
            index_text += f"{mark} {res['name']}: **{res['price']:,.1f}** ({res['pct']:+.2f}%)\n"
    fields.append({"name": "🌍 市場全体（指数）", "value": index_text + f"└ *{KNOWLEDGE_BASE['MARKET']}*", "inline": False})

    # セクション3: 材料・資源
    commodity_text = ""
    for res in commodity_results:
        if res:
            mark = "⚒️" if res['pct'] > 0 else "🧱"
            commodity_text += f"{mark} {res['name']}: **{res['price']:,.1f}** ({res['pct']:+.2f}%)\n"
    fields.append({"name": "🏗️ 材料・資源分析", "value": commodity_text + f"└ *{KNOWLEDGE_BASE['HG=F']}*", "inline": False})

    # セクション4: 個別株 + RSI
    for symbol in STOCKS:
        res = get_data(symbol)
        rsi = calculate_rsi(symbol)
        if res:
            mark = "🚀" if res['pct'] > 1.0 else ("📉" if res['pct'] < -1.0 else "➖")
            rsi_val = f"{rsi:.1f}" if rsi else "--"
            opp = " 💡買い場?" if rsi and rsi < 35 else ""
            fields.append({
                "name": f"{mark} {res['name']}",
                "value": f"**{res['price']:,.1f}** ({res['pct']:+.2f}%)\n`RSI: {rsi_val}`{opp}",
                "inline": True
            })

    # Discord送信
    lesson = random.choice(MATERIALS_LESSONS)
    payload = {
        "content": f"🎓 **投資学習・監視レポート**\n{lesson}",
        "embeds": [{
            "title": "Kota's Materials Science & Invest Bot v4.0",
            "description": f"*{KNOWLEDGE_BASE['RSI']}*",
            "color": 0x3498db,
            "fields": fields,
            "footer": {"text": "理科大 材料工学専攻 | 投資教育プロダクト開発中"}
        }]
    }
    requests.post(WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    main()
