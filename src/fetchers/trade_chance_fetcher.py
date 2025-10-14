import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import os
import re
import yfinance as yf

def get_technical_indicators(stock_code: str):
    """
    yfinanceを使用して、指定された銘柄の基本的な株価情報を取得する。
    Args:
        stock_code (str): 証券コード (例: "7203")
    Returns:
        dict: 'price', 'change', 'volume' を含む辞書。
              取得失敗時は値が "N/A" となる。
    """
    try:
        # .T をつけて日本の証券取引所を指定
        ticker = yf.Ticker(f"{stock_code}.T")
        # 1年分のデータを取得
        hist = ticker.history(period="1y")

        if hist.empty:
            return {
                'price': 'N/A', 'change': 'N/A', 'macd': 'N/A',
                'rsi': 'N/A', 'volume': 'N/A'
            }

        # pandas-taでの計算をコメントアウト
        # hist.ta.macd(append=True)
        # hist.ta.rsi(append=True)

        # 最新のデータを取得
        latest = hist.iloc[-1]
        price = latest['Close']
        change = price - hist.iloc[-2]['Close']
        volume = latest['Volume']

        return {
            'price': f"{price:.2f}",
            'change': f"{change:+.2f}",
            'macd': "N/A", # pandas-ta を使わないため N/A
            'rsi': "N/A",   # pandas-ta を使わないため N/A
            'volume': f"{volume:,}"
        }

    except Exception as e:
        print(f"  [ERROR] yfinanceでのデータ取得エラー ({stock_code}): {e}")
        return {
            'price': '取得失敗', 'change': '取得失敗', 'macd': '取得失敗',
            'rsi': '取得失敗', 'volume': '取得失敗'
        }

def get_historical_price(stock_code: str, date_str: str):
    """
    yfinanceを使用して、指定された日付の終値を取得する。
    Args:
        stock_code (str): 証券コード
        date_str (str): 日付 (YYYY-MM-DD)
    Returns:
        str: 終値、または "データ無"
    """
    try:
        ticker = yf.Ticker(f"{stock_code}.T")
        # 指定日のデータを取得
        start_date = datetime.strptime(date_str, '%Y-%m-%d')
        end_date = start_date + timedelta(days=1)
        hist = ticker.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
        if not hist.empty:
            return f"{hist.iloc[0]['Close']:.2f}"
        else:
            return "データ無(休日等)"
    except Exception as e:
        print(f"  [ERROR] yfinanceでの過去データ取得エラー ({stock_code} on {date_str}): {e}")
        return "取得失敗"

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
        return ["銘柄リストが見つかりませんでした。" ]

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

def main(days: int = 7):
    """
    メインの処理を実行する関数
    """
    base_url = "https://sbi.alpaca-tech.ai/trade_chance/buy"
    urls_to_scrape = []
    today = datetime.now()

    print("--- 取得対象URLリスト ---")
    # 取得日数を引数で指定できるようにする
    for i in range(days): 
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
            date_part_for_history = url.split('/')[-2]

            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            print(f"  [DEBUG] Status Code: {response.status_code}")
            if response.status_code == 200:
                stocks_data = extract_data_from_html(response.content)
                
                if not stocks_data or isinstance(stocks_data[0], str):
                    print(f"  [WARN] {stocks_data[0] if stocks_data else '銘柄データが空です。'}")
                    continue

                print(f"[OK] {len(stocks_data)}件の銘柄データを検出。株価とテクニカル指標を取得します...")
                
                processed_stocks_lines = []
                for stock in stocks_data:
                    time.sleep(0.5)
                    
                    print(f"  -> {stock['name']} ({stock['code']}) のデータを取得中...")
                    historical_price = get_historical_price(stock['code'], date_part_for_history)
                    tech_indicators = get_technical_indicators(stock['code'])
                    
                    line = (f"{stock['name']} ({stock['code']})\n"
                            f"  勝率: {stock['win_loss']} | 期待上昇率: {stock['return_rate']}\n"
                            f"  シグナル日終値: {historical_price}円\n"
                            f"  現在の株価: {tech_indicators['price']}円 (前日比: {tech_indicators['change']})\n"
                            f"  MACD: {tech_indicators['macd']} | RSI: {tech_indicators['rsi']}\n"
                            f"  出来高: {tech_indicators['volume']}")
                    
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
    # 取得する日数を指定
    DAYS_TO_FETCH = 7
    main(days=DAYS_TO_FETCH)
    print("\n全ての処理が完了しました。")
