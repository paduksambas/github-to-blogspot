#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Paduka Sambas - Scheduled Draft Publisher
=========================================
1. Memindai draf artikel di posts/*.md secara FIFO.
2. Mempublikasikan draf terpilih ke Blogger (Live via Blogger API v3).
3. Memperbarui status frontmatter berkas markdown menjadi 'publish'.
4. Membuat Master News Card 4:5 PNG & caption Zero-Link.
5. Mengunggah postingan otomatis ke Halaman Facebook Paduka Sambas.
6. Mengirim laporan instan ke Telegram Bot Redaksi (@padukasambas_bot).
7. Memperbarui published_history.json.
"""

import os
import sys
import re
import glob
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

# Import helper modul internal
try:
    from scripts.generate_facebook_post import (
        generate_facebook_news_card,
        generate_facebook_caption,
        publish_to_facebook
    )
except ImportError:
    try:
        from generate_facebook_post import (
            generate_facebook_news_card,
            generate_facebook_caption,
            publish_to_facebook
        )
    except ImportError:
        generate_facebook_news_card = None
        generate_facebook_caption = None
        publish_to_facebook = None

try:
    import markdown
except ImportError:
    markdown = None

try:
    import frontmatter
except ImportError:
    frontmatter = None


def get_wib_now():
    """Mengembalikan waktu saat ini dalam format WIB (UTC+7)."""
    wib_tz = timezone(timedelta(hours=7))
    return datetime.now(wib_tz).strftime("%Y-%m-%d %H:%M:%S")


def parse_post_file(file_path):
    """Membaca file markdown dan mengekstrak metadata serta isi HTML."""
    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    title = ""
    labels = []
    status = "publish"
    description = ""
    thumbnail = ""
    body_markdown = raw_text

    if frontmatter:
        try:
            post = frontmatter.loads(raw_text)
            metadata = post.metadata
            body_markdown = post.content
            title = metadata.get("title", "")
            labels = metadata.get("labels", [])
            description = metadata.get("description", "")
            status = str(metadata.get("status", "publish")).lower()
            thumbnail = metadata.get("thumbnail", "")
        except Exception:
            pass

    if not title:
        # Fallback regex / manual
        if raw_text.startswith("---"):
            parts = raw_text.split("---", 2)
            if len(parts) >= 3:
                header = parts[1]
                body_markdown = parts[2]
                for line in header.splitlines():
                    line_s = line.strip()
                    if line_s.startswith("title:"):
                        title = line_s.replace("title:", "").strip().strip("\"'")
                    elif line_s.startswith("labels:"):
                        raw_l = line_s.replace("labels:", "").strip().strip("[]")
                        labels = [lbl.strip().strip("\"'") for lbl in raw_l.split(",") if lbl.strip()]
                    elif line_s.startswith("description:"):
                        description = line_s.replace("description:", "").strip().strip("\"'")
                    elif line_s.startswith("status:"):
                        status = line_s.replace("status:", "").strip().strip("\"'").lower()
                    elif line_s.startswith("thumbnail:"):
                        thumbnail = line_s.replace("thumbnail:", "").strip().strip("\"'")

    if isinstance(labels, str):
        labels = [lbl.strip() for lbl in labels.split(",") if lbl.strip()]

    if not title:
        for line in body_markdown.splitlines():
            ls = line.strip()
            if ls.startswith("# "):
                title = ls[2:].strip()
                break
    if not title:
        title = os.path.splitext(os.path.basename(file_path))[0].replace("-", " ").title()

    if not description:
        plain = re.sub(r"<[^>]+>", "", body_markdown).strip()
        first_sentence = plain.split(".")[0] if "." in plain else plain[:140]
        description = first_sentence.replace("\n", " ").strip()[:150]

    if markdown:
        html_content = markdown.markdown(
            body_markdown,
            extensions=["extra", "codehilite", "toc", "nl2br", "sane_lists"]
        )
    else:
        html_content = "".join(f"<p>{p.strip()}</p>" for p in body_markdown.split("\n\n") if p.strip())

    return {
        "file_path": file_path,
        "title": title,
        "labels": labels,
        "status": status,
        "description": description,
        "thumbnail": thumbnail,
        "raw_markdown": body_markdown,
        "html_content": html_content
    }


def find_draft_posts():
    """Mencari semua berkas draf di posts/*.md, diurutkan FIFO (paling lama lebih dahulu)."""
    all_files = sorted(glob.glob("posts/*.md"))
    drafts = []
    for fp in all_files:
        fn = os.path.basename(fp)
        if "contoh" in fn.lower():
            continue
        data = parse_post_file(fp)
        if data["status"] == "draft":
            # Urutkan berdasarkan tanggal modifikasi file atau nama
            mtime = os.path.getmtime(fp)
            drafts.append((mtime, fp, data))

    # Urutkan secara FIFO (mtime paling lama duluan)
    drafts.sort(key=lambda x: (x[0], x[1]))
    return [d[2] for d in drafts]


def get_blogger_access_token():
    """Mendapatkan OAuth access token Blogger API v3."""
    client_id = os.environ.get("BLOGGER_CLIENT_ID")
    client_secret = os.environ.get("BLOGGER_CLIENT_SECRET")
    refresh_token = os.environ.get("BLOGGER_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError("Kredensial Blogger API tidak lengkap (BLOGGER_CLIENT_ID, BLOGGER_CLIENT_SECRET, BLOGGER_REFRESH_TOKEN).")

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
        token = res_json.get("access_token")
        if not token:
            raise RuntimeError(f"Gagal mendapatkan Blogger access token: {res_json}")
        return token


def publish_post_to_blogger(post_data):
    """
    Mempublikasikan artikel ke Blogger API v3:
    1. Cek apakah ada post (DRAFT/LIVE) dengan judul yang sama.
    2. Jika ada di DRAFT: update isinya via PUT, lalu publish via POST /publish.
    3. Jika belum ada: terbitkan langsung via POST /posts?isDraft=false.
    """
    blog_id = os.environ.get("BLOGGER_BLOG_ID")
    if not blog_id:
        raise ValueError("BLOGGER_BLOG_ID belum disetel di environment.")

    access_token = get_blogger_access_token()

    def normalize(text):
        t = text.lower()
        t = re.sub(r"[^\w\s]", "", t)
        return " ".join(t.split())

    target_norm = normalize(post_data["title"])
    existing_post_id = None
    existing_status = None
    existing_url = None

    print(f"[*] Mencari status artikel di Blogger untuk: '{post_data['title']}'...")
    for st in ["DRAFT", "LIVE"]:
        try:
            list_url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts?status={st}&maxResults=100"
            req = urllib.request.Request(list_url)
            req.add_header("Authorization", f"Bearer {access_token}")
            with urllib.request.urlopen(req, timeout=20) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                for item in res_data.get("items", []):
                    item_norm = normalize(item.get("title", ""))
                    if item_norm == target_norm or (len(item_norm) > 20 and (item_norm in target_norm or target_norm in item_norm)):
                        existing_post_id = item.get("id")
                        existing_status = st
                        existing_url = item.get("url")
                        print(f"[+] Ditemukan di Blogger: ID={existing_post_id}, Status={existing_status}")
                        break
        except Exception as e:
            print(f"[!] Info cek Blogger ({st}): {e}")
        if existing_post_id:
            break

    payload = {
        "kind": "blogger#post",
        "title": post_data["title"],
        "content": post_data["html_content"],
        "labels": post_data["labels"]
    }
    if post_data.get("description"):
        payload["customMetaData"] = post_data["description"]

    payload_bytes = json.dumps(payload).encode("utf-8")

    if existing_post_id:
        # Perbarui data artikel via PUT
        print(f"[*] Memperbarui data artikel Blogger ID: {existing_post_id}...")
        put_url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/{existing_post_id}"
        put_req = urllib.request.Request(put_url, data=payload_bytes, method="PUT")
        put_req.add_header("Authorization", f"Bearer {access_token}")
        put_req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(put_req, timeout=30) as p_resp:
                updated_item = json.loads(p_resp.read().decode("utf-8"))
                existing_url = updated_item.get("url", existing_url)
        except Exception as e:
            print(f"[!] Peringatan saat PUT artikel: {e}")

        # Jika sebelumnya DRAFT, ubah menjadi LIVE menggunakan endpoint publish resmi
        if existing_status == "DRAFT":
            print(f"[*] Mempublikasikan Draf ID {existing_post_id} menjadi LIVE...")
            pub_url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/{existing_post_id}/publish"
            pub_req = urllib.request.Request(pub_url, data=b"", method="POST")
            pub_req.add_header("Authorization", f"Bearer {access_token}")
            with urllib.request.urlopen(pub_req, timeout=30) as pub_resp:
                pub_data = json.loads(pub_resp.read().decode("utf-8"))
                live_url = pub_data.get("url") or existing_url or f"https://padukasambas.blogspot.com/"
                print(f"[+] Draf resmi beralih status ke LIVE: {live_url}")
                return live_url
        else:
            print(f"[+] Artikel sudah berstatus LIVE sebelumnya: {existing_url}")
            return existing_url or f"https://padukasambas.blogspot.com/"

    else:
        # Buat artikel baru langsung LIVE
        print(f"[*] Artikel belum ada di Blogger. Menerbitkan baru secara LIVE...")
        create_url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts?isDraft=false"
        c_req = urllib.request.Request(create_url, data=payload_bytes, method="POST")
        c_req.add_header("Authorization", f"Bearer {access_token}")
        c_req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(c_req, timeout=30) as c_resp:
            c_data = json.loads(c_resp.read().decode("utf-8"))
            live_url = c_data.get("url") or f"https://padukasambas.blogspot.com/"
            print(f"[+] Artikel baru sukses diterbitkan LIVE: {live_url}")
            return live_url


def update_markdown_status_to_publish(file_path, live_url=None):
    """Memperbarui frontmatter berkas markdown dari 'draft' ke 'publish'."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Ganti status: "draft" atau status: draft
    new_content = re.sub(
        r'status:\s*["\']?draft["\']?',
        'status: "publish"',
        content,
        flags=re.IGNORECASE
    )

    # Tambahkan atau perbarui blogger_url jika ada
    if live_url and "blogger_url:" not in new_content:
        new_content = re.sub(
            r'(status:\s*["\']?publish["\']?)',
            r'\1\nblogger_url: "' + live_url + '"',
            new_content
        )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"[+] Berkas {file_path} berhasil diperbarui statusnya ke 'publish'.")


def extract_facebook_card_data(post_data, gemini_api_key=None):
    """
    Mengekstrak data terstruktur untuk Master News Card 4:5 dan caption Zero-Link.
    Menggunakan Gemini API jika tersedia, dengan fallback heuristik cerdas.
    """
    title = post_data["title"]
    labels = post_data["labels"]
    desc = post_data["description"]
    thumbnail = post_data["thumbnail"]
    category = labels[0] if labels else "INFO SAMBAS"
    raw_md = post_data["raw_markdown"]

    # Coba gunakan Gemini API jika key tersedia
    if gemini_api_key:
        try:
            print("[*] Mengekstrak format visual Facebook menggunakan AI Gemini...")
            prompt = f"""Kamu adalah Editor Visual Berita Paduka Sambas.
Tugasmu adalah mengekstrak data dari artikel berita berikut ke dalam format JSON untuk kartu berita visual 4:5 dan caption Facebook Zero-Link.

Judul: {title}
Kategori: {category}
Deskripsi: {desc}
Isi Artikel:
{raw_md[:2500]}

Aturan JSON:
- is_data_mode: boolean (true jika berita dominan data statistik/angka/persen, false jika peristiwa/kebijakan)
- badge_gold: 1-2 kata huruf kapital (contoh: INFRASTRUKTUR, HUKUM & ETIK, EKONOMI, PEMKAB SAMBAS)
- kicker: 3-5 kata huruf kapital penjelas konteks (contoh: RESPON CEPAT KELUHAN WARGA, BABAK BARU PROSES HUKUM)
- headline_line1: Baris 1 judul pada kartu (maksimal 28 karakter)
- headline_line2_prefix: Awalan baris 2 (contoh: "Resmi ", "Capai ", "Kini ")
- keyword_highlight: 1-2 kata kunci utama huruf kapital warna emas (contoh: "DITAHAN POLISI", "3,92%", "MULAI DIKERJAKAN")
- box1_title: Judul kotak 1 (2-3 kata kapital)
- box1_body: Isi kotak 1 (ringkas, padat)
- box2_title: Judul kotak 2 (2-3 kata kapital)
- box2_body: Isi kotak 2 (ringkas, padat)
- subtext: 1 kalimat penjelas ringkas di bawah kotak (maksimal 80 karakter)
- source_credit: Sumber berita / foto (contoh: Redaksi Paduka Sambas, Humas Pemda)
- lead: Paragraf pembuka 5W+1H tuntas untuk caption
- body: Paragraf kedua pendalaman konteks
- impact: Paragraf ketiga dampak dan tindak lanjut
- discussion_prompt: Pertanyaan santun pemantik diskusi warga untuk kolom komentar
- hashtags: array 5 tagar (contoh: ["PadukaSambas", "KabarSambas", "SambasTerkini", "HukumKalbar", "KalbarHariIni"])

Hanya kirimkan blok kode JSON tanpa komentar lain."""

            candidate_models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
            for model in candidate_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.2, "response_mime_type": "application/json"}
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                try:
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        res = json.loads(resp.read().decode("utf-8"))
                        text_resp = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                        card_data = json.loads(text_resp)
                        card_data["photo_url"] = thumbnail
                        card_data["title"] = title
                        card_data["badge_red"] = "PADUKA SAMBAS"
                        print("[+] Ekstraksi AI Gemini untuk News Card Facebook berhasil!")
                        return card_data
                except Exception as e:
                    print(f"[!] Model {model} gagal atau rate limit: {e}")
        except Exception as e:
            print(f"[!] Gagal ekstraksi via AI, beralih ke Fallback Heuristik: {e}")

    # Fallback Heuristik Cerdas
    words = title.split()
    mid = len(words) // 2
    hl1 = " ".join(words[:mid])
    hl2_words = words[mid:]
    kw = hl2_words[-1].upper() if hl2_words else "TERKINI"
    hl2_p = " ".join(hl2_words[:-1]) + " " if len(hl2_words) > 1 else ""

    paragraphs = [p.strip() for p in raw_md.split("\n\n") if p.strip() and not p.strip().startswith("#") and not p.strip().startswith("<p")]
    lead = paragraphs[0] if len(paragraphs) > 0 else desc
    lead = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", lead)
    body = paragraphs[1] if len(paragraphs) > 1 else desc
    body = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", body)
    impact = paragraphs[2] if len(paragraphs) > 2 else "Langkah tindak lanjut dan pengawasan terus dilakukan oleh pihak berwenang guna memastikan penyelesaian berjalan optimal bagi masyarakat."
    impact = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", impact)

    return {
        "is_data_mode": False,
        "photo_url": thumbnail,
        "badge_red": "PADUKA SAMBAS",
        "badge_gold": category.upper(),
        "kicker": "KABAR TERKINI DAERAH",
        "headline_line1": hl1[:28],
        "headline_line2_prefix": hl2_p[:15],
        "keyword_highlight": kw[:20],
        "box1_title": "STATUS PERKARA",
        "box1_body": "Proses Berjalan",
        "box2_title": "FOKUS PUBLIK",
        "box2_body": "Kawal Bersama",
        "subtext": desc[:75] + ("..." if len(desc) > 75 else ""),
        "source_credit": "Redaksi Paduka Sambas",
        "title": title,
        "lead": lead,
        "body": body,
        "impact": impact,
        "discussion_prompt": "Bagaimana pandangan Anda mengenai perkembangan kabar ini? Sampaikan pendapat Anda di kolom komentar!",
        "hashtags": ["PadukaSambas", f"Kabar{category.replace(' ', '')}", "SambasTerkini", "KalbarHariIni"]
    }


def send_telegram_publication_alert(post_data, live_url, fb_success=False):
    """Mengirim pesan konfirmasi publikasi ke Telegram Bot Redaksi."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[!] TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID belum disetel.")
        return

    wib_now = get_wib_now()
    category = post_data["labels"][0] if post_data["labels"] else "Berita"
    fb_status_text = " Terbit di Halaman Facebook (Zero-Link Card)" if fb_success else " Belum diterbitkan ke Facebook"

    msg = f""" *ARTIKEL RESMI DIPUBLIKASIKAN!*

📌 *Judul:* {post_data['title']}
🏷️ *Kategori:* {category}
⏰ *Waktu Terbit:* {wib_now} WIB
🌐 *Blogger Live:* [Baca Artikel]({live_url})
📱 *Facebook Page:* {fb_status_text}

_Sistem penjadwalan otomatis Paduka Sambas telah sukses menayangkan berita ke publik!_"""

    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=urllib.parse.urlencode({
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "Markdown",
                "disable_web_page_preview": "false"
            }).encode("utf-8")
        )
        with urllib.request.urlopen(req, timeout=15):
            print("[+] Konfirmasi publikasi sukses terkirim ke Telegram Redaksi!")
    except Exception as e:
        print(f"[!] Gagal mengirim pesan ke Telegram: {e}")


def update_published_history(post_data, live_url):
    """Menyimpan catatan riwayat publikasi ke published_history.json."""
    history_file = "published_history.json"
    history = {}
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = {}

    title_key = post_data["title"].lower().strip()
    history[title_key] = {
        "published_at": get_wib_now(),
        "title": post_data["title"],
        "file": post_data["file_path"],
        "blogger_url": live_url,
        "labels": post_data["labels"]
    }

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    print(f"[+] Riwayat publikasi diperbarui di {history_file}.")


def run_scheduled_publishing(target_file=None, limit=1, skip_fb=False, skip_telegram=False, dry_run=False):
    """
    Eksekutor utama penerbitan terjadwal.
    """
    print("\n" + "=" * 65)
    print(f"⏰ PADUKA SAMBAS - RUN SCHEDULED PUBLISHER ({get_wib_now()} WIB)")
    print("=" * 65)

    if target_file and os.path.exists(target_file):
        target_posts = [parse_post_file(target_file)]
    else:
        drafts = find_draft_posts()
        if not drafts:
            print("[INFO] Tidak ada artikel berstatus 'draft' yang ditemukan di posts/*.md.")
            print("Semua artikel sudah berstatus 'publish' atau direktori kosong.")
            return True
        print(f"[*] Ditemukan {len(drafts)} artikel draf yang menunggu jadwal tayang.")
        target_posts = drafts[:limit]

    print(f"[*] Memproses {len(target_posts)} artikel untuk dipublikasikan pada jadwal ini...")

    gemini_key = os.environ.get("GEMINI_API_KEY")

    for i, post in enumerate(target_posts, 1):
        print(f"\n--- [{i}/{len(target_posts)}] Memproses: '{post['title']}' ---")
        print(f"Berkas  : {post['file_path']}")
        print(f"Label   : {post['labels']}")

        if dry_run:
            print("[DRY-RUN] Melewati panggilan API eksternal...")
            continue

        # 1. Publikasikan ke Blogger API v3
        try:
            live_url = publish_post_to_blogger(post)
        except Exception as e:
            print(f"[!] Gagal mempublikasikan ke Blogger: {e}")
            continue

        # 2. Perbarui frontmatter file markdown
        update_markdown_status_to_publish(post["file_path"], live_url)

        # 3. Publikasikan ke Facebook Page (Zero-Link 4:5 Master News Card)
        fb_published = False
        if not skip_fb and generate_facebook_news_card and publish_to_facebook:
            try:
                card_data = extract_facebook_card_data(post, gemini_key)
                card_png = os.path.join("posts/facebook_drafts", f"live_card_{int(datetime.now().timestamp())}.png")
                generate_facebook_news_card(card_data, card_png)
                fb_caption = generate_facebook_caption(card_data)

                # Simpan salinan caption
                cap_txt = card_png.replace(".png", ".txt")
                with open(cap_txt, "w", encoding="utf-8") as f:
                    f.write(fb_caption)

                fb_published = publish_to_facebook(card_png, fb_caption)
            except Exception as e:
                print(f"[!] Peringatan saat proses Facebook: {e}")
        else:
            print("[*] Melewati publikasi Facebook (--skip-fb aktif atau modul tidak lengkap).")

        # 4. Kirim Konfirmasi ke Telegram Bot Redaksi
        if not skip_telegram:
            send_telegram_publication_alert(post, live_url, fb_published)

        # 5. Catat riwayat
        update_published_history(post, live_url)

    print("\n🎉 Proses penerbitan draf terjadwal telah selesai dengan sukses!")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Paduka Sambas Scheduled Publisher")
    parser.add_argument("--file", help="Jalur spesifik berkas markdown draf (opsional)")
    parser.add_argument("--limit", type=int, default=1, help="Batas jumlah draf yang dipublikasikan (default: 1)")
    parser.add_argument("--skip-fb", action="store_true", help="Lewati posting ke Halaman Facebook")
    parser.add_argument("--skip-telegram", action="store_true", help="Lewati notifikasi Telegram")
    parser.add_argument("--dry-run", action="store_true", help="Jalankan simulasi tanpa posting ke API eksternal")
    args = parser.parse_args()

    success = run_scheduled_publishing(
        target_file=args.file,
        limit=args.limit,
        skip_fb=args.skip_fb,
        skip_telegram=args.skip_telegram,
        dry_run=args.dry_run
    )
    if not success:
        sys.exit(1)
