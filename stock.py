import os
import yfinance as yf
import requests
import pandas as pd
import random
from datetime import datetime, timedelta

# --- 設定 ---
WEBHOOK_URL = os.getenv("MY_DISCORD_URL")
HISTORY_FILE = "market_history.csv"  # 過去データを保存するファイル名

# 判断基準
USD_BUY_THRESHOLD = 145.0
RSI_PERIOD = 14
PREDICTION_DAYS = 7  # 何日前の予測を検証するか（1週間前）

# --- 1. 教育用データベース（商品化の核） ---
KNOWLEDGE_BASE = {
    "MARKET": "🌍 **市場全体**: 個別株の動きは市場の波に左右されます。波が良い時に買うのが基本です。",
    "HG=F": "🏗️ **銅（材料）**: 景気の先行指標。AIやEVに必須の材料です。価格上昇は産業の活発化を意味します。",
    "RSI": "📊 **RSI**: 30以下は『安すぎ』、70以上は『過熱』。初心者は安値を拾う目安にしましょう。",
    "WIN_RATE": "🎯 **的中率**: 1週間前に『高スコア』だった際、実際に価格が上がった割合です。システムの信頼性を示します。"
}

MATERIALS_LESSONS = [
    "【材料知識】銅配線は半導体の高速化に不可欠。銅価格はハイテク産業のコストに直結します。",
    "【材料知識】EVはガソリン車の3〜4倍の銅を使用。脱炭素化は銅需要を爆発させています。",
    "【材料知識】半導体材料のシリコンウエハー、実は日本企業（信越化学・SUMCO）が世界シェアの半分以上を占めています。",
    "【材料知識】次世代半導体材料(SiC)は電力ロスを激減させます。テスラのEVにも採用され注目されました。"
]

# --- 2. ターゲット ---
INDICES = {"^GSPC": "S&P 500", "^SOX": "SOX指数"}
STOCKS = ["NVDA", "6857.T"] # 検証用に主要銘柄に絞る
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

# --- 3. 実績保存と的中率計算（新機能） ---
def update_performance(today_score, current_price):
    today_str = datetime.now().strftime('%Y-%m-%d')
    new_data = pd.DataFrame([[today_str, today_score, current_price]], columns=['Date', 'Score', 'Price'])
    
    if os.path.exists(HISTORY_FILE):
        history_df = pd.read_csv(HISTORY_FILE)
        history_df = pd.concat([history_df, new_data], ignore_index=True).drop_duplicates('Date')
    else:
        history_df = new_data
    
    history_df.to_csv(HISTORY_FILE, index=False)
    
    # 的中率の計算
    try:
        # 7日前のデータを探す
        target_date = (datetime.now() - timedelta(days=PREDICTION_DAYS)).strftime('%Y-%m-%d')
        past_records = history_df[history_df['Date'] <= target_date]
        
        if len(past_records) < 1:
            return "データ蓄積中...", "まだ十分な過去データがありません。1週間後から表示されます。"

        # スコア70以上の時に、その後価格が上がったか
        buy_signals = history_df[history_df['Score'] >= 70]
        hits = 0
        total_signals = 0
        
        for idx, row in buy_signals.iterrows():
            # その日の価格と、それ以降の最新価格を比較
            future_prices = history_df.iloc[idx + 1:]
            if not future_prices.empty:
                total_signals += 1
                if future_prices.iloc[-1]['Price'] > row['Price']:
                    hits += 1
        
        win_rate = (hits / total_signals * 100) if total_signals > 0 else 0
        return f"{win_rate:.1f}%", f"過去 {total_signals} 回の買い推奨中、{hits} 回価格が上昇しました。"
    except:
        return "計算中...", "データの分析中です。"

def calculate_market_score(fx, index_results):
    score = 50
    if fx and fx['price'] <= USD_BUY_THRESHOLD: score += 20
    for res in index_results:
        if res and res['pct'] > 0: score += 10
    return min(max(score, 0), 100)

def main():
    if not WEBHOOK_URL: return

    # データ収集
    fx = get_data(FX_SYMBOL, "ドル円")
    idx_res = [get_data(sym, label) for sym, label in INDICES.items()]
    
    # スコアと的中率の計算
    m_score = calculate_market_score(fx, idx_res)
    # 代表としてS&P500(idx_res[0])の価格で検証
    current_market_price = idx_res[0]['price'] if idx_res[0] else 0
    win_rate, win_comment = update_performance(m_score, current_market_price)

    fields = []
    # 的中率セクション
    fields.append({
        "name": f"🎯 システム的中率: {win_rate}",
        "value": f"{win_comment}\n*Advice: {KNOWLEDGE_BASE['WIN_RATE']}*",
        "inline": False
    })

    # 市場スコア
    status_emoji = "💎" if m_score >= 70 else ("⚖️" if m_score >= 40 else "⚠️")
    fields.append({
        "name": f"{status_emoji} 本日の市場スコア: {m_score}点",
        "value": f"**判定: {'買い推奨' if m_score >= 70 else '様子見'}**",
        "inline": True
    })

    # 指数と個別株（簡略化して表示）
    stock_text = ""
    for symbol in STOCKS:
        res = get_data(symbol)
        rsi = calculate_rsi(symbol)
        if res:
            stock_text += f"🔹 {res['name']}: {res['price']:,.0f} ({res['pct']:+.2f}%) RSI:{rsi:.1f}\n"
    fields.append({"name": "📈 注目銘柄の動き", "value": stock_text, "inline": False})

    # Discord送信
    lesson = random.choice(MATERIALS_LESSONS)
    payload = {
        "content": f"🎓 **投資実績・監視レポート**\n{lesson}",
        "embeds": [{
            "title": "Kota's Invest System v5.0",
            "color": 0xe74c3c if m_score < 40 else 0x2ecc71,
            "fields": fields,
            "footer": {"text": "理科大 材料工学専攻 | 実績に基づく投資教育を目指して"}
        }]
    }
    requests.post(WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    main()
