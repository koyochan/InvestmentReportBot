
import requests
from bs4 import BeautifulSoup
import sys

def scrape_article(url):
    """
    指定されたURLから記事の本文をスクレイピングする。

    Args:
        url (str): スクレイピング対象のURL。

    Returns:
        str: 抽出した記事のテキスト。エラーが発生した場合はNoneを返す。
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # HTTPエラーがあれば例外を発生させる

        soup = BeautifulSoup(response.content, 'html.parser')

        # AVCブログの本文は 'div.post-body' にあると仮定
        # 他のサイトではこのセレクタを調整する必要がある
        article_body = soup.select_one('div.post-body')

        if article_body:
            return article_body.get_text(separator='\n', strip=True)
        else:
            print(f"Warning: Could not find article body in {url}", file=sys.stderr)
            # フォールバックとして<p>タグをすべて取得
            paragraphs = soup.find_all('p')
            return '\n'.join([p.get_text(strip=True) for p in paragraphs])

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return None

if __name__ == '__main__':
    # テスト用のURL (AVCのブログ記事)
    # 将来的にはNewsPicksなどの他のURLにも対応させる
    test_url = "https://avc.com/2024/08/the-new-york-trilogy/"

    print(f"Scraping article from: {test_url}")
    article_text = scrape_article(test_url)

    if article_text:
        print("\n--- Article Text ---")
        print(article_text)
        print("\n--- End of Article ---")
    else:
        print("Failed to scrape the article.")
