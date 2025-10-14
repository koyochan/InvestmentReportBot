
import snscrape.modules.twitter as sntwitter
import pandas as pd
from datetime import datetime, timedelta, timezone

def get_last_week_tweets(usernames: list[str]) -> str:
    """
    指定されたTwitterユーザー名のリストから過去1週間のツイートを取得し、
    テキストファイルに保存します。

    Args:
        usernames: Twitterのユーザー名のリスト。

    Returns:
        保存されたファイルのパス。
    """
    all_tweets = []
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=7)

    for username in usernames:
        try:
            # sntwitterを使って特定のユーザーのツイートを取得
            scraper = sntwitter.TwitterUserScraper(username)
            for i, tweet in enumerate(scraper.get_items()):
                if tweet.date < start_date:
                    break
                all_tweets.append([tweet.date, tweet.user.username, tweet.rawContent])
        except Exception as e:
            print(f"Error fetching tweets for {username}: {e}")

    if not all_tweets:
        print("No tweets found in the last week.")
        return ""

    # データフレームを作成してソート
    df = pd.DataFrame(all_tweets, columns=['Date', 'User', 'Tweet'])
    df = df.sort_values(by='Date', ascending=False)

    # ファイルに保存
    output_path = "output/twitter_posts.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        for index, row in df.iterrows():
            f.write(f"--- {row['User']} at {row['Date']} ---
")
            f.write(row['Tweet'])
            f.write("\n\n")

    print(f"Tweets saved to {output_path}")
    return output_path

if __name__ == '__main__':
    # テスト用のTwitterアカウントリスト
    # ここに情報を取得したいアカウントのIDを追加してください
    target_accounts = ["elonmusk", "VitalikButerin"]
    get_last_week_tweets(target_accounts)
