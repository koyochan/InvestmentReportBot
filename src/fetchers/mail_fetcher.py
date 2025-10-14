import imaplib
import email
from email.header import decode_header
import os
from datetime import datetime, timedelta

def get_emails(days: int, from_email: str, to_email: str) -> str:
    """
    指定された日数、送信元、宛先のメールを取得してテキストファイルに保存します。

    Args:
        days (int): 何日前までのメールを取得するか。
        from_email (str): 取得するメールの送信元アドレス。
        to_email (str): 取得するメールの宛先アドレス。

    Returns:
        str: 保存されたファイルのパス。成功した場合はパス、失敗した場合は空文字を返す。
    """
    # 環境変数からメールアカウント情報を取得
    IMAP_SERVER = os.getenv('IMAP_SERVER')
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
    PASSWORD = os.getenv('EMAIL_PASSWORD')

    if not all([IMAP_SERVER, EMAIL_ADDRESS, PASSWORD]):
        print("エラー: 環境変数 IMAP_SERVER, EMAIL_ADDRESS, PASSWORD を設定してください。")
        return ""

    output_path = os.path.join('output', 'mail_report.txt')
    all_email_bodies = []

    try:
        print(f"IMAPサーバー ({IMAP_SERVER}) に接続しています...")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ADDRESS, PASSWORD)
        mail.select('inbox')
        print("IMAPサーバーにログインしました。")

        # 検索条件の日付をフォーマット
        since_date = (datetime.now() - timedelta(days=days)).strftime('%d-%b-%Y')
        search_criteria = f'(SINCE "{since_date}" FROM "{from_email}" TO "{to_email}")'
        
        print(f"検索条件: {search_criteria}")
        status, messages = mail.search(None, search_criteria)
        
        if status != 'OK':
            print("メールの検索に失敗しました。")
            mail.logout()
            return ""

        email_ids = messages[0].split()
        if not email_ids:
            print("指定された条件のメールは見つかりませんでした。")
            mail.logout()
            return ""
        
        print(f"{len(email_ids)}件のメールが見つかりました。内容を取得します...")

        for email_id in reversed(email_ids):
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            if status == 'OK':
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")

                        from_ = msg.get("From")
                        date_ = msg.get("Date")

                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                if content_type == "text/plain":
                                    charset = part.get_content_charset()
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        body = payload.decode(charset if charset else "utf-8", errors='ignore')
                                        break
                        else:
                            if msg.get_content_type() == "text/plain":
                                charset = msg.get_content_charset()
                                payload = msg.get_payload(decode=True)
                                if payload:
                                    body = payload.decode(charset if charset else "utf-8", errors='ignore')
                        
                        if body:
                            email_info = f"--- From: {from_} | Subject: {subject} at {date_} ---\n{body}"
                            all_email_bodies.append(email_info)

        mail.logout()
        print("IMAPサーバーからログアウトしました。")

    except imaplib.IMAP4.error as e:
        print(f"IMAPエラーが発生しました: {e}")
        return ""
    except Exception as e:
        print(f"メールの取得中に予期せぬエラーが発生しました: {e}")
        return ""

    if not all_email_bodies:
        print("メール本文を取得できませんでした。")
        return ""

    os.makedirs('output', exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_email_bodies))

    print(f"取得したメールを {output_path} に保存しました。")
    return output_path

if __name__ == '__main__':
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print(".envファイルから環境変数を読み込みました。")
    except ImportError:
        print("警告: python-dotenvがインストールされていません。.envファイルは読み込まれません。")

    # === 設定項目 ===
    DAYS_TO_FETCH = 7
    # 取得したいメールの送信元と宛先を指定してください
    FROM_EMAIL = "user@example.com"
    TO_EMAIL = "kkobayashi12356@gmail.com"
    # ================
    
    print(f"過去{DAYS_TO_FETCH}日間のメールを取得します (From: {FROM_EMAIL}, To: {TO_EMAIL})")
    get_emails(DAYS_TO_FETCH, FROM_EMAIL, TO_EMAIL)
    print("\n処理が完了しました。")
