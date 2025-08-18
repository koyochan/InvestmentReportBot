import yt_dlp
import json
import re
import os
from datetime import datetime, timedelta
from yt_dlp.postprocessor import PostProcessor

# === ▼▼▼ 修正箇所 ▼▼▼ ===
# AIが読みやすいようにVTTを解析する、より高機能な関数
def parse_vtt(vtt_content):
    """
    WEBVTT形式の文字列から、タイムスタンプやメタデータを削除し、
    AIが読みやすいように重複や部分的な重複を除去した、
    クリーンな文字起こしテキストを抽出します。
    """
    lines = vtt_content.strip().split('\n')
    
    # 1. まず、VTTからテキスト部分だけを抽出し、基本的な掃除をする
    raw_transcript_lines = []
    for line in lines:
        # 不要な行（タイムスタンプ、空行、メタデータなど）をスキップ
        if not line.strip() or '-->' in line or line.strip().isdigit() or line.strip() == 'WEBVTT' or line.strip().startswith('Kind:') or line.strip().startswith('Language:'):
            continue
        
        # HTMLタグ、[音楽]のようなメタデータ、話者マーカーを削除
        cleaned_line = re.sub(r'<[^>]+>', '', line)
        cleaned_line = re.sub(r'\[[^]]+\]', '', cleaned_line)
        cleaned_line = cleaned_line.replace('&gt;&gt;', '').strip()
        cleaned_line = " ".join(cleaned_line.split()) # 連続する空白を1つにまとめる

        if cleaned_line:
            raw_transcript_lines.append(cleaned_line)

    # 2. 重複や部分的な重複を取り除くロジック
    if not raw_transcript_lines:
        return ""
        
    final_transcript = []
    if raw_transcript_lines:
        # 最初の行は無条件で追加
        final_transcript.append(raw_transcript_lines[0])

        for i in range(1, len(raw_transcript_lines)):
            prev_line = final_transcript[-1]
            current_line = raw_transcript_lines[i]
            
            # 全く同じ行ならスキップ
            if current_line == prev_line:
                continue
            
            # 前の行が現在の行に内包されている場合 (例: "A" の次に "A B")
            # 前の行を現在の行で置き換えることで、文章を結合する
            if current_line.startswith(prev_line):
                final_transcript[-1] = current_line
                continue
                
            # 現在の行が前の行に内包されている場合 (例: "A B" の次に "B")
            # これは古い情報なのでスキップ
            if prev_line.endswith(current_line):
                continue

            # 上記のどれにも当てはまらない場合は、新しい発話として追加
            final_transcript.append(current_line)
            
    return " ".join(final_transcript)
# === ▲▲▲ 修正箇所 ▲▲▲ ===


# yt-dlpのダウンロード処理後にVTTをTXTに変換するためのカスタムPostProcessor
class VttToTextPostProcessor(PostProcessor):
    def __init__(self, out_dir):
        super(VttToTextPostProcessor, self).__init__(None)
        self.out_dir = out_dir

    def run(self, info):
        sub_file_path = None
        base_name, _ = os.path.splitext(info['_filename'])
        potential_sub_path = base_name + '.ja.vtt' # yt-dlpが生成する標準的な字幕ファイル名

        if os.path.exists(potential_sub_path):
            sub_file_path = potential_sub_path
        else:
            # フォールバックとしてディレクトリを探索
            for file in os.listdir(self.out_dir):
                if file.startswith(info['id']) and file.endswith('.vtt'):
                    sub_file_path = os.path.join(self.out_dir, file)
                    break
        
        if sub_file_path and os.path.exists(sub_file_path):
            print(f"デバッグ: 字幕ファイルが見つかりました: {sub_file_path}")
            try:
                with open(sub_file_path, 'r', encoding='utf-8') as f:
                    vtt_content = f.read()
                
                transcript_text = parse_vtt(vtt_content)
                
                txt_file_path = os.path.splitext(sub_file_path)[0] + '.txt'
                with open(txt_file_path, 'w', encoding='utf-8') as out_f:
                    out_f.write(transcript_text)
                
                print(f"クリーンな文字起こしを '{txt_file_path}' に保存しました。")
                
                try:
                    os.remove(sub_file_path)
                    print(f"デバッグ: 元のVTTファイルを削除しました: {sub_file_path}")
                except OSError as e:
                    print(f"警告: 元のVTTファイルの削除に失敗しました: {sub_file_path} - {e}")
                
            except Exception as e:
                print(f"エラー: 動画ID: {info['id']} の文字起こし処理中にエラーが発生しました: {e}")
        else:
            print(f"警告: 動画ID: {info['id']} の字幕ファイルが見つかりませんでした。")
            
        return [], info

def get_weekly_video_transcripts(channel_url):
    """
    指定されたYouTubeチャンネルの過去1週間の動画の文字起こしを取得します。
    """
    print("デバッグ: チャンネル情報の取得を開始します...")
    one_week_ago = (datetime.now() - timedelta(days=7)).date()
    
    output_dir = 'transcripts'
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"デバッグ: ディレクトリ '{output_dir}' を作成しました。")
    except OSError as e:
        print(f"エラー: ディレクトリ '{output_dir}' の作成に失敗しました: {e}")
        return

    ydl_opts_info = {
        'playlistend': 20,
        'quiet': True,
        'ignoreerrors': True,
    }
    
    video_urls = []
    
    try:
        videos_url = f"{channel_url.rstrip('/')}/videos"
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            print(f"デバッグ: チャンネルURL '{videos_url}' から最新20件の動画情報を抽出中...")
            info_dict = ydl.extract_info(videos_url, download=False)
            
            if 'entries' in info_dict and info_dict['entries']:
                print("デバッグ: 取得した動画情報を1件ずつ日付でフィルタリングします...")
                for video in info_dict['entries']:
                    if video and 'upload_date' in video:
                        upload_date_str = video['upload_date']
                        upload_date = datetime.strptime(upload_date_str, "%Y%m%d").date()
                        
                        if upload_date >= one_week_ago:
                            video_url = video.get('webpage_url') or f"https://www.youtube.com/watch?v={video['id']}"
                            video_urls.append(video_url)
                            print(f"デバッグ: 動画ID {video['id']} (アップロード日: {upload_date_str}) を対象に追加しました。")
                        else:
                            print(f"デバッグ: 動画ID {video['id']} (アップロード日: {upload_date_str}) は対象外です。")
            
            print(f"デバッグ: {len(video_urls)}件の動画URLを抽出しました。")
    except yt_dlp.utils.DownloadError as e:
        print(f"エラー: チャンネル情報の取得に失敗しました: {e}")
        return
    except Exception as e:
        print(f"予期せぬエラー: チャンネル情報の取得中にエラーが発生しました: {e}")
        return
    
    if not video_urls:
        print("過去1週間に新しい動画はありませんでした。")
        return

    print(f"{len(video_urls)}件の動画が見つかりました。文字起こしを取得します。")
    
    ydl_opts_download = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['ja'],
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'quiet': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
            pp = VttToTextPostProcessor(output_dir)
            ydl.add_post_processor(pp)
            print("デバッグ: 見つかった動画の字幕を一括ダウンロード中...")
            ydl.download(video_urls)
    except Exception as e:
        print(f"エラー: 動画の文字起こし取得中にエラーが発生しました: {e}")

if __name__ == '__main__':
    channel_url = 'https://www.youtube.com/@AC_Investor'
    get_weekly_video_transcripts(channel_url)