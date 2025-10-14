import os
import sys
import configparser
from datetime import datetime
from dotenv import load_dotenv

# モジュール検索パスにカレントディレクトリを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# fetcherモジュールをインポート
from fetchers.youtube_fetcher import fetch_youtube_summaries
# from fetchers.twitter_fetcher import get_tweets # Twitter無効化
from fetchers.trade_chance_fetcher import main as fetch_trade_chance
from fetchers.mail_fetcher import get_emails

def load_config(filepath: str) -> configparser.ConfigParser:
    """設定ファイルを読み込む。"""
    config = configparser.ConfigParser()
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"設定ファイルが見つかりません: {filepath}")
    config.read(filepath, encoding='utf-8')
    return config

def read_file_content(filepath: str) -> str:
    """指定されたファイルのコンテンツを読み込んで返す。"""
    if not filepath or not os.path.exists(filepath):
        print(f"警告: ファイルが見つかりません: {filepath}")
        return ""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"エラー: ファイルの読み込み中にエラーが発生しました ({filepath}): {e}")
        return ""

def main():
    """
    すべてのデータソースから情報を収集し、1つのファイルに集約する。
    """
    print("--- データ収集プロセスを開始します ---")
    load_dotenv()
    
    # --- 設定ファイルの読み込み ---
    try:
        config = load_config('src/fetchers/fetcher_config.ini')
        YOUTUBE_URLS = [url.strip() for url in config.get('YouTube', 'urls', fallback='').split(',') if url.strip()]
        MAIL_FROM_EMAIL = config.get('Mail', 'from_email', fallback='user@example.com')
        MAIL_TO_EMAIL = config.get('Mail', 'to_email', fallback='your-email@example.com')
    except Exception as e:
        print(f"エラー: 設定ファイルの読み込みまたは解析に失敗しました: {e}")
        sys.exit(1)

    DAYS_TO_FETCH = 7
    today_str = datetime.now().strftime('%Y%m%d')
    
    # --- データ収集の実行 ---
    print("\n[1/2] YouTubeの要約を取得中...")
    youtube_report_path = fetch_youtube_summaries(YOUTUBE_URLS, DAYS_TO_FETCH)
    if not youtube_report_path:
        print("エラー: YouTubeの要約取得に失敗しました。処理を中断します。")
        sys.exit(1)

    print("\n[2/2] トレードチャンスのシグナルを取得中...")
    fetch_trade_chance(days=DAYS_TO_FETCH)
    trade_chance_report_path = f"output/{today_str}_trade_chance_report_with_prices.txt"
    if not os.path.exists(trade_chance_report_path):
        print(f"エラー: トレードチャンスのレポートファイルの生成に失敗しました。処理を中断します。")
        sys.exit(1)

    # メール取得はオプションとして実行し、失敗しても中断しない
    print("\n[3/3] メールを取得中...")
    mail_report_path = get_emails(DAYS_TO_FETCH, MAIL_FROM_EMAIL, MAIL_TO_EMAIL)
    
    print("\n--- 全てのデータ収集が完了しました ---")

    # --- 収集データの集約 ---
    print("\n収集したデータを1つのファイルにまとめています...")
    youtube_content = read_file_content(youtube_report_path)
    trade_chance_content = read_file_content(trade_chance_report_path)
    mail_content = read_file_content(mail_report_path) if mail_report_path else "（メールデータなし）"
    
    combined_data = f"""
# YouTube専門家の解説
{youtube_content}

# AIのシグナルデータ（トレードチャンス）
{trade_chance_content}

# 関連メール情報
{mail_content}
"""
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    combined_filepath = os.path.join(output_dir, f"{today_str}_collected_data.txt")
    
    with open(combined_filepath, 'w', encoding='utf-8') as f:
        f.write(combined_data.strip())
        
    print(f"\n--- データ集約完了 ---")
    print(f"全ての収集データが '{combined_filepath}' に保存されました。")
    print("\n次に、以下のコマンドを実行してAIによる分析を行ってください:")
    print(f"python3 src/analyze.py {combined_filepath}")

if __name__ == '__main__':
    main()
    print("\n--- データ収集プロセスが完了しました ---")
