import sys
import os
from datetime import datetime
from dotenv import load_dotenv
from xai_sdk import Client
from xai_sdk.chat import user, system

def read_file_content(filepath: str) -> str:
    """指定されたファイルのコンテンツを読み込んで返す。"""
    if not os.path.exists(filepath):
        print(f"エラー: 入力ファイルが見つかりません: {filepath}")
        sys.exit(1)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"エラー: ファイルの読み込み中にエラーが発生しました ({filepath}): {e}")
        sys.exit(1)

def call_grok_api(prompt: str) -> str:
    """xai-sdkを使用してGrok APIを呼び出す。"""
    print("\n[AI Process] Grok APIを呼び出し、最終的な投資戦略を生成しています...")
    try:
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            raise ValueError("環境変数 XAI_API_KEY が設定されていません。")

        client = Client(api_key=api_key)
        
        chat = client.chat.create(model="grok-4")
        chat.append(user(prompt))

        response = chat.sample()
        print("Grokによる戦略立案が完了しました。")
        return response.content
    except Exception as e:
        print(f"エラー: Grok APIの呼び出し中にエラーが発生しました: {e}")
        sys.exit(1)

def analyze_with_grok(briefing_filepath: str):
    """
    指定されたGeminiの要約レポートを使って、Grokによる分析を実行する。
    """
    print(f"--- Grok分析プロセスを開始します ---")
    print(f"入力ファイル (Gemini要約レポート): {briefing_filepath}")
    load_dotenv()

    # --- データとプロンプトの読み込み ---
    briefing_report = read_file_content(briefing_filepath)
    grok_prompt_template = read_file_content('src/prompt/prompt_grok.txt')

    if not (briefing_report and grok_prompt_template):
        print("エラー: 入力ファイルまたはプロンプトファイルが見つかりません。")
        sys.exit(1)

    # --- Grokによる戦略立案フェーズ ---
    grok_prompt = f"{grok_prompt_template}\n\n# ブリーフィング資料\n{briefing_report}"
    final_strategy_report = call_grok_api(grok_prompt)

    today_str = datetime.now().strftime('%Y%m%d')
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    final_report_filepath = os.path.join(output_dir, f"{today_str}_final_investment_strategy.md")
    with open(final_report_filepath, 'w', encoding='utf-8') as f:
        f.write(final_strategy_report)
    print(f"Grokが生成した最終戦略レポートを '{final_report_filepath}' に保存しました。")
    
    print("\n--- 最終レポート ---")
    print(final_strategy_report)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("エラー: 分析対象のGeminiレポートファイルパスを引数として指定してください。")
        print("使用法: python3 src/analyze.py <Geminiレポートのファイルパス>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    analyze_with_grok(input_file)
    print("\n--- 全ての分析プロセスが完了しました ---")
