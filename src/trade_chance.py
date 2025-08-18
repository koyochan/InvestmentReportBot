import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import os
import re

def extract_data_from_html(html_content):
    """
    HTMLコンテンツから「買いシグナル銘柄一覧」の各銘柄データを抽出する。
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    extracted_stocks = []

    # ページ全体から、個々の銘柄情報（カード）をすべて探す
    # 各銘柄は class="trade-chance__stock" のdivで囲まれている
    stock_cards = soup.find_all('div', class_='trade-chance__stock')
    
    if not stock_cards:
        # 「TOP5」のみで「一覧」がないページも考慮
        header = soup.find(['h2', 'h3'], string=re.compile(r'本日の買いシグナル点灯銘柄TOP5'))
        if header:
            # TOP5の場合は、親要素から a タグを探す
            list_container = header.find_next_sibling()
            if list_container:
                stock_cards = list_container.find_all('a')
        
    if not stock_cards:
        return ["銘柄リストが見つかりませんでした。"]

    # 各カードから、必要な情報を抜き出す
    for card in stock_cards:
        # try...exceptで、どれか一つの情報取得に失敗してもエラーで止まらないようにする
        try:
            name, code, win_loss_str, return_rate = "N/A", "N/A", "N/A", "N/A"

            # 銘柄名と証券コードの取得
            name_container = card.find('div', class_='trade-chance__stock-name')
            if name_container:
                name_tag = name_container.find('a')
                code_tag = name_container.find('span')
                if name_tag and code_tag:
                    name = name_tag.text.strip()
                    code = code_tag.text.strip()

            # 勝敗の取得
            signal_graph = card.find('div', class_='signal-graph__texts')
            if signal_graph:
                p_tag = signal_graph.find('p')
                if p_tag:
                    spans = p_tag.find_all('span')
                    if len(spans) >= 2:
                        wins = spans[0].text.strip()
                        losses = spans[1].text.strip()
                        win_loss_str = f"{wins}勝/{losses}敗"

            # 期待上昇率の取得
            description_p = card.find('p', class_='trade-chance__stock__signal__description')
            if description_p:
                match = re.search(r'上昇率は(.*?%)です', description_p.text)
                if match:
                    return_rate = match.group(1).strip()
            
            # 取得した情報が有効な場合のみリストに追加
            if name != "N/A" and code != "N/A":
                extracted_stocks.append(f"{name} ({code}) | 勝率: {win_loss_str} | 期待上昇率: {return_rate}")

        except Exception:
            # カードの解析中にエラーが発生した場合は、そのカードをスキップして次に進む
            continue
            
    if not extracted_stocks:
        return ["★★★ 銘柄データを解析できませんでした ★★★"]

    return extracted_stocks

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

    all_signals_text = []

    for url in urls_to_scrape:
        print(f"\n[INFO] 処理中: {url}")
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            print(f"  [DEBUG] Status Code: {response.status_code}")
            if response.status_code == 200:
                data = extract_data_from_html(response.content)
                
                print("[OK] 取得データ:")
                for item in data:
                    print(f"  - {item}")
                
                # 取得したデータを日付情報とともに追加
                date_part = url.split('/')[-2] + " " + url.split('/')[-1]
                all_signals_text.append(f"--- {date_part} ---\n" + "\n".join(data))
            else:
                print(f"  [WARN] ページ取得に失敗しました。")

        except requests.exceptions.RequestException as e:
            print(f"  [ERROR] 通信エラーが発生しました: {e}")
        except Exception as e:
            print(f"  [ERROR] 不明なエラーが発生しました: {e}")
        
        time.sleep(1)
        
    print(f"\n[INFO] スクレピング完了。データ取得に成功したページ数: {len(all_signals_text)} 件")

    if all_signals_text:
        output_dir = 'output'
        os.makedirs(output_dir, exist_ok=True)
        today_filename_str = today.strftime('%Y%m%d')
        output_filename = f"{today_filename_str}_trade_chance_report.txt"
        output_filepath = os.path.join(output_dir, output_filename)
        
        print(f"\n[INFO] 全ての取得結果をファイルに書き出します: {output_filepath}")
        
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(all_signals_text))
            
        print("[OK] ファイルの保存が完了しました。")

if __name__ == '__main__':
    main()
    print("\n全ての処理が完了しました。")