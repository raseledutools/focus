import os
import sys
import time
import ctypes
import subprocess
from datetime import datetime, timedelta

# কনফিগারেশন
HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
REDIRECT = "127.0.0.1"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def block_sites(websites):
    with open(HOSTS_PATH, 'r+') as file:
        content = file.read()
        for site in websites:
            if site not in content:
                file.write(f"{REDIRECT} {site}\n")

def unblock_sites(websites):
    with open(HOSTS_PATH, 'r') as file:
        lines = file.readlines()
    with open(HOSTS_PATH, 'w') as file:
        for line in lines:
            if not any(site in line for site in websites):
                file.write(line)

def block_apps(apps):
    for app in apps:
        subprocess.run(['taskkill', '/F', '/IM', app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    if not is_admin():
        print("দয়া করে Administrator হিসেবে রান করুন!")
        sys.exit()

    print("--- ফোকাস মোড সেটআপ ---")
    sites_to_block = input("ব্লক করার ওয়েবসাইটগুলো দিন (comma separated, e.g: facebook.com,youtube.com): ").split(',')
    apps_to_block = input("ব্লক করার অ্যাপগুলো দিন (e.g: chrome.exe,msedge.exe): ").split(',')
    duration = int(input("কত মিনিটের জন্য ফোকাস করবেন? "))

    end_time = datetime.now() + timedelta(minutes=duration)
    print(f"ফোকাস মোড শুরু হয়েছে! শেষ হবে: {end_time.strftime('%H:%M:%S')}")

    try:
        while datetime.now() < end_time:
            block_sites([s.strip() for s in sites_to_block])
            block_apps([a.strip() for a in apps_to_block])
            time.sleep(5) # প্রতি ৫ সেকেন্ড পরপর চেক করবে
    finally:
        unblock_sites([s.strip() for s in sites_to_block])
        print("ফোকাস মোড শেষ। সব কিছু আনব্লক করা হয়েছে।")

if __name__ == "__main__":
    main()
