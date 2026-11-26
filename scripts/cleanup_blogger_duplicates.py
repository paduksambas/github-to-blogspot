import os
import sys
import json
import re
import urllib.request
import urllib.parse


def get_blogger_token():
    client_id = os.environ.get("BLOGGER_CLIENT_ID")
    client_secret = os.environ.get("BLOGGER_CLIENT_SECRET")
    refresh_token = os.environ.get("BLOGGER_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError("Kredensial OAuth Blogger tidak lengkap.")

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
            raise RuntimeError(f"Gagal refresh access token: {res_json}")
        return access_token


def normalize_title(title):
    t = title.lower()
    t = re.sub(r"[^\w\s]", "", t)
    return " ".join(t.split())


def clean_duplicates():
    print("=" * 60)
    print("🧹 MEMULAI DETEKSI & PEMBERSIHAN DRAF DUPLIKAT DI BLOGGER")
    print("=" * 60)

    blog_id = os.environ.get("BLOGGER_BLOG_ID")
    if not blog_id:
        print("[ERROR] BLOGGER_BLOG_ID tidak ditemukan.")
        sys.exit(1)

    access_token = get_blogger_token()

    # 1. Ambil semua artikel DRAFT
    drafts = []
    page_token = None
    while True:
        url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts?status=DRAFT&maxResults=100"
        if page_token:
            url += f"&pageToken={page_token}"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {access_token}")
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
            items = data.get("items", [])
            drafts.extend(items)
            page_token = data.get("nextPageToken")
            if not page_token or not items:
                break

    print(f"[*] Ditemukan total {len(drafts)} postingan draf di Blogger.")

    # 2. Ambil semua artikel LIVE (Publish) untuk memastikan tidak ada draf yang sudah terbit
    live_posts = []
    page_token = None
    while True:
        url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts?status=LIVE&maxResults=100"
        if page_token:
            url += f"&pageToken={page_token}"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {access_token}")
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
            items = data.get("items", [])
            live_posts.extend(items)
            page_token = data.get("nextPageToken")
            if not page_token or not items:
                break

    print(f"[*] Ditemukan total {len(live_posts)} postingan terbit (LIVE) di Blogger.")

    live_titles = {normalize_title(p.get("title", "")): p for p in live_posts}

    # 3. Kelompokkan Draf berdasarkan Judul
    drafts_grouped = {}
    for d in drafts:
        norm = normalize_title(d.get("title", ""))
        drafts_grouped.setdefault(norm, []).append(d)

    deleted_count = 0

    for norm_title, group in drafts_grouped.items():
        # Kasus A: Jika artikel ini ternyata SUDAH LIVE (terbit)
        if norm_title in live_titles:
            print(f"\n[!] Draf '{group[0].get('title')}' sudah memiliki versi LIVE terbit.")
            # Hapus semua salinan draf karena versi aslinya sudah publish
            for duplicate in group:
                post_id = duplicate["id"]
                del_url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/{post_id}"
                del_req = urllib.request.Request(del_url, method="DELETE")
                del_req.add_header("Authorization", f"Bearer {access_token}")
                try:
                    with urllib.request.urlopen(del_req, timeout=15):
                        print(f"    🗑️ Dihapus draf redundan (sudah live): ID {post_id}")
                        deleted_count += 1
                except Exception as e:
                    print(f"    [!] Gagal menghapus draf ID {post_id}: {e}")
            continue

        # Kasus B: Ada lebih dari 1 draf dengan judul yang sama
        if len(group) > 1:
            print(f"\n[!] Ditemukan {len(group)} salinan draf untuk: '{group[0].get('title')}'")
            # Urutkan berdasarkan waktu update terbaru, simpan 1 yang paling baru
            sorted_group = sorted(group, key=lambda x: x.get("updated", ""), reverse=True)
            keep_item = sorted_group[0]
            to_delete = sorted_group[1:]

            print(f"    ✅ Tetap mempertahankan draf terbaru (ID: {keep_item['id']}, update: {keep_item.get('updated')})")

            for dup in to_delete:
                post_id = dup["id"]
                del_url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/{post_id}"
                del_req = urllib.request.Request(del_url, method="DELETE")
                del_req.add_header("Authorization", f"Bearer {access_token}")
                try:
                    with urllib.request.urlopen(del_req, timeout=15):
                        print(f"    🗑️ Berhasil menghapus draf duplikat: ID {post_id}")
                        deleted_count += 1
                except Exception as e:
                    print(f"    [!] Gagal menghapus ID {post_id}: {e}")

    print("\n" + "=" * 60)
    print(f"🎉 PEMBERSIHAN SELESAI: Berhasil menghapus {deleted_count} draf duplikat.")
    print("=" * 60)


if __name__ == "__main__":
    clean_duplicates()
