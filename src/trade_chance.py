import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import os
import re

def get_historical_price(stock_code, date_str):
    """
    Yahoo!ファイナンスから指定された銘柄コードと日付の終値を取得する。
    Args:
        stock_code (str): 証券コード (例: "7203")
        date_str (str): 日付文字列 (例: "2025-08-18")
    Returns:
        str: 指定日の終値。取得失敗時は "取得失敗" などを返す。
    """
    try:
        # Yahoo Financeの履歴データURLを構築
        formatted_date = date_str.replace('-', '')
        historical_url = f"https://finance.yahoo.co.jp/quote/{stock_code}.T/history?from={formatted_date}&to={formatted_date}&timeFrame=d&page=1"
        
        response = requests.get(historical_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # 履歴データテーブルを探す (クラス名は変更される可能性があるため、部分一致で検索)
        history_table = soup.find('table', class_=re.compile(r"HistoryTable_"))
        if not history_table:
            return "取得失敗(テーブル無)"

        # テーブル内のデータ行を探す
        rows = history_table.find_all('tr')
        # ヘッダー行を除き、データ行をループ
        for row in rows[1:]:
            cols = row.find_all('td')
            if len(cols) > 4: # 少なくとも終値のカラムまで存在するか確認
                # 終値は通常5番目のカラム(インデックス4)
                closing_price = cols[4].text.strip().replace(',', '')
                return closing_price
        
        # ループを抜けてしまった場合は、その日のデータがなかったことを意味する
        return "データ無(休日等)"

    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] Yahoo!履歴データの通信エラー ({stock_code} on {date_str}): {e}")
        return "取得失敗(通信)"
    except Exception as e:
        print(f"  [ERROR] Yahoo!履歴データの解析エラー ({stock_code} on {date_str}): {e}")
        return "取得失敗(不明)"

def get_current_price_and_change(stock_code):
    """
    Yahoo!ファイナンスから指定された銘柄コードの現在の株価と前日比を取得する。
    ページのテキストラベルを基準に情報を探すことで安定性を向上。
    Args:
        stock_code (str): 証券コード（例: "7203"）
    Returns:
        dict: 'price'と'change'のキーを持つ辞書。取得失敗時は値が "取得失敗" となる。
    """
    yahoo_url = f"https://finance.yahoo.co.jp/quote/{stock_code}.T"
    try:
        response = requests.get(yahoo_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        result = {'price': '取得失敗', 'change': '取得失敗'}

        # --- 株価の取得 ---
        price_label = soup.find('dt', string='株価')
        if price_label and price_label.find_next_sibling('dd'):
            price_dd = price_label.find_next_sibling('dd')
            price_span = price_dd.find('span')
            if price_span:
                result['price'] = price_span.text.strip().replace(',', '')

        # --- 前日比の取得 ---
        change_label = soup.find('dt', string='前日比')
        if change_label and change_label.find_next_sibling('dd'):
            change_dd = change_label.find_next_sibling('dd')
            change_span = change_dd.find('span')
            if change_span:
                change_text = ' '.join(change_span.text.strip().split())
                result['change'] = change_text
        
        return result

    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] Yahoo!ファイナンスへの通信エラー ({stock_code}): {e}")
        return {'price': '取得失敗(通信)', 'change': '取得失敗(通信)'}
    except Exception as e:
        print(f"  [ERROR] Yahoo!ファイナンスの解析エラー ({stock_code}): {e}")
        return {'price': '取得失敗(不明)', 'change': '取得失敗(不明)'}


def extract_data_from_html(html_content):
    """
    HTMLコンテンツから「買いシグナル銘柄一覧」の基本データを抽出する。
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    extracted_stocks = []
    stock_cards = soup.find_all('div', class_='trade-chance__stock')
    
    if not stock_cards:
        header = soup.find(['h2', 'h3'], string=re.compile(r'本日の買いシグナル点灯銘柄TOP5'))
        if header:
            list_container = header.find_next_sibling()
            if list_container:
                stock_cards = list_container.find_all('a')
        
    if not stock_cards:
        return ["銘柄リストが見つかりませんでした。"]

    for card in stock_cards:
        try:
            name, code, win_loss_str, return_rate = "N/A", "N/A", "N/A", "N/A"

            name_container = card.find('div', class_='trade-chance__stock-name')
            if name_container:
                name_tag = name_container.find('a')
                code_tag = name_container.find('span')
                if name_tag and code_tag:
                    name = name_tag.text.strip()
                    code_match = re.search(r'(\d+)', code_tag.text)
                    if code_match:
                        code = code_match.group(1)

            signal_graph = card.find('div', class_='signal-graph__texts')
            if signal_graph:
                p_tag = signal_graph.find('p')
                if p_tag:
                    spans = p_tag.find_all('span')
                    if len(spans) >= 2:
                        wins = spans[0].text.strip()
                        losses = spans[1].text.strip()
                        win_loss_str = f"{wins}勝/{losses}敗"

            description_p = card.find('p', class_='trade-chance__stock__signal__description')
            if description_p:
                match = re.search(r'上昇率は(.*?%)です', description_p.text)
                if match:
                    return_rate = match.group(1).strip()
            
            if name != "N/A" and code != "N/A":
                extracted_stocks.append({
                    "name": name, "code": code, "win_loss": win_loss_str,
                    "return_rate": return_rate
                })

        except Exception as e:
            print(f"  [WARN] カードの解析中にエラーが発生しました: {e}")
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
    # 取得日数を3日間に設定
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
    processed_count = 0

    for url in urls_to_scrape:
        print(f"\n[INFO] 処理中: {url}")
        try:
            # URLから日付部分を抽出
            date_part_for_history = url.split('/')[-2]

            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            print(f"  [DEBUG] Status Code: {response.status_code}")
            if response.status_code == 200:
                stocks_data = extract_data_from_html(response.content)
                
                if not stocks_data or isinstance(stocks_data[0], str):
                    print(f"  [WARN] {stocks_data[0] if stocks_data else '銘柄データが空です。'}")
                    continue

                print(f"[OK] {len(stocks_data)}件の銘柄データを検出。株価情報を取得します...")
                
                processed_stocks_lines = []
                for stock in stocks_data:
                    # サーバー負荷軽減のため待機
                    time.sleep(0.5) 
                    
                    # 1. シグナル発生日の終値を取得
                    print(f"  -> {stock['name']} ({stock['code']}) のシグナル日({date_part_for_history})の株価を取得中...")
                    historical_price = get_historical_price(stock['code'], date_part_for_history)
                    
                    # 2. 現在の株価と前日比を取得
                    print(f"  -> {stock['name']} ({stock['code']}) の現在値を取得中...")
                    price_info = get_current_price_and_change(stock['code'])
                    
                    # 出力フォーマットを更新
                    line = (f"{stock['name']} ({stock['code']}) | "
                            f"勝率: {stock['win_loss']} | "
                            f"期待上昇率: {stock['return_rate']} | "
                            f"シグナル日終値: {historical_price}円 | "
                            f"現在の株価: {price_info['price']}円 (前日比: {price_info['change']})")
                    
                    print(f"     [RESULT] {line}")
                    processed_stocks_lines.append(line)
                
                date_part_for_header = url.split('/')[-2] + " " + url.split('/')[-1]
                all_signals_text.append(f"--- {date_part_for_header} ---\n" + "\n".join(processed_stocks_lines))
                processed_count += 1
            else:
                print(f"  [WARN] ページ取得に失敗しました。ステータスコード: {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"  [ERROR] 通信エラーが発生しました: {e}")
        except Exception as e:
            print(f"  [ERROR] 不明なエラーが発生しました: {e}")
        
        time.sleep(1)
        
    print(f"\n[INFO] スクレピング完了。データ取得に成功したページ数: {processed_count} 件")

    if all_signals_text:
        output_dir = 'output'
        os.makedirs(output_dir, exist_ok=True)
        today_filename_str = today.strftime('%Y%m%d')
        output_filename = f"{today_filename_str}_trade_chance_report_with_prices.txt"
        output_filepath = os.path.join(output_dir, output_filename)
        
        print(f"\n[INFO] 全ての取得結果をファイルに書き出します: {output_filepath}")
        
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(all_signals_text))
            
        print("[OK] ファイルの保存が完了しました。")

if __name__ == '__main__':
    main()
    print("\n全ての処理が完了しました。")
