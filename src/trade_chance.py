import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta

def extract_data_from_html(html_content):
    """
    HTMLコンテンツを受け取り、目的のデータを抽出してリストとして返す。
    ★★★ このバージョンでは、まずページの主要なテキストを全て取得します ★★★
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    extracted_data = []
    
    # --- ▼▼▼ 修正箇所 START ▼▼▼ ---
    #
    # <body> タグの中にある全てのテキストを取得し、改行で連結する
    # これにより、まずページにどのようなテキスト情報があるか全体像を把握できます。
    #
    body_content = soup.body
    if body_content:
        # get_text() を使い、人間が読みやすいようにテキストを抽出
        # separator='\n' で、各要素を改行で区切ります
        full_text = body_content.get_text(separator='\n', strip=True)
        extracted_data.append(full_text)
    #
    # --- ▲▲▲ 修正箇所 END ▲▲▲ ---

    if not extracted_data:
        return ["★★★ ページの本文（bodyタグ）からテキストを取得できませんでした。 ★★★"]
            
    return extracted_data

def main():
    """
    メインの処理を実行する関数
    """
    base_url = "https://sbi.alpaca-tech.ai/trade_chance/buy"
    urls_to_scrape = []
    today = datetime.now()

    print("--- 取得対象URLリスト ---")
    for i in range(7):
        target_date = today - timedelta(days=i)
        date_str = target_date.strftime('%Y-%m-%d')
        morning_url = f"{base_url}/{date_str}/morning"
        evening_url = f"{base_url}/{date_str}/evening"
        urls_to_scrape.append(morning_url)
        urls_to_scrape.append(evening_url)
        print(morning_url)
        print(evening_url)
    print("------------------------")

    for url in urls_to_scrape:
        print(f"\n[INFO] 処理中: {url}")
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                data = extract_data_from_html(response.content)
                print("[OK] 取得したページ本文テキスト:")
                for item in data:
                    # 長すぎるので、ターミナルの表示は最初の1000文字に制限
                    print(item[:1000] + "...")
            else:
                print(f"[WARN] ページが存在しないか、アクセスできませんでした (ステータスコード: {response.status_code})")

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] 通信エラーが発生しました: {e}")
        except Exception as e:
            print(f"[ERROR] 不明なエラーが発生しました: {e}")
        
        time.sleep(1)

if __name__ == '__main__':
    main()
    print("\n全ての処理が完了しました。")