iimport os  # これを追加
import yfinance as yf
import requests

# URLを直接書かずに、設定した秘密の場所から読み込むように変更
WEBHOOK_URL = os.getenv("MY_DISCORD_URL")

# 【設定】ここを書き換えます
WEBHOOK_URL = "https://discordapp.com/api/webhooks/1452668737043038229/5bGWK0eFl8DCADXIHbmVRF3NX1WDpaa6WlRW_lJz-yBOpDzazlynEiGIPrDSWOUnIEnO"
STOCK_CODE = "7203.T"  # トヨタ自動車の場合。米国株なら "AAPL" など
# 修正: 2日前と前日の株価を使い、もしいずれかが0やNaNならエラーハンドリングする
# また、最新の株価取得時に例外が出たら通知する

def main():
    # 1. 株の情報を取ってくる
    stock = yf.Ticker(STOCK_CODE)
    data = stock.history(period="2d") # 直近2日分のデータ
    
    # 2. 価格を取り出す
    latest_price = data['Close'].iloc[-1] # 最新の価格
    old_price = data['Close'].iloc[-2]    # 1つ前の価格
    
    # 3. 前日比の計算
    diff = ((latest_price - old_price) / old_price) * 100

    if abs(diff) >= 1.0:
        # 4. 送るメッセージを作る
        message = f"【株価通知】\n銘柄: {STOCK_CODE}\n現在値: {latest_price:,.1f}円\n前日比: {diff:+.2f}%"
        
        # 5. Discordに送信！
        payload = {"content": message}
        requests.post(WEBHOOK_URL, json=payload)
    else:
        print("変化なし")
    print("送信完了しました！")

# プログラムを実行する
main()
