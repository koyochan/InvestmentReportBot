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

def scrape_articles(urls: list[str], days: int = 7):
    """
    URLのリストから記事をスクレイピングし、1つのファイルにまとめる。
    日付の引数(days)は他のfetcherとのインターフェースを合わせるためのもので、
    この関数では使用されません。
    
    Args:
        urls (list[str]): スクレイピング対象のURLリスト。
        days (int): インターフェース統一のための引数（未使用）。

    Returns:
        str: 保存されたファイルのパス。
    """
    all_articles_text = []
    for url in urls:
        print(f"Scraping article from: {url}")
        article_text = scrape_article(url)
        if article_text:
            all_articles_text.append(f"--- Source: {url} ---\n{article_text}")
    
    if not all_articles_text:
        print("No articles were successfully scraped.")
        return ""

    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    today_filename_str = datetime.now().strftime('%Y%m%d')
    output_filename = f"{today_filename_str}_articles_report.txt"
    output_filepath = os.path.join(output_dir, output_filename)

    with open(output_filepath, 'w', encoding='utf-8') as f:
        f.write("\n\n".join(all_articles_text))

    print(f"Scraped articles saved to {output_filepath}")
    return output_filepath

if __name__ == '__main__':
    import os
    from datetime import datetime

    # テスト用のURLリスト
    # 日付でのフィルタリングはサイトの構造に依存するため、ここではURLリストを直接指定
    test_urls = [
        "https://avc.com/2024/08/the-new-york-trilogy/",
        "https://avc.com/2024/08/a-big-new-thing/"
    ]
    
    print(f"Scraping {len(test_urls)} articles...")
    scrape_articles(test_urls)
    print("\nArticle scraping process finished.")
