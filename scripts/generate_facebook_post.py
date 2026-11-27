#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generator Postingan Halaman Facebook (Page) Paduka Sambas
========================================================
Standar Resmi: Zero-Link Posting (Jurnalisme Native)
Format Visual: Master News Card 4:5 (1080 x 1350 px) PNG
Palet Warna  : Hijau Zamrud Sangat Gelap (#0B251C) & Kuning Emas Melayu (#F4C430)
"""

import os
import io
import re
import sys
import json
import urllib.request
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps


def get_system_font(font_type="bold", size=24):
    """Mencari font sistem yang tersedia di Windows maupun Linux (GitHub Actions)."""
    if font_type == "impact":
        candidate_paths = [
            "C:/Windows/Fonts/impact.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        ]
    elif font_type == "bold":
        candidate_paths = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        ]
    else:
        candidate_paths = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        ]

    for p in candidate_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass

    try:
        return ImageFont.load_default()
    except Exception:
        return None


def generate_facebook_news_card(data, output_path="posts/facebook_drafts/news_card.png"):
    """
    Menghasilkan Master News Card 4:5 (1080 x 1350 px) Berstandar Viral Media Sosial Paduka Sambas:
    - Zona Atas   : Banner Merah dengan Headline Utama Besar Putih & Emas + Badge Resmi
    - Zona Tengah : Frame Foto Khusus Proporsional 16:9 (Foto jernih, tajam, tidak terpotong)
    - Zona Bawah  : Box Judul Kuning Terang Berkontras Tinggi (Sangat mudah dibaca di Feed)
    - Metadata    : Info Bar Kategori & Sumber
    - Footer      : Branding Elegan PADUKA SAMBAS | BERITA KALBAR
    """
    import textwrap
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    w, h = 1080, 1350

    card = Image.new("RGB", (w, h), (14, 14, 14))
    draw = ImageDraw.Draw(card)

    # -------------------------------------------------------------
    # 1. ZONA ATAS (HEADER MERAH & BRANDING: 0 - 250 px)
    # -------------------------------------------------------------
    draw.rectangle([0, 0, w, 250], fill=(215, 25, 25))

    # Aksen Garis Diagonal Kuning di Kanan Atas
    for i in range(4):
        x = w - 160 + (i * 32)
        draw.polygon([(x, 0), (x + 18, 0), (x - 30, 250), (x - 48, 250)], fill=(255, 215, 0))

    # Aksen Dot Matrix Kanan Atas
    for r in range(4):
        for c in range(6):
            cx = w - 190 - (c * 16)
            cy = 35 + (r * 16)
            draw.ellipse([cx, cy, cx + 6, cy + 6], fill=(255, 215, 0))

    # Badge Logo Kiri Atas (Kuning Lengkung)
    badge_w, badge_h = 240, 95
    draw.rounded_rectangle([25, 20, 25 + badge_w, 20 + badge_h], radius=18, fill=(255, 215, 0), outline=(0, 0, 0), width=3)
    f_badge1 = get_system_font("impact", 28)
    f_badge2 = get_system_font("impact", 24)
    draw.text((42, 28), "PADUKA SAMBAS", font=f_badge1, fill=(0, 0, 0))
    badge_sub = data.get("badge_red", "BERITA DAERAH")
    if len(badge_sub) > 14:
        badge_sub = "BERITA UTAMA"
    draw.text((42, 60), badge_sub.upper(), font=f_badge2, fill=(195, 20, 20))

    # Headline Utama Atas (Gaya Impact Tebal Bergaris Luar Hitam)
    hl1 = data.get("headline_line1", "").strip().upper()
    hl2_p = data.get("headline_line2_prefix", "").strip().upper()
    hl2_k = data.get("keyword_highlight", "").strip().upper()
    hl2 = f"{hl2_p} {hl2_k}".strip()

    if not hl1:
        # Fallback dari judul jika ekstraksi kosong
        full_title = data.get("title", "")
        parts = full_title.split(":") if ":" in full_title else full_title.split(" - ")
        if len(parts) > 1:
            hl1 = parts[0][:22].upper()
            hl2 = parts[1][:22].upper()
        else:
            words = full_title.split()
            hl1 = " ".join(words[:len(words)//2])[:22].upper()
            hl2 = " ".join(words[len(words)//2:])[:22].upper()

    font_top = get_system_font("impact", 66)
    avail_x = 285
    avail_w = w - avail_x - 110

    b_hl1 = font_top.getbbox(hl1)
    w_hl1 = b_hl1[2] - b_hl1[0]
    x_hl1 = avail_x + max(0, (avail_w - w_hl1) // 2)

    b_hl2 = font_top.getbbox(hl2)
    w_hl2 = b_hl2[2] - b_hl2[0]
    x_hl2 = avail_x + max(0, (avail_w - w_hl2) // 2)

    draw.text((x_hl1, 30), hl1, font=font_top, fill=(255, 255, 255), stroke_width=6, stroke_fill=(0, 0, 0))
    draw.text((x_hl2, 115), hl2, font=font_top, fill=(255, 225, 0), stroke_width=6, stroke_fill=(0, 0, 0))

    # Garis Pembatas Header Hitam
    draw.line([(0, 250), (w, 250)], fill=(0, 0, 0), width=6)

    # -------------------------------------------------------------
    # 2. ZONA TENGAH (FRAME FOTO KHUSUS PROPORSIONAL 16:9: 250 - 890 px)
    # -------------------------------------------------------------
    photo_box_h = 640
    photo_url = data.get("photo_url", "")
    p_img = None

    # Prioritaskan foto mentah bersih tanpa watermark teks jika tersedia
    if photo_url:
        bn = os.path.basename(photo_url)
        raw_cand = os.path.join("posts/images", "raw_" + bn)
        if os.path.exists(raw_cand):
            try:
                p_img = Image.open(raw_cand).convert("RGB")
                print(f"[+] Menggunakan foto mentah bersih: {raw_cand}")
            except Exception:
                pass

    if not p_img and photo_url and os.path.exists(photo_url):
        try:
            p_img = Image.open(photo_url).convert("RGB")
        except Exception as e:
            print(f"[!] Gagal buka foto lokal {photo_url}: {e}")
    elif not p_img and photo_url and photo_url.startswith("http"):
        local_cand = os.path.join("posts/images", os.path.basename(photo_url))
        if os.path.exists(local_cand):
            try:
                p_img = Image.open(local_cand).convert("RGB")
            except Exception:
                pass
        if not p_img:
            try:
                req = urllib.request.Request(photo_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    p_img = Image.open(io.BytesIO(resp.read())).convert("RGB")
            except Exception as e:
                print(f"[!] Gagal unduh foto latar {photo_url}: {e}")

    if not p_img:
        p_img = Image.new("RGB", (w, photo_box_h), (25, 30, 40))
        draw_p = ImageDraw.Draw(p_img)
        draw_p.text((w // 4, photo_box_h // 2), "DOKUMENTASI FOTO REDAKSI", font=get_system_font("bold", 32), fill=(180, 180, 180))
    else:
        # Resize proporsional dengan metode Lanczos tajam
        p_img = ImageOps.fit(p_img, (w, photo_box_h), method=Image.Resampling.LANCZOS)

    card.paste(p_img, (0, 250))

    # Aksen Diagonal Stripes pada Sudut Bawah Foto
    for i in range(3):
        ox = 0 + (i * 26)
        col = (255, 215, 0) if i % 2 == 0 else (215, 25, 25)
        draw.polygon([(ox, 890), (ox + 16, 890), (ox + 75, 800), (ox + 59, 800)], fill=col)

    for i in range(3):
        ox = w - 10 + (i * 26)
        col = (255, 215, 0) if i % 2 == 0 else (215, 25, 25)
        draw.polygon([(ox - 60, 890), (ox - 44, 890), (ox, 800), (ox - 16, 800)], fill=col)

    # -------------------------------------------------------------
    # 3. ZONA BAWAH (BOX JUDUL KUNING TERANG: 890 - 1150 px)
    # -------------------------------------------------------------
    draw.rectangle([0, 890, w, 1150], fill=(255, 215, 0))
    draw.line([(0, 890), (w, 890)], fill=(0, 0, 0), width=5)

    # Aksen Garis Merah di Sisi Kiri Box Kuning
    for i in range(3):
        ox = 18 + (i * 26)
        draw.polygon([(ox, 1150), (ox + 15, 1150), (ox + 65, 890), (ox + 50, 890)], fill=(215, 25, 25))

    # Judul Berita Lengkap & Jelas
    title_text = data.get("title", "")
    f_title = get_system_font("bold", 43)
    lines = textwrap.wrap(title_text, width=37)
    y_t = 915 if len(lines) <= 2 else 905
    line_spacing = 58 if len(lines) <= 2 else 52
    for line in lines[:3]:
        draw.text((140, y_t), line, font=f_title, fill=(10, 10, 10))
        y_t += line_spacing

    # -------------------------------------------------------------
    # 4. METADATA SUB-BAR (1150 - 1225 px)
    # -------------------------------------------------------------
    draw.rectangle([0, 1150, w, 1225], fill=(20, 20, 22))

    # Ikon Info (i)
    draw.ellipse([30, 1166, 68, 1204], fill=(215, 25, 25))
    draw.text((45, 1172), "i", font=get_system_font("bold", 24), fill=(255, 255, 255))

    badge_cat = data.get("badge_gold", "TRENDING").upper()
    source_cr = data.get("source_credit", "Redaksi Media").upper()
    
    # Deteksi jangkauan wilayah (Global / Nasional / Daerah)
    title_upper = (data.get("title", "") + " " + badge_cat).upper()
    if any(k in title_upper for k in ["DUNIA", "GLOBAL", "INTERNASIONAL", "AS", "AMERIKA", "CHINA", "TIMUR TENGAH", "RUSIA"]):
        region_tag = "BERITA GLOBAL"
    elif any(k in title_upper for k in ["KALBAR", "SAMBAS", "PONTIANAK"]):
        region_tag = "KALIMANTAN BARAT"
    else:
        region_tag = "BERITA NASIONAL"

    sub_text = f"{badge_cat}  •  SUMBER: {source_cr}  •  {region_tag}"
    draw.text((85, 1176), sub_text, font=get_system_font("bold", 21), fill=(240, 240, 240))

    # Aksen Dots Kanan
    for c in range(5):
        for r in range(2):
            cx = w - 40 - (c * 14)
            cy = 1178 + (r * 14)
            draw.ellipse([cx, cy, cx + 5, cy + 5], fill=(255, 215, 0))

    # -------------------------------------------------------------
    # 5. FOOTER RESMI (1225 - 1350 px)
    # -------------------------------------------------------------
    draw.rectangle([0, 1225, w, 1350], fill=(8, 8, 8))
    draw.line([(0, 1225), (w, 1225)], fill=(255, 215, 0), width=4)

    f_foot = get_system_font("impact", 44)
    foot_1 = "PADUKA SAMBAS"
    foot_sep = " | "
    foot_2 = region_tag

    b1 = f_foot.getbbox(foot_1)
    b_s = f_foot.getbbox(foot_sep)
    b2 = f_foot.getbbox(foot_2)

    tot_w = (b1[2] - b1[0]) + (b_s[2] - b_s[0]) + (b2[2] - b2[0])
    x_pos = (w - tot_w) // 2

    draw.text((x_pos, 1255), foot_1, font=f_foot, fill=(255, 215, 0))
    x_pos += (b1[2] - b1[0])
    draw.text((x_pos, 1255), foot_sep, font=f_foot, fill=(255, 255, 255))
    x_pos += (b_s[2] - b_s[0])
    draw.text((x_pos, 1255), foot_2, font=f_foot, fill=(255, 255, 255))

    # Simpan dalam format PNG tanpa kompresi pecah
    card.save(output_path, "PNG")
    print(f"[+] Master News Card 4:5 Gaya Viral berhasil dibuat: {output_path}")
    return output_path


def generate_facebook_caption(data):
    """
    Menyusun narasi caption Facebook resmi berformat Zero-Link (5W+1H tuntas tanpa tautan luar).
    """
    title = data.get("title", "").strip()
    lead = data.get("lead", "").strip()
    body = data.get("body", "").strip()
    impact = data.get("impact", "").strip()
    discussion = data.get("discussion_prompt", "Bagaimana tanggapan Anda mengenai kabar ini? Sampaikan di kolom komentar!")
    source = data.get("source_credit", "Paduka Sambas")
    hashtags = data.get("hashtags", ["PadukaSambas", "KabarSambas", "SambasTerkini", "KalbarHariIni"])

    ht_str = " ".join([f"#{t.replace('#', '')}" for t in hashtags])

    caption = f"""📌 {title.upper()}

SAMBAS (PADUKA SAMBAS) — {lead}

{body}

{impact}

---
💬 {discussion}

(Foto / Sumber: {source})

{ht_str}"""
    return caption.strip()


# =====================================================================
# CONTOH DATA SIMULASI (UNTUK UJI COBA INTERNAL / DRY-RUN)
# =====================================================================
SAMPLE_DATA_NEWS = {
    "is_data_mode": True,
    "photo_url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=80",
    "badge_red": "INFO SAMBAS",
    "badge_gold": "DATA BPS TERBARU",
    "kicker": "KABAR BAIK KETENAGAKERJAAN DAERAH",
    "headline_line1": "Pengangguran di Sambas",
    "headline_line2_prefix": "Turun Tajam ke ",
    "keyword_highlight": "3,92%",
    "box1_val": "96,08%",
    "box1_lbl": "Tingkat Kesempatan Kerja (TKK)",
    "box2_val": "UNGGULAN",
    "box2_lbl": "Perdagangan & Pertanian Lokal",
    "subtext": "Pemulihan ekonomi daerah serap ribuan tenaga kerja baru di usia produktif.",
    "source_credit": "BPS Kabupaten Sambas",
    "title": "Tingkat Pengangguran Terbuka di Sambas Turun ke 3,92%",
    "lead": "Berdasarkan rilis indikator ketenagakerjaan Badan Pusat Statistik (BPS) terbaru, Tingkat Pengangguran Terbuka (TPT) di Kabupaten Sambas berhasil ditekan hingga menyentuh angka 3,92%.",
    "body": "Penurunan ini selaras dengan meningkatnya Tingkat Kesempatan Kerja (TKK) yang kini mencapai 96,08%. Sektor pertanian, perdagangan lokal, dan hilirisasi produk unggulan daerah menjadi penyumbang terbesar penyerapan tenaga kerja produktif.",
    "impact": "Pemerintah daerah terus mengarahkan penguatan vokasi dan kemudahan berusaha bagi pelaku UMKM agar tren penyerapan tenaga kerja positif ini tetap berkesinambungan.",
    "discussion_prompt": "Bagaimana pandangan Anda mengenai geliat lapangan kerja dan iklim usaha di Sambas saat ini? Sampaikan di kolom komentar!",
    "hashtags": ["PadukaSambas", "EkonomiSambas", "KabarSambas", "SambasTerkini", "KalbarHariIni"]
}

SAMPLE_EVENT_NEWS = {
    "is_data_mode": False,
    "photo_url": "https://images.unsplash.com/photo-1474487548417-781cb71495f3?w=1200&q=80",
    "badge_red": "INFO SAMBAS",
    "badge_gold": "INFRASTRUKTUR",
    "kicker": "RESPON CEPAT KELUHAN WARGA",
    "headline_line1": "Jembatan Rusak di Sambas",
    "headline_line2_prefix": "Resmi ",
    "keyword_highlight": "MULAI DIPERBAIKI",
    "box1_title": "STATUS PEKERJAAN",
    "box1_body": "Pondasi Tiang Pancang",
    "box2_title": "JALUR ALTERNATIF",
    "box2_body": "Dialihkan ke Jalan Lingkar",
    "subtext": "Dinas PUPR targetkan akses transportasi warga segera normal kembali.",
    "source_credit": "Pemkab Sambas / PUPR",
    "title": "Jembatan Penghubung di Sambas Resmi Mulai Diperbaiki",
    "lead": "Pemerintah daerah melalui instansi teknis resmi memulai pengerjaan perbaikan jembatan penghubung utama yang sebelumnya mengalami kerusakan dan dikeluhkan masyarakat.",
    "body": "Fokus pengerjaan tahap awal mencakup pemasangan tiang pancang baja dan penguatan abutmen guna memastikan struktur jembatan kokoh dilalui kendaraan tonase sedang.",
    "impact": "Selama pengerjaan berlangsung, arus lalu lintas warga dialihkan sementara melalui jalan lingkar alternatif guna menghindari kemacetan dan menjaga keselamatan pengendara.",
    "discussion_prompt": "Bagaimana kondisi infrastruktur jembatan dan jalan di sekitar lingkungan Anda? Berikan laporan Anda di kolom komentar!",
    "hashtags": ["PadukaSambas", "InfrastrukturSambas", "KabarSambas", "SambasMaju", "KalbarHariIni"]
}


def publish_to_facebook(image_path, caption, page_id=None, page_token=None):
    """
    Mengunggah foto dan caption berita secara otomatis ke Halaman Facebook via Meta Graph API.
    """
    raw_page_id = page_id or os.environ.get("FB_PAGE_ID", "")
    raw_page_token = page_token or os.environ.get("FB_PAGE_ACCESS_TOKEN", "")

    page_id = str(raw_page_id).strip().strip('"\'')
    page_token = str(raw_page_token).strip().strip('"\'')

    if not page_id or not page_token:
        print("[!] Gagal: FB_PAGE_ID atau FB_PAGE_ACCESS_TOKEN belum disetel di environment.")
        return False

    url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
    print(f"[*] Mengirim postingan otomatis ke Halaman Facebook ID: {page_id}...")

    # Membaca data gambar binary untuk multipart upload
    with open(image_path, "rb") as f:
        img_bytes = f.read()

    boundary = "----WebKitFormBoundaryPadukaSambas"
    body = io.BytesIO()

    # Part: caption
    body.write(f"--{boundary}\r\n".encode("utf-8"))
    body.write(b'Content-Disposition: form-data; name="caption"\r\n\r\n')
    body.write(caption.encode("utf-8"))
    body.write(b"\r\n")

    # Part: access_token
    body.write(f"--{boundary}\r\n".encode("utf-8"))
    body.write(b'Content-Disposition: form-data; name="access_token"\r\n\r\n')
    body.write(page_token.encode("utf-8"))
    body.write(b"\r\n")

    # Part: source (photo)
    body.write(f"--{boundary}\r\n".encode("utf-8"))
    body.write(b'Content-Disposition: form-data; name="source"; filename="news_card.png"\r\n')
    body.write(b"Content-Type: image/png\r\n\r\n")
    body.write(img_bytes)
    body.write(b"\r\n")

    body.write(f"--{boundary}--\r\n".encode("utf-8"))
    payload = body.getvalue()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(payload))
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            post_id = res_data.get("id") or res_data.get("post_id")
            print(f"[+] BERHASIL! Postingan otomatis telah terbit di Facebook dengan Post ID: {post_id}")
            return True
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"[!] Gagal posting ke Facebook: {err_msg}")
        return False
    except Exception as e:
        print(f"[!] Terjadi kesalahan jaringan: {e}")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generator Postingan Facebook Paduka Sambas")
    parser.add_argument("--test-data", action="store_true", help="Uji pembuatan kartu berita berbasis data angka")
    parser.add_argument("--test-event", action="store_true", help="Uji pembuatan kartu berita berbasis peristiwa non-angka")
    parser.add_argument("--publish-test", action="store_true", help="Uji coba otomatis posting 1 berita ke Halaman Facebook")
    args = parser.parse_args()

    out_dir = "posts/facebook_drafts"
    os.makedirs(out_dir, exist_ok=True)

    if args.publish_test:
        print("[*] MEMULAI UJI COBA OTOMATIS POSTING 1 BERITA KE FACEBOOK PAGE...")
        img_file = os.path.join(out_dir, "draft_data_news.png")
        cap_file = os.path.join(out_dir, "draft_data_caption.txt")
        if not os.path.exists(img_file) or not os.path.exists(cap_file):
            generate_facebook_news_card(SAMPLE_DATA_NEWS, img_file)
            with open(cap_file, "w", encoding="utf-8") as f:
                f.write(generate_facebook_caption(SAMPLE_DATA_NEWS))

        with open(cap_file, "r", encoding="utf-8") as f:
            caption_text = f.read()

        publish_to_facebook(img_file, caption_text)

    elif args.test_event:
        print("[*] Menjalankan uji coba: Berita Peristiwa Non-Angka...")
        img_file = generate_facebook_news_card(SAMPLE_EVENT_NEWS, os.path.join(out_dir, "draft_event_news.png"))
        caption = generate_facebook_caption(SAMPLE_EVENT_NEWS)
        with open(os.path.join(out_dir, "draft_event_caption.txt"), "w", encoding="utf-8") as f:
            f.write(caption)
        print(f"[+] Draf Berita Peristiwa selesai dibuat di: {out_dir}")
        print("\n--- CONTOH CAPTION ---")
        print(caption)

    else:
        # Default: Uji coba Berita Data Angka
        print("[*] Menjalankan uji coba: Berita Data Angka...")
        img_file = generate_facebook_news_card(SAMPLE_DATA_NEWS, os.path.join(out_dir, "draft_data_news.png"))
        caption = generate_facebook_caption(SAMPLE_DATA_NEWS)
        with open(os.path.join(out_dir, "draft_data_caption.txt"), "w", encoding="utf-8") as f:
            f.write(caption)
        print(f"[+] Draf Berita Data selesai dibuat di: {out_dir}")
        print("\n--- CONTOH CAPTION ---")
        print(caption)
