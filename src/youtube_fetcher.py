
import yt_dlp
import json
import re
import os
from datetime import datetime, timedelta

def parse_vtt(vtt_content):
    lines = vtt_content.strip().split('\n')
    transcript_lines = []
    prev_line = ""
    for line in lines:
        if not line.strip() or '-->' in line or line.strip().isdigit() or line.strip() == 'WEBVTT' or line.strip().startswith('Kind:') or line.strip().startswith('Language:'):
            continue
        cleaned_line = re.sub(r'<[^>]+>', '', line)
        cleaned_line = re.sub(r'\[[^]]+\]', '', cleaned_line)
        cleaned_line = cleaned_line.strip()
        if cleaned_line and cleaned_line != prev_line:
            transcript_lines.append(cleaned_line)
            prev_line = cleaned_line
    return " ".join(transcript_lines)

def get_weekly_video_transcripts(channel_url):
    """
    指定されたYouTubeチャンネルの過去1週間の動画の文字起こしを取得します。

    Args:
        channel_url (str): YouTubeチャンネルのURL。
    """
    one_week_ago = datetime.now() - timedelta(days=7)
    date_after = one_week_ago.strftime("%Y%m%d")

    ydl_opts_info = {
        'quiet': True,
        'dateafter': date_after,
    }

    video_ids = []
    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
        try:
            info_dict = ydl.extract_info(channel_url, download=False)
            if 'entries' in info_dict and info_dict['entries']:
                for video in info_dict['entries']:
                    if video:
                        video_ids.append(video['id'])
        except yt_dlp.utils.DownloadError as e:
            print(f"チャンネル情報の取得に失敗しました: {e}")
            return

    if not video_ids:
        print("過去1週間に新しい動画はありませんでした。")
        return

    print(f"{len(video_ids)}件の動画が見つかりました。")

    if not os.path.exists('transcripts'):
        os.makedirs('transcripts')

    for video_id in video_ids:
        print(f"動画ID: {video_id} の文字起こしを取得中...")
        ydl_opts_transcript = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['ja'],
            'outtmpl': f'transcripts/%(id)s.sub',
        }

        with yt_dlp.YoutubeDL(ydl_opts_transcript) as ydl:
            try:
                ydl.download([f'https://www.youtube.com/watch?v={video_id}'])
                try:
                    with open(f'transcripts/{video_id}.sub.ja.vtt', 'r', encoding='utf-8') as f:
                        vtt_content = f.read()
                        transcript_text = parse_vtt(vtt_content)
                        with open(f'transcripts/{video_id}.txt', 'w', encoding='utf-8') as out_f:
                            out_f.write(transcript_text)
                    print(f"文字起こしを 'transcripts/{video_id}.txt' に保存しました。")
                    os.remove(f'transcripts/{video_id}.sub.ja.vtt') # remove the vtt file
                except FileNotFoundError:
                    print(f"動画ID: {video_id} の字幕ファイルが見つかりませんでした。")
            except Exception as e:
                print(f"動画ID: {video_id} の文字起こしの取得中にエラーが発生しました: {e}")

if __name__ == '__main__':
    channel_url = 'https://www.youtube.com/@AC_Investor' # AC_Investor
    get_weekly_video_transcripts(channel_url)
