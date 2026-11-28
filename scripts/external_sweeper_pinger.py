#!/usr/bin/env python3
"""
PADUKA SAMBAS — External Sweeper Pinger (Opsi 3 Fail-Safe)
=========================================================
Skrip pemicu eksternal independen di luar cron internal GitHub.
Mendukung:
1. Facebook Master News Card (facebook_hourly.yml)
2. Blog Paduka Sambas / Blogger (scheduled_publisher.yml)

Dapat dijalankan dari:
- cron-job.org / EasyCron (via Webhook)
- Windows Task Scheduler / Cron Lokal
- Vercel Serverless Function / Cloud Pinger
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

REPO_OWNER = "paduksambas"
REPO_NAME = "github-to-blogspot"

MASTER_NEWS_SLOTS = [
    ("06:17 WIB", "05:15", "07:15"),
    ("08:17 WIB", "07:15", "09:15"),
    ("10:17 WIB", "09:15", "11:15"),
    ("12:17 WIB", "11:15", "13:15"),
    ("14:17 WIB", "13:15", "15:15"),
    ("16:17 WIB", "15:15", "17:15"),
    ("18:17 WIB", "17:15", "19:15"),
    ("20:17 WIB", "19:15", "21:15"),
    ("22:17 WIB", "21:15", "23:45"),
]

BLOGGER_SLOTS = [
    ("07:30 WIB", "06:45", "09:00"),
    ("12:30 WIB", "11:45", "14:00"),
    ("17:30 WIB", "16:45", "19:00"),
    ("20:30 WIB", "19:45", "22:00"),
]

def get_wib_now():
    return datetime.now(timezone(timedelta(hours=7)))

def parse_date_to_wib_hm(date_str):
    if not date_str:
        return ""
    if "T" in date_str:
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone(timedelta(hours=7))).strftime("%H:%M")
        except Exception:
            pass
    try:
        parts = date_str.replace(" WIB", "").split()
        if len(parts) >= 2:
            return parts[1][:5]
    except Exception:
        pass
    return ""

def fetch_json_online_or_local(filename):
    url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{filename}"
    req = urllib.request.Request(url, headers={"User-Agent": "PadukaSambas-External-Pinger"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), filename)
        if os.path.exists(local_path):
            with open(local_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

def is_facebook_slot_fulfilled(history):
    now = get_wib_now()
    today_str = now.strftime("%Y-%m-%d")
    cur_hm = now.strftime("%H:%M")

    matching_slot = None
    for label, start_w, end_w in MASTER_NEWS_SLOTS:
        if start_w <= cur_hm <= end_w:
            matching_slot = (label, start_w, end_w)
            break

    if not matching_slot:
        return True, "Di luar jam aktif Facebook (Tengah Malam)"

    label, start_w, end_w = matching_slot
    for item in history:
        pub = item.get("published_at", "")
        if today_str in pub:
            time_part = pub.split()[1][:5]
            if start_w <= time_part <= end_w:
                return True, f"Slot Facebook {label} sudah terbit pada {pub}"

    return False, f"Slot Facebook {label} BELUM TERBIT!"

def is_blogger_slot_fulfilled(history):
    now = get_wib_now()
    today_str = now.strftime("%Y-%m-%d")
    cur_hm = now.strftime("%H:%M")

    matching_slot = None
    for label, start_w, end_w in BLOGGER_SLOTS:
        if start_w <= cur_hm <= end_w:
            matching_slot = (label, start_w, end_w)
            break

    if not matching_slot:
        return True, "Di luar jam aktif Blogger"

    label, start_w, end_w = matching_slot
    if isinstance(history, dict):
        for k, v in history.items():
            if k == "__used_bg_images__":
                continue
            pub = v.get("published_at", "") or v.get("date", "")
            if today_str in pub:
                time_part = parse_date_to_wib_hm(pub)
                if start_w <= time_part <= end_w:
                    title = v.get("title") or v.get("published_title", "")
                    return True, f"Slot Blogger {label} sudah terbit ({title})"

    return False, f"Slot Blogger {label} BELUM TERBIT!"

def trigger_github_workflow(token, workflow_file):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{workflow_file}/dispatches"
    payload = json.dumps({"ref": "main"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "PadukaSambas-External-Pinger",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status in (200, 204):
                print(f"[+] SUKSES: Workflow {workflow_file} berhasil dipicu via external API!")
                return True
            else:
                print(f"[!] Respon server: HTTP {resp.status}")
                return False
    except urllib.error.HTTPError as e:
        print(f"[!] HTTP Error {e.code}: {e.read().decode('utf-8')}")
        return False
    except Exception as e:
        print(f"[!] Error koneksi: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Paduka Sambas External Sweeper Pinger (Opsi 3)")
    parser.add_argument("--target", choices=["facebook", "blogger", "all"], default="all",
                        help="Kanal target yang ingin dipantau dan dipicu (default: all)")
    args = parser.parse_args()

    print("=" * 65)
    print(f"PADUKA SAMBAS — EXTERNAL SWEEPER PINGER (Target: {args.target.upper()})")
    print(f"Waktu Sekarang: {get_wib_now().strftime('%Y-%m-%d %H:%M:%S WIB')}")
    print("=" * 65)

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_PAT")
    if not token:
        print("[!] GITHUB_TOKEN atau GH_PAT tidak ditemukan di environment.")
        sys.exit(1)

    # 1. Periksa Facebook Master Card
    if args.target in ("facebook", "all"):
        fb_hist = fetch_json_online_or_local("facebook_published_history.json")
        fb_done, fb_msg = is_facebook_slot_fulfilled(fb_hist)
        print(f"[*] Facebook: {fb_msg}")
        if not fb_done:
            print("[!] Menembak GitHub Actions: facebook_hourly.yml...")
            trigger_github_workflow(token, "facebook_hourly.yml")
        else:
            print("[i] Facebook aman, tidak perlu aksi.")

    # 2. Periksa Blog Paduka Sambas / Blogger
    if args.target in ("blogger", "all"):
        blog_hist = fetch_json_online_or_local("published_history.json")
        blog_done, blog_msg = is_blogger_slot_fulfilled(blog_hist)
        print(f"[*] Blogger : {blog_msg}")
        if not blog_done:
            print("[!] Menembak GitHub Actions: scheduled_publisher.yml...")
            trigger_github_workflow(token, "scheduled_publisher.yml")
        else:
            print("[i] Blogger aman, tidak perlu aksi.")

if __name__ == "__main__":
    main()
