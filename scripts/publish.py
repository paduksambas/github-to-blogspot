import os
import sys
import glob
import json
import smtplib
import urllib.request
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    import markdown
except ImportError:
    markdown = None

try:
    import frontmatter
except ImportError:
    frontmatter = None


def parse_post(file_path):
    """
    Membaca berkas markdown dan mengekstrak metadata (frontmatter) serta konten HTML.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    title = ""
    labels = []
    status = "LIVE"  # LIVE (publish) atau DRAFT
    description = ""
    body_markdown = raw_text

    # Ekstraksi frontmatter jika library frontmatter tersedia
    if frontmatter:
        post = frontmatter.loads(raw_text)
        metadata = post.metadata
        body_markdown = post.content
        title = metadata.get("title", "")
        labels = metadata.get("labels", [])
        description = metadata.get("description", "")
        if isinstance(labels, str):
            labels = [lbl.strip() for lbl in labels.split(",")]
        raw_status = str(metadata.get("status", "publish")).lower()
        if raw_status == "draft":
            status = "DRAFT"
    else:
        # Fallback manual jika frontmatter lib belum terinstall
        if raw_text.startswith("---"):
            parts = raw_text.split("---", 2)
            if len(parts) >= 3:
                header = parts[1]
                body_markdown = parts[2]
                for line in header.splitlines():
                    if line.startswith("title:"):
                        title = line.replace("title:", "").strip().strip("\"'")
                    elif line.startswith("labels:"):
                        raw_lbls = line.replace("labels:", "").strip().strip("[]")
                        labels = [l.strip().strip("\"'") for l in raw_lbls.split(",") if l.strip()]
                    elif line.startswith("description:"):
                        description = line.replace("description:", "").strip().strip("\"'")

    # Jika deskripsi belum ada, ambil kalimat pertama isi artikel
    if not description:
        plain_text = re.sub(r"<[^>]+>", "", body_markdown).strip()
        first_sentence = plain_text.split(".")[0] if "." in plain_text else plain_text[:140]
        description = first_sentence.replace("\n", " ").strip()[:150]

    # Jika judul belum ada, ambil H1 pertama atau nama file
    if not title:
        for line in body_markdown.splitlines():
            line_str = line.strip()
            if line_str.startswith("# "):
                title = line_str[2:].strip()
                break
    if not title:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        title = base_name.replace("-", " ").replace("_", " ").title()

    # Konversi Markdown ke HTML
    if markdown:
        html_content = markdown.markdown(
            body_markdown,
            extensions=["extra", "codehilite", "toc", "nl2br", "sane_lists"]
        )
    else:
        # Fallback sederhana mengubah baris baru ke <p>/<br>
        html_content = "".join(f"<p>{p.strip()}</p>" for p in body_markdown.split("\n\n") if p.strip())

    return {
        "file_path": file_path,
        "title": title,
        "labels": labels,
        "status": status,
        "description": description,
        "html_content": html_content,
        "raw_markdown": body_markdown
    }


def publish_via_blogger_api(post_data):
    """
    Metode 1: Memposting ke Blogger menggunakan Google Blogger API v3.
    Membutuhkan:
    - BLOGGER_BLOG_ID
    - BLOGGER_CLIENT_ID
    - BLOGGER_CLIENT_SECRET
    - BLOGGER_REFRESH_TOKEN
    """
    blog_id = os.environ.get("BLOGGER_BLOG_ID")
    client_id = os.environ.get("BLOGGER_CLIENT_ID")
    client_secret = os.environ.get("BLOGGER_CLIENT_SECRET")
    refresh_token = os.environ.get("BLOGGER_REFRESH_TOKEN")

    if not all([blog_id, client_id, client_secret, refresh_token]):
        raise ValueError("Konfigurasi Blogger API tidak lengkap (BLOG_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN diperlukan).")

    print(f"[*] Mencoba posting via Blogger API v3 untuk: '{post_data['title']}'...")

    # 1. Dapatkan Access Token baru menggunakan Refresh Token
    token_url = "https://oauth2.googleapis.com/token"
    token_data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }).encode("utf-8")

    req = urllib.request.Request(token_url, data=token_data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req, timeout=30) as resp:
        res_json = json.loads(resp.read().decode("utf-8"))
        access_token = res_json.get("access_token")
        if not access_token:
            raise RuntimeError(f"Gagal mendapatkan access token: {res_json}")

    # 2. Kirim postingan ke Blogger API
    is_draft = "true" if post_data["status"] == "DRAFT" else "false"
    post_url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts?isDraft={is_draft}"

    payload = {
        "kind": "blogger#post",
        "title": post_data["title"],
        "content": post_data["html_content"],
        "labels": post_data["labels"]
    }
    # Tambahkan Deskripsi Penelusuran (Search Description SEO) jika ada
    if post_data.get("description"):
        payload["customMetaData"] = post_data["description"]
        print(f"[*] Menambahkan Deskripsi Penelusuran SEO: '{post_data['description'][:60]}...'")

    payload_bytes = json.dumps(payload).encode("utf-8")

    post_req = urllib.request.Request(post_url, data=payload_bytes, method="POST")
    post_req.add_header("Authorization", f"Bearer {access_token}")
    post_req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(post_req, timeout=30) as resp:
        created_post = json.loads(resp.read().decode("utf-8"))
        url = created_post.get("url", "(URL belum tersedia)")
        print(f" [SUKSES VIA BLOGGER API] Postingan terbit: {url}")
        return True, url


def publish_via_email(post_data):
    """
    Metode 2 (Fallback): Memposting ke Blogspot melalui fitur Mail-to-Blogger.
    Membutuhkan:
    - BLOGGER_SECRET_EMAIL (contoh: user.secretword@blogger.com)
    - SENDER_EMAIL (Gmail Anda)
    - SENDER_APP_PASSWORD (16 digit Google App Password)
    """
    secret_email = os.environ.get("BLOGGER_SECRET_EMAIL")
    sender_email = os.environ.get("SENDER_EMAIL")
    sender_password = os.environ.get("SENDER_APP_PASSWORD")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))

    if not all([secret_email, sender_email, sender_password]):
        raise ValueError("Konfigurasi Mail-to-Blogger tidak lengkap (BLOGGER_SECRET_EMAIL, SENDER_EMAIL, SENDER_APP_PASSWORD diperlukan).")

    print(f"[*] Mencoba posting via Mail-to-Blogger (Email) untuk: '{post_data['title']}'...")

    msg = MIMEMultipart("alternative")
    msg["From"] = sender_email
    msg["To"] = secret_email

    # Format subject dengan label resmi Blogger: Judul Artikel , #Label1 #Label2
    subject_title = post_data["title"]
    labels = post_data.get("labels", [])
    if labels:
        labels_str = " ".join([f"#{lbl.strip()}" for lbl in labels if lbl.strip()])
        msg["Subject"] = f"{subject_title} , {labels_str}"
    else:
        msg["Subject"] = subject_title

    # Tambahkan format HTML
    part_html = MIMEText(post_data["html_content"], "html", "utf-8")
    msg.attach(part_html)

    # Kirim via SMTP TLS
    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, [secret_email], msg.as_string())

    print(f" [SUKSES VIA MAIL-TO-BLOGGER] Email artikel terkirim ke {secret_email}!")
    return True, "Terkirim via Email"


def publish_post(file_path):
    print("\n" + "=" * 60)
    print(f"Memproses berkas: {file_path}")
    post_data = parse_post(file_path)
    print(f"Judul   : {post_data['title']}")
    print(f"Labels  : {post_data['labels']}")
    print(f"Status  : {post_data['status']}")
    print("-" * 60)

    # 1. Coba Metode Utama: Blogger API v3
    api_error = None
    try:
        success, info = publish_via_blogger_api(post_data)
        if success:
            return True
    except Exception as e:
        api_error = e
        print(f"[!] Metode 1 (Blogger API v3) gagal/tidak tersedia: {e}")
        print("[*] Mengalihkan ke Metode 2 (Fallback: Mail-to-Blogger)...")

    # 2. Coba Metode Fallback: Mail-to-Blogger
    email_error = None
    try:
        success, info = publish_via_email(post_data)
        if success:
            return True
    except Exception as e:
        email_error = e
        print(f"[X] Metode 2 (Mail-to-Blogger) juga gagal: {e}")

    # Jika kedua metode gagal
    print("\n[GAGAL] Tidak dapat menerbitkan artikel karena kedua metode gagal:")
    print(f" - Error Blogger API : {api_error}")
    print(f" - Error Email       : {email_error}")
    return False


def main():
    target_file = None
    if len(sys.argv) > 1:
        target_file = sys.argv[1]

    if target_file and os.path.exists(target_file):
        files_to_process = [target_file]
    else:
        # Cari berkas markdown di dalam folder posts/
        files_to_process = glob.glob("posts/**/*.md", recursive=True) + glob.glob("posts/*.md")

    if not files_to_process:
        print("[INFO] Tidak ada berkas markdown yang ditemukan untuk diproses.")
        sys.exit(0)

    print(f"[INFO] Ditemukan {len(files_to_process)} berkas artikel.")

    has_failure = False
    for f in files_to_process:
        success = publish_post(f)
        if not success:
            has_failure = True

    if has_failure:
        sys.exit(1)
    else:
        print("\n🎉 Semua artikel berhasil diproses!")


if __name__ == "__main__":
    main()
