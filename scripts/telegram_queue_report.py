#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Queue Reporter - Paduka Sambas
=======================================
Mengirimkan rekapitulasi status draf ke Telegram Bot Redaksi:
- Draf yang masuk antrean jadwal tayang 4 kali sehari (07:30, 12:30, 17:30, 20:30 WIB)
- Draf cadangan yang menunggu giliran berikutnya
- Artikel yang sudah berhasil terbit
"""

import os
import sys
import re
import glob
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

def get_wib_now():
    wib_tz = timezone(timedelta(hours=7))
    return datetime.now(wib_tz).strftime("%Y-%m-%d %H:%M:%S")

def parse_post(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    title = ""
    status = "publish"
    labels = []
    blogger_url = ""
    
    for line in content.splitlines()[:20]:
        line_s = line.strip()
        if line_s.startswith("title:"):
            title = line_s.replace("title:", "").strip().strip("\"'")
        elif line_s.startswith("status:"):
            status = line_s.replace("status:", "").strip().strip("\"'").lower()
        elif line_s.startswith("blogger_url:"):
            blogger_url = line_s.replace("blogger_url:", "").strip().strip("\"'")
        elif line_s.startswith("labels:"):
            raw_l = line_s.replace("labels:", "").strip().strip("[]")
            labels = [lbl.strip().strip("\"'") for lbl in raw_l.split(",") if lbl.strip()]
            
    if not title:
        title = os.path.splitext(os.path.basename(file_path))[0].replace("-", " ").title()

    return {
        "file": os.path.basename(file_path),
        "path": file_path,
        "title": title,
        "status": status,
        "labels": labels,
        "blogger_url": blogger_url,
        "mtime": os.path.getmtime(file_path)
    }

def generate_queue_report():
    all_md = sorted(glob.glob("posts/*.md"))
    drafts = []
    published = []

    for fp in all_md:
        if "contoh" in os.path.basename(fp).lower():
            continue
        p = parse_post(fp)
        if p["status"] == "draft":
            drafts.append(p)
        else:
            published.append(p)

    # Urutkan draft secara FIFO (terlama duluan)
    drafts.sort(key=lambda x: (x["mtime"], x["file"]))
    # Urutkan published berdasarkan mtime terbaru
    published.sort(key=lambda x: x["mtime"], reverse=True)

    # Hitung 4 slot penayangan berikutnya yang valid dari waktu sekarang (WIB)
    wib_tz = timezone(timedelta(hours=7))
    now_dt = datetime.now(wib_tz)
    daily_slots = [(7, 30), (12, 30), (17, 30), (20, 30)]
    upcoming_slots = []
    
    for day_offset in range(7):
        target_d = now_dt.date() + timedelta(days=day_offset)
        for h, m in daily_slots:
            slot_dt = datetime(target_d.year, target_d.month, target_d.day, h, m, tzinfo=wib_tz)
            if slot_dt > now_dt:
                day_label = "Hari Ini" if day_offset == 0 else ("Besok" if day_offset == 1 else slot_dt.strftime("%d %b"))
                date_str = slot_dt.strftime("%d/%m")
                time_str = slot_dt.strftime("%H:%M")
                upcoming_slots.append(f"{day_label} ({date_str}), {time_str} WIB")
                if len(upcoming_slots) == 4:
                    break
        if len(upcoming_slots) == 4:
            break

    scheduled_next = drafts[:len(upcoming_slots)]
    waiting_queue = drafts[len(upcoming_slots):]

    wib_now = get_wib_now()

    lines = []
    lines.append("📋 *STATUS ANTREAN DRAF REDAKSI PADUKA SAMBAS*")
    lines.append(f"⏰ _Pembaruan: {wib_now} WIB_\n")

    lines.append("🗓️ *ANTREAN JADWAL TAYANG BERIKUTNYA:*")
    if scheduled_next:
        for idx, item in enumerate(scheduled_next):
            slot = upcoming_slots[idx] if idx < len(upcoming_slots) else "Slot Berikutnya"
            lbl = f"[{item['labels'][0]}] " if item["labels"] else ""
            lines.append(f"*{idx+1}. {slot}*\n   ↳ {lbl}{item['title']}")
    else:
        lines.append("_(Tidak ada draf yang sedang menunggu jadwal)_")

    lines.append("")
    lines.append(f"⏳ *DRAF MENUNGGU GILIRAN BERIKUTNYA ({len(waiting_queue)} Artikel):*")
    if waiting_queue:
        for idx, item in enumerate(waiting_queue, 1):
            lbl = f"[{item['labels'][0]}] " if item["labels"] else ""
            lines.append(f"{idx}. {lbl}{item['title']}")
    else:
        lines.append("_(Semua draf telah masuk slot antrean utama)_")

    lines.append("")
    lines.append(f"✅ *ARTIKEL SUDAH TERBIT (LIVE) TERBARU:*")
    for item in published[:3]:
        url_text = f" — [Buka Blog]({item['blogger_url']})" if item.get("blogger_url") else ""
        lines.append(f"• {item['title']}{url_text}")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━")
    lines.append("ℹ️ *Ringkasan Sistem:*")
    lines.append(f"• Total Draf Antrean: *{len(drafts)}* artikel")
    lines.append(f"• Total Artikel Terbit: *{len(published)}* artikel")
    lines.append("• Target Rilis: Blogger + FB Page (Zero-Link 4:5)")

    return "\n".join(lines)

def send_report_to_telegram():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    report_text = generate_queue_report()
    print("\n--- LAPORAN YANG AKAN DIKIRIM KE TELEGRAM ---")
    print(report_text)
    print("---------------------------------------------")

    if not token or not chat_id:
        print("[!] TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID belum disetel di lingkungan lokal.")
        return False

    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=urllib.parse.urlencode({
                "chat_id": chat_id,
                "text": report_text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": "true"
            }).encode("utf-8")
        )
        with urllib.request.urlopen(req, timeout=15):
            print("[+] Laporan status antrean draf berhasil terkirim ke Telegram!")
            return True
    except Exception as e:
        print(f"[!] Gagal mengirim laporan ke Telegram: {e}")
        return False

if __name__ == "__main__":
    success = send_report_to_telegram()
    if not success and os.environ.get("TELEGRAM_BOT_TOKEN"):
        sys.exit(1)
