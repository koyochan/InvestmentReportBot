import yt_dlp
import json

import re

def parse_vtt(vtt_content):
    lines = vtt_content.strip().split('\n')
    transcript_lines = []
    prev_line = ""
    for line in lines:
        if not line.strip() or '-->' in line or line.strip().isdigit() or line.strip() == 'WEBVTT' or line.strip() == 'Kind: captions' or line.strip().startswith('Language:'):
            continue
        cleaned_line = re.sub(r'<[^>]+>', '', line)
        cleaned_line = re.sub(r'\[[^\]]+\]', '', cleaned_line)
        cleaned_line = cleaned_line.strip()
        if cleaned_line and cleaned_line != prev_line:
            transcript_lines.append(cleaned_line)
            prev_line = cleaned_line
    return " ".join(transcript_lines)

def get_latest_video_transcript(channel_url):
    """
    指定されたYouTubeチャンネルの最新動画の文字起こしを取得します。

    Args:
        channel_url (str): YouTubeチャンネルのURL。

    Returns:
        str: 最新動画の文字起こしテキスト。文字起こしが見つからない場合はNone。
    """
    ydl_opts_info = {
        'playlistend': 1,
        'quiet': True,
    }

    video_id = None
    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
        try:
            info_dict = ydl.extract_info(channel_url, download=False)
            # print(json.dumps(info_dict, indent=4)) # デバッグ用にinfo_dictの内容を出力
            if 'entries' in info_dict and info_dict['entries'] and 'entries' in info_dict['entries'][0] and info_dict['entries'][0]['entries']:
                video_id = info_dict['entries'][0]['entries'][0]['id']
        except yt_dlp.utils.DownloadError as e:
            print(f"チャンネル情報の取得に失敗しました: {e}")
            return None

    if not video_id:
        print("最新の動画が見つかりませんでした。")
        return None

    print(f"最新の動画ID: {video_id}")

    ydl_opts_transcript = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['ja'], # 日本語の字幕を優先
        'outtmpl': f'%(id)s.sub',
    }

    transcript_text = None
    with yt_dlp.YoutubeDL(ydl_opts_transcript) as ydl:
        try:
            ydl.download([f'https://www.youtube.com/watch?v={video_id}'])
            # ダウンロードされた字幕ファイルを読む
            try:
                with open(f'{video_id}.sub.ja.vtt', 'r', encoding='utf-8') as f:
                    vtt_content = f.read()
                    transcript_text = parse_vtt(vtt_content)
            except FileNotFoundError:
                print("字幕ファイルが見つかりませんでした。")

        except Exception as e:
            print(f"文字起こしの取得中にエラーが発生しました: {e}")

    return transcript_text


if __name__ == '__main__':
    # AC_InvestorチャンネルのURL
    # 注: @AC_Investor のチャンネルURLは "https://www.youtube.com/c/ACInvestor" または "https://www.youtube.com/channel/UC_p7_Q_s_t-iJ2g_xR2-8iA" のような形式になります。
    # 正しいURLを指定する必要があります。ここではサンプルとして後者を使います。
    channel_url = 'https://www.youtube.com/@AC_Investor' # AC_Investor
    transcript = get_latest_video_transcript(channel_url)

    if transcript:
        with open('ac_investor_transcript.txt', 'w', encoding='utf-8') as f:
            f.write(transcript)
        print("文字起こしを 'ac_investor_transcript.txt' に保存しました。")