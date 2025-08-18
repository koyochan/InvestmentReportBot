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

def get_weekly_video_transcripts(channel_url):
    """
    YouTubeチャンネルから動画の文字起こしを取得し、要約・クリーンアップし、
    外部プロンプトファイルと結合して単一ファイルにまとめる。
    """
    print("デバッグ: チャンネル情報の取得を開始します...")
    one_week_ago = (datetime.now() - timedelta(days=7)).date()
    output_dir = 'transcripts'
    if not os.path.exists(output_dir): os.makedirs(output_dir)

    ydl_opts_info = {'playlistend': 20, 'quiet': True, 'ignoreerrors': True}
    videos_to_process = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info_dict = ydl.extract_info(f"{channel_url.rstrip('/')}/videos", download=False)
            if 'entries' in info_dict and info_dict['entries']:
                for video in info_dict.get('entries', []):
                    if video and 'upload_date' in video and 'title' in video:
                        upload_date = datetime.strptime(video['upload_date'], "%Y%m%d").date()
                        if upload_date >= one_week_ago:
                            videos_to_process.append({
                                'url': video.get('webpage_url') or f"https://www.youtube.com/watch?v={video['id']}",
                                'title': video['title'], 'id': video['id']
                            })
                            print(f"デバッグ: 対象動画が見つかりました: '{video['title']}'")
    except Exception as e:
        print(f"予期せぬエラー: チャンネル情報の取得中にエラーが発生しました: {e}")
        return
    
    if not videos_to_process:
        print("過去1週間に新しい動画はありませんでした。"); return
    
    print(f"\n{len(videos_to_process)}件の動画が見つかりました。字幕をダウンロードします。")

    for video in videos_to_process:
        print(f"デバッグ: '{video['title']}' の字幕をダウンロード中...")
        try:
            output_template = os.path.join(output_dir, '%(title)s.%(ext)s')
            command = ['yt-dlp', '--write-auto-sub', '--sub-lang', 'ja', '--skip-download', '-o', output_template, video['url']]
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"警告: '{video['title']}' の字幕ダウンロードに失敗しました。エラー: {e.stderr}")
        except Exception as e:
            print(f"予期せぬエラー: '{video['title']}' の処理中にエラーが発生しました: {e}")

    all_summaries = []
    print("\nデバッグ: 字幕ファイルの変換・要約・クリーンアップを開始します...")
    
    for filename in os.listdir(output_dir):
        if filename.endswith(".vtt"):
            vtt_path = os.path.join(output_dir, filename)
            video_title = os.path.splitext(filename)[0]
            if video_title.endswith('.ja'): video_title = os.path.splitext(video_title)[0]
            print(f"デバッグ: '{video_title}' を処理中...")
            try:
                with open(vtt_path, 'r', encoding='utf-8') as f:
                    vtt_content = f.read()
                transcript_text = parse_vtt(vtt_content)
                summary_text = summarize_text(transcript_text, sentence_count=25)
                final_text = cleanup_text(summary_text)
                all_summaries.append(final_text)
                print(f"処理完了: '{video_title}' の要約をメモリに追加しました。")
                os.remove(vtt_path)
            except Exception as e:
                print(f"エラー: '{video_title}' の処理中にエラーが発生しました: {e}")

    # === ▼▼▼ 修正箇所 ▼▼▼ ===
    if all_summaries:
        prompt_filename = 'prompt.txt'
        default_prompt_text = """以下のテキストは、複数の投資に関するYouTube動画の文字起こしを要約したものです。
内容の要点を保持しつつ、冗長な表現や会話特有のフィラーワードを削除し、全体を一つの滑らかで一貫性のあるレポートにまとめてください。

---
"""
        # prompt.txtがなければ、デフォルトの内容で自動生成する
        if not os.path.exists(prompt_filename):
            print(f"デバッグ: プロンプトファイル '{prompt_filename}' が見つかりません。デフォルトのプロンプトで作成します。")
            with open(prompt_filename, 'w', encoding='utf-8') as f:
                f.write(default_prompt_text)
        
        # 外部ファイルからプロンプトを読み込む
        with open(prompt_filename, 'r', encoding='utf-8') as f:
            prompt_header = f.read()
            
        today_str = datetime.now().strftime('%Y-%m-%d')
        final_filename = f"prompt_for_ai_{today_str}.txt"
        separator = "\n\n---\n\n"
        summaries_content = separator.join(all_summaries)
        final_content = prompt_header + "\n" + summaries_content
        
        with open(final_filename, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        print(f"\nAIへの指示（プロンプト）を含むファイルを '{final_filename}' に保存しました。")
    # === ▲▲▲ ▲▲▲ ▲▲▲ ===

    print("\n全ての処理が完了しました。")

if __name__ == '__main__':
    channel_url = 'https://www.youtube.com/@AC_Investor'
    get_weekly_video_transcripts(channel_url)