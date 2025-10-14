import yt_dlp
import re
import os
import subprocess
import time
from datetime import datetime, timedelta
import whisper

def get_channel_videos(channel_url: str, days: int) -> list:
    """
    yt-dlpを使用して、チャンネルの指定された日数以内の動画リストを取得する。
    """
    print(f"チャンネル '{channel_url}' の過去{days}日間の動画リストを取得中...")
    ydl_opts = {
        'playlistend': 50,
        'quiet': True,
        'ignoreerrors': True,
        'extract_flat': False,
    }
    videos = []
    target_date = (datetime.now() - timedelta(days=days)).date()

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(channel_url, download=False)
            if 'entries' in info_dict and info_dict['entries']:
                for video in info_dict.get('entries', []):
                    if not (video and 'id' in video and 'title' in video and 'upload_date' in video):
                        continue
                    
                    upload_date = datetime.strptime(video['upload_date'], "%Y%m%d").date()
                    if upload_date >= target_date:
                        videos.append({'id': video['id'], 'title': video['title'], 'url': video.get('webpage_url') or f"https://www.youtube.com/watch?v={video['id']}"})
                        print(f"  [+] 対象動画を発見: '{video['title']}' ({upload_date})")
    except Exception as e:
        print(f"  [!] 動画リストの取得中にエラーが発生しました: {e}")
    return videos

def fetch_youtube_summaries(source_urls: list[str], days: int) -> str:
    """
    複数のYouTubeのURLから音声をダウンロードし、Whisperで文字起こしを行う。
    """
    all_transcripts = []
    print(f"Fetching YouTube videos from the last {days} days...")

    print("  [*] Whisperモデルをロード中... (初回は時間がかかります)")
    try:
        model = whisper.load_model("small")
        print("  [*] Whisperモデルのロード完了。")
    except Exception as e:
        print(f"  [!] Whisperモデルのロードに失敗しました: {e}")
        return ""

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    audio_dir = os.path.join(project_root, 'transcripts')
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)

    for url in source_urls:
        print(f"\n{'='*20}\n処理を開始します: {url}\n{'='*20}")
        
        if 'list=' in url:
            print("  [*] 再生リストの処理は現在未対応です。スキップします。")
            continue
        else:
            videos_to_process = get_channel_videos(f"{url.rstrip('/')}/videos", days)

        if not videos_to_process:
            print("  [-] 期間内に処理対象の動画が見つかりませんでした。")
            continue

        print(f"\n  [*] {len(videos_to_process)}件の動画の音声をダウンロードし、文字起こしします.")

        for video in videos_to_process:
                            audio_path = None
                            try:
                                print(f"\n    - 音声ダウンロード中: '{video['title']}'")
                                output_template = os.path.join(audio_dir, f"{video['id']}.%(ext)s")
                                command = ['yt-dlp', '-x', '--audio-format', 'm4a', '-o', output_template, video['url']]
                                
                                result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
                                
                                audio_path_search = re.search(r'\[ExtractAudio\] Destination: (.*)', result.stdout)
                                if audio_path_search:
                                    audio_path = audio_path_search.group(1).strip()
                                else:
                                    potential_path = os.path.join(audio_dir, f"{video['id']}.m4a")
                                    if os.path.exists(potential_path):
                                        audio_path = potential_path
                                    else:
                                        print(f"    [!] 警告: ダウンロードされた音声ファイルが見つかりません。スキップします。")
                                        continue
                    
                                print(f"    - 音声ダウンロード完了: {os.path.basename(audio_path)}")
                                
                                print(f"    - 文字起こし中 (Whisper)...")
                                transcription_result = model.transcribe(audio_path, language="en")
                                transcript_text = transcription_result['text']
                                
                                if transcript_text:
                                    all_transcripts.append(f"--- {video['title']} ---\n{transcript_text}")
                                    print(f"    - 文字起こし完了。")
                                else:
                                    print(f"    [!] 警告: 文字起こし結果が空でした。")
                    
                            except subprocess.CalledProcessError as e:
                                print(f"    [!] 警告: 音声ダウンロードに失敗しました。 stderr: {e.stderr}")
                            except Exception as e:
                                print(f"    [!] 予期せぬエラーが発生しました: {e}")
                            finally:
                                if audio_path and os.path.exists(audio_path):
                                    os.remove(audio_path)
                                    print(f"    - クリーンアップ完了: {os.path.basename(audio_path)}")
                            
                            print("    ... 5秒待機 ...")
                            time.sleep(5)
    if not all_transcripts:
        print("\n[*] 警告: どの動画からも文字起こしを生成できませんでした。")
        return ""

    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'output')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    today_str = datetime.now().strftime('%Y%m%d')
    base_filename = f"{today_str}_youtube_report.txt"
    final_filepath = os.path.join(output_dir, base_filename)
    
    separator = "\n\n"
    content = separator.join(all_transcripts)
    
    with open(final_filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n{'='*20}\nAll transcripts saved to '{final_filepath}'.\n{'='*20}")
    return final_filepath

if __name__ == '__main__':
    test_source_urls = [
        'https://www.youtube.com/@AC_Investor',
        'https://www.youtube.com/@mabuchi-mariko/'
    ]
    DAYS_TO_FETCH = 7
    fetch_youtube_summaries(test_source_urls, DAYS_TO_FETCH)
    print("\nYouTube fetching process finished.")