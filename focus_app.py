import os
import sys
import time
import threading
import customtkinter as ctk
from PIL import Image
import pystray
from pystray import MenuItem as item
import subprocess
from datetime import datetime, timedelta

# UI থিম সেটআপ
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class FocusApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Rasel Focus Pro")
        self.geometry("400x500")
        self.protocol('WM_DELETE_WINDOW', self.withdraw_to_tray)

        self.is_focusing = False
        self.hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
        self.redirect = "127.0.0.1"

        # UI Elements
        self.label = ctk.CTkLabel(self, text="Focus Mode", font=("Arial", 24, "bold"))
        self.label.pack(pady=20)

        self.site_entry = ctk.CTkEntry(self, placeholder_text="Websites (e.g. facebook.com, youtube.com)", width=300)
        self.site_entry.pack(pady=10)

        self.app_entry = ctk.CTkEntry(self, placeholder_text="Apps (e.g. chrome.exe, spotify.exe)", width=300)
        self.app_entry.pack(pady=10)

        self.time_entry = ctk.CTkEntry(self, placeholder_text="Minutes (e.g. 30)", width=300)
        self.time_entry.pack(pady=10)

        self.start_btn = ctk.CTkButton(self, text="Start Focusing", command=self.start_focus)
        self.start_btn.pack(pady=20)

        self.status_label = ctk.CTkLabel(self, text="Status: Idle", text_color="gray")
        self.status_label.pack(pady=10)

    def withdraw_to_tray(self):
        self.withdraw()
        # এখানে একটি সিম্পল আইকন তৈরি (আপনি নিজের .png দিতে পারেন)
        image = Image.new('RGB', (64, 64), color=(73, 109, 137))
        menu = (item('Show', self.show_window), item('Exit', self.quit_app))
        self.tray_icon = pystray.Icon("FocusApp", image, "Focus Mode Active", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self):
        self.tray_icon.stop()
        self.deiconify()

    def quit_app(self):
        self.is_focusing = False
        if hasattr(self, 'tray_icon'): self.tray_icon.stop()
        self.destroy()
        sys.exit()

    def start_focus(self):
        if not self.time_entry.get(): return
        self.is_focusing = True
        self.start_btn.configure(state="disabled")
        duration = int(self.time_entry.get())
        sites = [s.strip() for s in self.site_entry.get().split(',') if s.strip()]
        apps = [a.strip() for a in self.app_entry.get().split(',') if a.strip()]
        
        threading.Thread(target=self.focus_engine, args=(duration, sites, apps), daemon=True).start()

    def focus_engine(self, minutes, sites, apps):
        end_time = datetime.now() + timedelta(minutes=minutes)
        while datetime.now() < end_time and self.is_focusing:
            # ব্লক ওয়েবসাইট
            try:
                with open(self.hosts_path, 'r+') as f:
                    content = f.read()
                    for site in sites:
                        if site not in content:
                            f.write(f"{self.redirect} {site}\n")
                
                # ব্লক অ্যাপস
                for app in apps:
                    subprocess.run(['taskkill', '/F', '/IM', app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass # Admin permission issues
            
            remaining = end_time - datetime.now()
            self.status_label.configure(text=f"Remaining: {str(remaining).split('.')[0]}", text_color="green")
            time.sleep(5)

        # আনব্লক করা
        try:
            with open(self.hosts_path, 'r') as f: lines = f.readlines()
            with open(self.hosts_path, 'w') as f:
                for line in lines:
                    if not any(site in line for site in sites): f.write(line)
        except: pass
        
        self.status_label.configure(text="Status: Finished", text_color="white")
        self.start_btn.configure(state="normal")

if __name__ == "__main__":
    app = FocusApp()
    app.mainloop()
