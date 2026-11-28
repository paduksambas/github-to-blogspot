#!/usr/bin/env python3
"""
PADUKA SAMBAS — External Sweeper Pinger (Opsi 3 Fail-Safe)
Skrip pemicu eksternal independen di luar cron internal GitHub.
Dapat dijalankan dari:
1. cron-job.org / EasyCron (via Webhook)
2. Windows Task Scheduler / Cron Lokal
3. Vercel Serverless Function

Fungsi:
Memeriksa apakah slot berita Master Card jam aktif sudah terbit hari ini.
Jika belum terbit (akibat antrean GitHub macet pada :17 dan :27), skrip ini
langsung menembak GitHub Actions REST API (workflow_dispatch) untuk mengeksekusi
penerbitan berita seketika tanpa antre di scheduler GitHub.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

REPO_OWNER = "paduksambas"
REPO_NAME = "github-to-blogspot"
WORKFLOW_FILE = "facebook_hourly.yml"

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

def get_wib_now():
    return datetime.now(timezone(timedelta(hours=7)))

def fetch_published_history():
    """Mengambil riwayat terbitan Facebook langsung dari GitHub raw."""
    url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/facebook_published_history.json"
    req = urllib.request.Request(url, headers={"User-Agent": "PadukaSambas-External-Pinger"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[!] Gagal mengambil riwayat online: {e}")
        # Coba baca lokal jika berkas ada
        local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "facebook_published_history.json")
        if os.path.exists(local_path):
            with open(local_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

def is_slot_fulfilled(history):
    now = get_wib_now()
    today_str = now.strftime("%Y-%m-%d")
    cur_hm = now.strftime("%H:%M")

    matching_slot = None
    for label, start_w, end_w in MASTER_NEWS_SLOTS:
        if start_w <= cur_hm <= end_w:
            matching_slot = (label, start_w, end_w)
            break

    if not matching_slot:
        return True, "Di luar jam aktif (Tengah Malam)"

    label, start_w, end_w = matching_slot
    for item in history:
        pub = item.get("published_at", "")
        if today_str in pub:
            time_part = pub.split()[1][:5]
            if start_w <= time_part <= end_w:
                return True, f"Slot {label} sudah terbit pada {pub}"

    return False, f"Slot {label} BELUM TERBIT!"

def trigger_github_workflow(token):
    """Memicu workflow_dispatch via GitHub REST API."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{WORKFLOW_FILE}/dispatches"
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
                print(f"[+] SUKSES: Workflow {WORKFLOW_FILE} berhasil dipicu via external API!")
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
    print("=" * 65)
    print("PADUKA SAMBAS — EXTERNAL SWEEPER PINGER (OPSI 3)")
    print(f"Waktu Sekarang: {get_wib_now().strftime('%Y-%m-%d %H:%M:%S WIB')}")
    print("=" * 65)

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_PAT")
    if not token:
        print("[!] GITHUB_TOKEN atau GH_PAT tidak ditemukan di environment.")
        print("    Set environment variable: $env:GH_PAT='ghp_...' lalu jalankan ulang.")
        sys.exit(1)

    history = fetch_published_history()
    fulfilled, msg = is_slot_fulfilled(history)
    print(f"[*] Status Slot: {msg}")

    if fulfilled:
        print("[i] Tidak perlu memicu pinger eksternal. Semua aman terkendali.")
        sys.exit(0)

    print("[!] MEMICU OPSI 3: Menembak GitHub Actions via workflow_dispatch...")
    ok = trigger_github_workflow(token)
    if ok:
        print("[+] Selesai: Slot tertunda kini sedang diproses oleh server cloud.")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
