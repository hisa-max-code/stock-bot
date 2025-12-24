import os
import yfinance as yf
import requests
import pandas as pd
import random
from datetime import datetime, timedelta

# --- 設定 ---
WEBHOOK_URL = os.getenv("MY_DISCORD_URL")
HISTORY_FILE = "market_history.csv"

# 判断基準
USD_BUY_THRESHOLD = 145.0
RSI_PERIOD = 14
PREDICTION_DAYS = 7  # 1週間前の予測を検証

# --- 1. 教育用データベース ---
KNOWLEDGE_BASE = {
    "MARKET": "🌍 **市場全体**: 個別株の動きは、まず市場全体の波に左右されます。波が良い時に買うのが基本です。",
    "HG=F": "🏗️ **銅（材料）**: 『ドクター・コッパー』。半導体やEVに必須の材料で、価格上昇は景気回復のサインです。",
    "RSI": "📊 **RSI**: 30以下は『安すぎ』、70以上は『過熱』。初心者は安値を拾う目安にしましょう。",
    "WIN_RATE": "🎯 **的中率**: 1週間前に『高スコア』だった際、実際に市場が上がった割合。システムの信頼性です。"
}

MATERIALS_LESSONS = [
    "【材料知識】銅配線は半導体の高速化に不可欠。銅価格はハイテク産業のコストに直結します。",
    "【材料知識】EVはガソリン車の3〜4倍の銅を使用。脱炭素化は銅需要を爆発させています。",
    "【材料知識】半導体材料のシリコンウエハー、実は日本企業（信越化学・SUMCO）が世界シェアの半分以上を占めています。",
    "【材料知識】次世代半導体材料(SiC)は電力ロスを激減させます。材料の進化が投資テーマになります。"
]

# --- 2. 監視ターゲット（以前のリストを完全復元） ---
INDICES = {"^N225": "日経平均", "^GSPC": "S&P 500", "^SOX": "SOX指数"}
COMMODITIES = {"GC=F": "金 (Gold)", "HG=F": "銅 (Copper)"}
STOCKS = ["NVDA", "MSFT", "6857.T", "6701.T", "7974.T"]
FX_SYMBOL = "JPY=X"

def calculate_rsi(symbol):
    try:
        data = yf.download(symbol, period="1mo", interval="1d", progress=False)
        if data.empty: return None
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
        rsi = 100 - (100 / (1 + (gain / loss)))
        return rsi.iloc[-1].item()
    except: return None

def get_data(symbol, name=None):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="2d")
        if len(data) < 2: return None
        current = data['Close'].iloc[-1]
        prev = data['Close'].iloc[-2]
        return {"name": name if name else symbol, "price": current, "pct": ((current - prev) / prev) * 100}
    except: return None

# --- 3. 実績保存と的中率計算 ---
def update_performance(today_score, current_price):
    today_str = datetime.now().strftime('%Y-%m-%d')
    new_data = pd.DataFrame([[today_str, today_score, current_price]], columns=['Date', 'Score', 'Price'])
    if os.path.exists(HISTORY_FILE):
        history_df = pd.read_csv(HISTORY_FILE)
        history_df = pd.concat([history_df, new_data], ignore_index=True).drop_duplicates('Date')
    else:
        history_df = new_data
    history_df.to_csv(HISTORY_FILE, index=False)
    
    try:
        target_date = (datetime.now() - timedelta(days=PREDICTION_DAYS)).strftime('%Y-%m-%d')
        past_records = history_df[history_df['Date'] <= target_date]
        if len(past_records) < 1: return "蓄積中...", "1週間後から表示されます。"
        buy_signals = history_df[history_df['Score'] >= 70]
        hits = 0
        total = 0
        for idx, row in buy_signals.iterrows():
            future = history_df.iloc[idx + 1:]
            if not future.empty:
                total += 1
                if future.iloc[-1]['Price'] > row['Price']: hits += 1
        return f"{(hits/total*100):.1f}%" if total > 0 else "0.0%", f"過去{total}回の買い推奨中、{hits}回的中。"
    except: return "分析中...", "データ収集中。"

def calculate_market_score(fx, idx_res, com_res):
    score = 50
    if fx and fx['price'] <= USD_BUY_THRESHOLD: score += 15
    for r in idx_res: 
        if r and r['pct'] > 0: score += 5
    for r in com_res:
        if r and "Copper" in r['name'] and r['pct'] > 0: score += 10
    return min(max(score, 0), 100)

def main():
    if not WEBHOOK_URL: return
    # データ収集
    fx = get_data(FX_SYMBOL, "ドル円")
    idx_res = [get_data(s, l) for s, l in INDICES.items()]
    com_res = [get_data(s, l) for s, l in COMMODITIES.items()]
    
    # 的中率・スコア計算
    m_score = calculate_market_score(fx, idx_res, com_res)
    win_rate, win_msg = update_performance(m_score, idx_res[1]['price'] if idx_res[1] else 0) # S&P500で検証

    fields = []
    # 的中率
    fields.append({"name": f"🎯 的中率: {win_rate}", "value": f"{win_msg}\n└ *{KNOWLEDGE_BASE['WIN_RATE']}*", "inline": False})
    
    # 市場スコア
    emoji = "💎" if m_score >= 70 else ("⚖️" if m_score >= 40 else "⚠️")
    fields.append({"name": f"{emoji} 投資チャンス指数: {m_score}点", "value": f"**判定: {'買い推奨' if m_score >= 70 else '様子見'}**", "inline": False})

    # 指数（v4.0形式の復元）
    idx_txt = "".join([f"{'📈' if r['pct']>0 else '📉'} {r['name']}: {r['price']:,.1f} ({r['pct']:+.2f}%)\n" for r in idx_res if r])
    fields.append({"name": "🌍 市場全体（指数）", "value": f"{idx_txt}└ *{KNOWLEDGE_BASE['MARKET']}*", "inline": False})

    # 材料（v4.0形式の復元）
    com_txt = "".join([f"{'⚒️' if r['pct']>0 else '🧱'} {r['name']}: {r['price']:,.1f} ({r['pct']:+.2f}%)\n" for r in com_res if r])
    fields.append({"name": "🏗️ 材料・資源分析", "value": f"{com_txt}└ *{KNOWLEDGE_BASE['HG=F']}*", "inline": False})

    # 個別株
    for s in STOCKS:
        r = get_data(s); rsi = calculate_rsi(s)
        if r:
            mark = "🚀" if r['pct'] > 1.0 else ("📉" if r['pct'] < -1.0 else "➖")
            opp = " 💡買い場?" if rsi and rsi < 35 else ""
            fields.append({"name": f"{mark} {r['name']}", "value": f"**{r['price']:,.1f}** ({r['pct']:+.2f}%)\n`RSI:{rsi:.1f}`{opp}", "inline": True})

    # 送信
    lesson = random.choice(MATERIALS_LESSONS)
    payload = {"content": f"🎓 **投資教育・監視レポート**\n{lesson}",
               "embeds": [{"title": "Kota's Invest System v5.1", "description": f"*{KNOWLEDGE_BASE['RSI']}*",
                           "color": 0x3498db, "fields": fields, "footer": {"text": "理科大 材料工学専攻 | 商品化プロトタイプ開発中"}}]}
    requests.post(WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    main()
