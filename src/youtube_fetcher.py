import yt_dlp
import json
import re
import os
from datetime import datetime, timedelta
from yt_dlp.postprocessor import PostProcessor

# VTTファイルを解析してクリーンなテキストを抽出する関数
def parse_vtt(vtt_content):
    """
    WEBVTT形式の文字列から、タイムスタンプやメタデータを削除し、
    純粋な文字起こしテキストを抽出します。
    """
    lines = vtt_content.strip().split('\n')
    transcript_lines = []
    prev_line = ""
    for line in lines:
        # 不要な行（タイムスタンプ、空行、メタデータなど）をスキップ
        if not line.strip() or '-->' in line or line.strip().isdigit() or line.strip() == 'WEBVTT' or line.strip().startswith('Kind:') or line.strip().startswith('Language:'):
            continue
        # HTMLタグや[音楽]のようなメタデータを削除
        cleaned_line = re.sub(r'<[^>]+>', '', line)
        cleaned_line = re.sub(r'\[[^]]+\]', '', cleaned_line)
        cleaned_line = cleaned_line.strip()
        # 連続する同じ行を削除して重複を避ける
        if cleaned_line and cleaned_line != prev_line:
            transcript_lines.append(cleaned_line)
            prev_line = cleaned_line
    return " ".join(transcript_lines)

# yt-dlpのダウンロード処理後にVTTをTXTに変換するためのカスタムPostProcessor
class VttToTextPostProcessor(PostProcessor):
    def __init__(self, out_dir):
        super(VttToTextPostProcessor, self).__init__(None)
        self.out_dir = out_dir

    def run(self, info):
        """
        ダウンロードされた字幕ファイルをテキストに変換し、元のファイルを削除します。
        """
        # ダウンロードされた字幕ファイルのパスを探す
        sub_file_path = None
        for file in os.listdir(self.out_dir):
            if file.startswith(info['id']) and file.endswith('.vtt'):
                sub_file_path = os.path.join(self.out_dir, file)
                break
        
        if sub_file_path and os.path.exists(sub_file_path):
            print(f"デバッグ: 字幕ファイルが見つかりました: {sub_file_path}")
            try:
                # VTTファイルを読み込み、テキストに変換
                with open(sub_file_path, 'r', encoding='utf-8') as f:
                    vtt_content = f.read()
                    transcript_text = parse_vtt(vtt_content)
                
                # 新しい.txtファイルに保存
                txt_file_path = os.path.join(self.out_dir, f"{info['id']}.txt")
                with open(txt_file_path, 'w', encoding='utf-8') as out_f:
                    out_f.write(transcript_text)
                
                print(f"文字起こしを '{txt_file_path}' に保存しました。")
                
                # 処理が完了したら元のVTTファイルを削除
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

    Args:
        channel_url (str): YouTubeチャンネルのURL。
    """
    print("デバッグ: チャンネル情報の取得を開始します...")
    # one_week_ago の計算を修正
    one_week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
    
    output_dir = 'transcripts'
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"デバッグ: ディレクトリ '{output_dir}' を作成しました。")
    except OSError as e:
        print(f"エラー: ディレクトリ '{output_dir}' の作成に失敗しました: {e}")
        return

    # yt-dlpのオプションを設定
    ydl_opts_info = {
        'extract_flat': True,  # プレイリストの高速な情報抽出を有効にする
        'quiet': True,
        'playlist_items': '1:10',
        'force_generic_extractor': True, # エラーを回避するために、汎用的なエクストラクターを使用する
    }

    video_urls = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            print(f"デバッグ: チャンネルURL '{channel_url}' から動画情報を抽出中...")
            info_dict = ydl.extract_info(channel_url, download=False)
            
            if 'entries' in info_dict and info_dict['entries']:
                for video in info_dict['entries']:
                    if video and 'upload_date' in video:
                        # 動画のアップロード日を文字列のまま取得
                        upload_date_str = video['upload_date']
                        
                        # upload_dateの形式がYMDであることを確認
                        if re.match(r'^\d{8}$', upload_date_str):
                            # upload_dateを整数として比較
                            if int(upload_date_str) >= int(one_week_ago):
                                video_urls.append(video['webpage_url'])
            
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
    
    # 実際の一括ダウンロード処理
    ydl_opts_download = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['ja'],
        'outtmpl': os.path.join(output_dir, '%(id)s.sub'),
        'quiet': True,
        'extractor_retries': 'no_impersonation',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
            ydl.add_post_processor(VttToTextPostProcessor(output_dir))
            print("デバッグ: 見つかった動画の字幕を一括ダウンロード中...")
            ydl.download(video_urls)
    except Exception as e:
        print(f"エラー: 動画の文字起こし取得中にエラーが発生しました: {e}")

if __name__ == '__main__':
    channel_url = 'https://www.youtube.com/@AC_Investor'
    get_weekly_video_transcripts(channel_url)
