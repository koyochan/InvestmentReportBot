import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from grok import Grok

# モジュール検索パスにカレントディレクトリを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# fetcherモジュールをインポート
from fetchers.youtube_fetcher import fetch_youtube_summaries
from fetchers.twitter_fetcher import get_tweets
from fetchers.trade_chance_fetcher import main as fetch_trade_chance
from fetchers.mail_fetcher import get_emails

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

def call_gemini_api(prompt: str) -> str:
    """Gemini APIを呼び出してコンテンツを生成する。"""
    print("\n[AI Process 1/2] Gemini APIに接続し、市場データの要約を生成しています...")
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("エラー: 環境変数 GEMINI_API_KEY が設定されていません。")
            return "エラー: GEMINI_API_KEYがありません。"
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        response = model.generate_content(prompt)
        print("Geminiによる要約の生成が完了しました。")
        return response.text
    except Exception as e:
        print(f"エラー: Gemini APIの呼び出し中にエラーが発生しました: {e}")
        return f"エラー: Gemini APIの呼び出しに失敗しました。詳細: {e}"

def call_grok_api(prompt: str) -> str:
    """Grok APIを呼び出して戦略的洞察を生成する。"""
    print("\n[AI Process 2/2] Grok APIを呼び出し、最終的な投資戦略を生成しています...")
    try:
        api_key = os.getenv("GROK_API_KEY")
        if not api_key:
            print("エラー: 環境変数 GROK_API_KEY が設定されていません。")
            return "エラー: GROK_API_KEYがありません。"

        client = Grok(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="grok-1",
        )
        
        response_text = chat_completion.choices[0].message.content
        print("Grokによる戦略立案が完了しました。")
        return response_text

    except Exception as e:
        print(f"エラー: Grok APIの呼び出し中にエラーが発生しました: {e}")
        return f"エラー: Grok APIの呼び出しに失敗しました。詳細: {e}"


def main():
    """
    データ収集から2段階のAI分析までを実行するメイン関数。
    """
    print("--- データ収集プロセスを開始します ---")
    load_dotenv()
    
    # --- 設定項目 ---
    DAYS_TO_FETCH = 7
    YOUTUBE_URLS = ['https://www.youtube.com/@AC_Investor', 'https://www.youtube.com/@mabuchi-mariko']
    TWITTER_ACCOUNTS = ["elonmusk", "VitalikButerin"]
    MAIL_FROM_EMAIL = os.getenv("MAIL_FROM_EMAIL", "user@example.com")
    MAIL_TO_EMAIL = os.getenv("MAIL_TO_EMAIL", "your-email@example.com")
    
    # --- データ収集の実行 ---
    youtube_report_path = fetch_youtube_summaries(YOUTUBE_URLS, DAYS_TO_FETCH)
    twitter_report_path = get_tweets(TWITTER_ACCOUNTS, DAYS_TO_FETCH)
    fetch_trade_chance(days=DAYS_TO_FETCH)
    today_str = datetime.now().strftime('%Y%m%d')
    trade_chance_report_path = f"output/{today_str}_trade_chance_report_with_prices.txt"
    mail_report_path = get_emails(DAYS_TO_FETCH, MAIL_FROM_EMAIL, MAIL_TO_EMAIL)
    print("\n--- 全てのデータ収集が完了しました ---")

    # --- プロンプトの準備 ---
    youtube_content = read_file_content(youtube_report_path)
    trade_chance_content = read_file_content(trade_chance_report_path)
    mail_content = read_file_content(mail_report_path)
    twitter_content = read_file_content(twitter_report_path)
    
    # --- Geminiによる要約フェーズ ---
    gemini_prompt_template = read_file_content('src/prompt/prompt_gemini.txt')
    gemini_prompt = f"""{gemini_prompt_template}

# 収集データ

## 専門家の解説（YouTube要約）
{youtube_content}

## AIのシグナルデータ（トレードチャンス）
{trade_chance_content}

## 関連メール情報
{mail_content}

## 関連ツイート
{twitter_content}
"""
    briefing_report = call_gemini_api(gemini_prompt)
    
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    briefing_filepath = os.path.join(output_dir, f"{today_str}_gemini_briefing_report.txt")
    with open(briefing_filepath, 'w', encoding='utf-8') as f:
        f.write(briefing_report)
    print(f"Geminiが生成した中間レポートを '{briefing_filepath}' に保存しました。")

    # --- Grokによる戦略立案フェーズ ---
    grok_prompt_template = read_file_content('src/prompt/prompt_grok.txt')
    grok_prompt = f"""{grok_prompt_template}

# ブリーフィング資料

{briefing_report}
"""
    final_strategy_report = call_grok_api(grok_prompt)

    final_report_filepath = os.path.join(output_dir, f"{today_str}_final_investment_strategy.md")
    with open(final_report_filepath, 'w', encoding='utf-8') as f:
        f.write(final_strategy_report)
    print(f"Grokが生成した最終戦略レポートを '{final_report_filepath}' に保存しました。")


if __name__ == '__main__':
    main()
    print("\n--- 全てのプロセスが完了しました ---")
