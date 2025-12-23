import os
import yfinance as yf
import requests

# 【重要】GitHub Actionsを使う場合は、URLを直接書かずにSecretsから読み込みます
# もし自分のPC(Cursor)でテストしたい場合は、ここを "https://..." と囲って書いてください
WEBHOOK_URL = os.getenv("MY_DISCORD_URL")

STOCK_CODE = "7203.T" 

def main():
    # URLが設定されていない場合のエラー回避
    if not WEBHOOK_URL:
        print("エラー: MY_DISCORD_URL が設定されていません。")
        return

    stock = yf.Ticker(STOCK_CODE)
    data = stock.history(period="2d")
    
    if len(data) < 2:
        print("エラー: 株価データが取得できませんでした。")
        return

    latest_price = data['Close'].iloc[-1]
    old_price = data['Close'].iloc[-2]
    diff = ((latest_price - old_price) / old_price) * 100
    
    # テストのために条件を外して必ず送るようにします
    message = f"【自動チェック成功】\n銘柄: {STOCK_CODE}\n現在値: {latest_price:,.1f}円\n前日比: {diff:+.2f}%"
    
    payload = {"content": message}
    response = requests.post(WEBHOOK_URL, json=payload)
    
    if response.status_code == 204:
        print("Discordへの送信に成功しました！")
    else:
        print(f"Discordへの送信に失敗しました。ステータスコード: {response.status_code}")

if __name__ == "__main__":
    main()
