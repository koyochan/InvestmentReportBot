import yt_dlp
import re
import os
import subprocess
from datetime import datetime, timedelta
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

def parse_vtt(vtt_content):
    """
    WEBVTTから重複等を除いたクリーンな文字起こしを生成する。
    """
    lines = vtt_content.strip().split('\n')
    raw_transcript_lines = []
    for line in lines:
        if not line.strip() or '-->' in line or line.strip().isdigit() or 'WEBVTT' in line or 'Kind:' in line or 'Language:' in line:
            continue
        cleaned_line = re.sub(r'<[^>]+>', '', line)
        cleaned_line = re.sub(r'\[[^]]+\]', '', cleaned_line)
        cleaned_line = cleaned_line.replace('&gt;&gt;', '').strip()
        cleaned_line = " ".join(cleaned_line.split())
        if cleaned_line:
            raw_transcript_lines.append(cleaned_line)
    if not raw_transcript_lines: return ""
    final_transcript = [raw_transcript_lines[0]]
    for i in range(1, len(raw_transcript_lines)):
        prev_line, current_line = final_transcript[-1], raw_transcript_lines[i]
        if current_line == prev_line: continue
        if current_line.startswith(prev_line):
            final_transcript[-1] = current_line
            continue
        if prev_line.endswith(current_line): continue
        final_transcript.append(current_line)
    return " ".join(final_transcript)

def summarize_text(text, sentence_count=25):
    """
    テキストを抜粋型要約する。
    """
    if not text: return ""
    parser = PlaintextParser.from_string(text, Tokenizer("japanese"))
    summarizer = TextRankSummarizer()
    summary_sentences = summarizer(parser.document, sentence_count)
    return " ".join([str(sentence) for sentence in summary_sentences])

def cleanup_text(text):
    """
    会話特有のフィラーワードや相づちを、より強力に削除する。
    """
    filler_words = [
        'えーと', 'えーっと', 'えっと', 'えー', 'あのー', 'あの', 
        'まー', 'まあ', 'ま', 'なんか', 'ええと', 'え', 'あ',
        'はい', 'うん', 'ええ', 'はいはい', 'そうですね'
    ]
    pattern = re.compile(r'\b(' + '|'.join(filler_words) + r')\b[、\s]*', re.IGNORECASE)
    cleaned_text = pattern.sub('', text)
    cleaned_text = re.sub(r'\s+([。、,.!?])', r'\1', cleaned_text)
    cleaned_text = " ".join(cleaned_text.split())
    return cleaned_text

def process_source(source_url):
    """
    単一のURL（チャンネル or 再生リスト）を処理し、要約のリストを返す。
    """
    one_week_ago = (datetime.now() - timedelta(days=7)).date()
    # 一時ファイル用のディレクトリ
    transcripts_dir = 'transcripts'
    if not os.path.exists(transcripts_dir): os.makedirs(transcripts_dir)

    if 'list=' in source_url:
        print(f"\n{'='*20}\n再生リストの処理を開始します...\n{'='*20}")
        url_to_fetch = source_url
    else:
        channel_name = source_url.split('@')[-1]
        print(f"\n{'='*20}\nチャンネル '{channel_name}' の処理を開始します...\n{'='*20}")
        url_to_fetch = f"{source_url.rstrip('/')}/videos"

    ydl_opts_info = {'playlistend': 50, 'quiet': True, 'ignoreerrors': True}
    videos_to_process = []
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info_dict = ydl.extract_info(url_to_fetch, download=False)
            if 'entries' in info_dict and info_dict['entries']:
                for video in info_dict.get('entries', []):
                    if not (video and 'upload_date' in video and 'title' in video): continue
                    upload_date = datetime.strptime(video['upload_date'], "%Y%m%d").date()
                    if upload_date >= one_week_ago:
                        videos_to_process.append({
                            'url': video.get('webpage_url') or f"https://www.youtube.com/watch?v={video['id']}",
                            'title': video['title'], 'id': video['id']
                        })
                        print(f"  [+] 対象動画を発見: '{video['title']}'")
    except Exception as e:
        print(f"  [!] 情報の取得中にエラーが発生しました: {e}")
        return []
    
    if not videos_to_process:
        print("  [-] 期間内に処理対象の動画が見つかりませんでした。")
        return []
    
    print(f"\n  [*] {len(videos_to_process)}件の動画が見つかりました。字幕をダウンロードします。")

    for video in videos_to_process:
        print(f"    - ダウンロード中: '{video['title']}'")
        try:
            output_template = os.path.join(transcripts_dir, '%(title)s.%(ext)s')
            command = ['yt-dlp', '--write-auto-sub', '--sub-lang', 'ja', '--skip-download', '-o', output_template, video['url']]
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"    [!] 警告: 字幕ダウンロードに失敗しました。エラー: {e.stderr}")
        except Exception as e:
            print(f"    [!] 予期せぬエラー: {e}")

    summaries = []
    print(f"\n  [*] 字幕ファイルの変換・要約を開始します...")
    processed_titles = {re.sub(r'[\\/*?:"<>|]', "", video['title']): True for video in videos_to_process}
    for filename in os.listdir(transcripts_dir):
        if filename.endswith(".vtt"):
            base_title = os.path.splitext(filename)[0]
            if base_title.endswith('.ja'): base_title = os.path.splitext(base_title)[0]
            if base_title in processed_titles:
                vtt_path = os.path.join(transcripts_dir, filename)
                print(f"    - 処理中: '{base_title}'")
                try:
                    with open(vtt_path, 'r', encoding='utf-8') as f: vtt_content = f.read()
                    transcript_text = parse_vtt(vtt_content)
                    summary_text = summarize_text(transcript_text, sentence_count=25)
                    final_text = cleanup_text(summary_text)
                    summaries.append(final_text)
                    os.remove(vtt_path)
                except Exception as e:
                    print(f"    [!] エラー: '{base_title}' の処理中にエラーが発生しました: {e}")
    return summaries

if __name__ == '__main__':
    source_urls = [
        'https://www.youtube.com/@AC_Investor',
        'https://www.youtube.com/watch?v=5tE_1UbzliI&list=PL-edxQ__zW_VuVcjAhsL_JvlfiZD19LdS',
    ]
    # === ▼▼▼ 修正箇所 ▼▼▼ ===
    # 最終的な出力ファイルを保存するディレクトリを定義
    final_output_dir = 'output'
    if not os.path.exists(final_output_dir):
        os.makedirs(final_output_dir)
    # === ▲▲▲ ▲▲▲ ▲▲▲ ===

    all_summaries = []
    for url in source_urls:
        summaries = process_source(url)
        all_summaries.extend(summaries)

    if all_summaries:
        prompt_filename = 'prompt.txt'
        default_prompt_text = """以下のテキストは、複数の投資に関するYouTube動画の文字起こしを要約したものです。
内容の要点を保持しつつ、冗長な表現や会話特有のフィラーワードを削除し、全体を一つの滑らかで一貫性のあるレポートにまとめてください。

---
"""
        if not os.path.exists(prompt_filename):
            print(f"\n[*] デバッグ: プロンプトファイル '{prompt_filename}' が見つかりません。デフォルトの内容で作成します。")
            with open(prompt_filename, 'w', encoding='utf-8') as f:
                f.write(default_prompt_text)
        
        with open(prompt_filename, 'r', encoding='utf-8') as f:
            prompt_header = f.read()
            
        today_str = datetime.now().strftime('%Y-%m-%d')
        # === ▼▼▼ 修正箇所 ▼▼▼ ===
        # ファイル名とパスを結合して、'output' ディレクトリ内に保存する
        base_filename = f"prompt_for_ai_{today_str}.txt"
        final_filepath = os.path.join(final_output_dir, base_filename)
        # === ▲▲▲ ▲▲▲ ▲▲▲ ===
        
        separator = "\n\n---\n\n"
        summaries_content = separator.join(all_summaries)
        final_content = prompt_header + "\n" + summaries_content
        
        with open(final_filepath, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        # === ▼▼▼ 修正箇所 ▼▼▼ ===
        # 保存先のパスをメッセージに表示
        print(f"\n{'='*20}\n全ての要約を '{final_filepath}' にまとめて保存しました。\n{'='*20}")
    else:
        print("\n[*] 全てのURLで処理対象の動画が見つかりませんでした。")

    print("\n全ての処理が完了しました。")