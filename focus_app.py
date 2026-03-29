import os

import sys

import time

import json

import threading

import subprocess

import random

import string

import ctypes

import winreg

from datetime import datetime, timedelta

import customtkinter as ctk

from PIL import Image

import pystray

from pystray import MenuItem as item



# মডার্ন থিম

ctk.set_appearance_mode("dark")

ctk.set_default_color_theme("blue")



# ফাইল পাথ (ডেটা সেভ করার জন্য)

APPDATA_DIR = os.path.join(os.getenv('APPDATA'), 'RasFocus')

if not os.path.exists(APPDATA_DIR):

    os.makedirs(APPDATA_DIR)



STATE_FILE = os.path.join(APPDATA_DIR, 'state.json')

STATS_FILE = os.path.join(APPDATA_DIR, 'stats.json')

HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"

REDIRECT = "127.0.0.1"

FIREWALL_RULE_NAME = "RasFocus_Block"



class FocusApp(ctk.CTk):

    def __init__(self):

        super().__init__()

        self.title("RasFocus Pro Max")

        self.geometry("800x850")

        self.resizable(False, False)

        self.protocol('WM_DELETE_WINDOW', self.withdraw_to_tray)



        self.is_focusing = False

        self.end_time = None

        self.total_duration_minutes = 0

        self.sites = []

        self.apps = []

        

        self.stats_data = self.load_stats()

        self.setup_ui()

        self.check_previous_state()



    def load_stats(self):

        if os.path.exists(STATS_FILE):

            with open(STATS_FILE, 'r') as f: return json.load(f)

        return {"total_sessions": 0, "total_minutes": 0}



    def save_stats(self, minutes_focused):

        self.stats_data["total_sessions"] += 1

        self.stats_data["total_minutes"] += int(minutes_focused)

        with open(STATS_FILE, 'w') as f: json.dump(self.stats_data, f)

        self.update_stats_ui()



    def set_autostart(self, enable):

        key = winreg.HKEY_CURRENT_USER

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        try:

            registry_key = winreg.OpenKey(key, key_path, 0, winreg.KEY_ALL_ACCESS)

            if enable:

                winreg.SetValueEx(registry_key, "RasFocus", 0, winreg.REG_SZ, sys.executable)

            else:

                winreg.DeleteValue(registry_key, "RasFocus")

            winreg.CloseKey(registry_key)

        except Exception:

            pass



    def setup_ui(self):

        self.header_frame = ctk.CTkFrame(self, fg_color="#1e1e2e", corner_radius=15, height=80)

        self.header_frame.pack(pady=20, padx=20, fill="x")

        self.title_label = ctk.CTkLabel(self.header_frame, text="⚡ RasFocus Pro Max", font=("Segoe UI", 32, "bold"), text_color="#a6e3a1")

        self.title_label.place(relx=0.5, rely=0.5, anchor="center")



        self.tabview = ctk.CTkTabview(self, width=760, height=680)

        self.tabview.pack(pady=5, padx=20)

        self.tab_focus = self.tabview.add("Set Focus")

        self.tab_stats = self.tabview.add("Web Statistics")

        self.tab_settings = self.tabview.add("Settings")



        # --- SET FOCUS TAB ---

        self.input_frame = ctk.CTkFrame(self.tab_focus, fg_color="#282a36", corner_radius=15)

        self.input_frame.pack(pady=15, padx=20, fill="x")

        self.site_entry = ctk.CTkEntry(self.input_frame, placeholder_text="🌐 Block Websites (comma separated)", width=600, height=45)

        self.site_entry.pack(pady=15)

        self.app_entry = ctk.CTkEntry(self.input_frame, placeholder_text="📱 Block Apps (e.g. chrome.exe)", width=600, height=45)

        self.app_entry.pack(pady=10)



        self.features_frame = ctk.CTkFrame(self.tab_focus, fg_color="transparent")

        self.features_frame.pack(pady=10, padx=20, fill="x")

        self.internet_switch = ctk.CTkSwitch(self.features_frame, text="Kill All Internet", font=("Segoe UI", 15, "bold"), progress_color="#f38ba8")

        self.internet_switch.grid(row=0, column=0, padx=40, pady=10)

        self.strict_switch = ctk.CTkSwitch(self.features_frame, text="Strict Mode (Block TaskMgr)", font=("Segoe UI", 15, "bold"), progress_color="#fab387")

        self.strict_switch.grid(row=0, column=1, padx=40, pady=10)

        self.hardcore_switch = ctk.CTkSwitch(self.features_frame, text="Hardcore (No Unlock)", font=("Segoe UI", 15, "bold"), progress_color="#cba6f7")

        self.hardcore_switch.grid(row=1, column=0, columnspan=2, pady=10)



        self.time_frame = ctk.CTkFrame(self.tab_focus, fg_color="#282a36", corner_radius=15)

        self.time_frame.pack(pady=10, padx=20, fill="x")

        self.preset_frame = ctk.CTkFrame(self.time_frame, fg_color="transparent")

        self.preset_frame.pack(pady=10)

        ctk.CTkButton(self.preset_frame, text="15m", width=120, height=40, fg_color="#89b4fa", command=lambda: self.set_time("15")).pack(side="left", padx=20)

        ctk.CTkButton(self.preset_frame, text="30m", width=120, height=40, fg_color="#89b4fa", command=lambda: self.set_time("30")).pack(side="left", padx=20)

        ctk.CTkButton(self.preset_frame, text="60m", width=120, height=40, fg_color="#89b4fa", command=lambda: self.set_time("60")).pack(side="left", padx=20)

        self.custom_time = ctk.CTkEntry(self.time_frame, placeholder_text="Custom Min", width=150, height=40, justify="center")

        self.custom_time.pack(pady=10)



        self.start_btn = ctk.CTkButton(self.tab_focus, text="🚀 START FOCUS SESSION", font=("Segoe UI", 22, "bold"), fg_color="#f38ba8", hover_color="#d20f39", height=60, width=500, corner_radius=30, command=self.start_focus)

        self.start_btn.pack(pady=15)

        

        self.progress_bar = ctk.CTkProgressBar(self.tab_focus, width=500, height=15, progress_color="#a6e3a1")

        self.progress_bar.set(0)

        self.progress_bar.pack(pady=5)

        self.status_label = ctk.CTkLabel(self.tab_focus, text="Ready to focus!", font=("Segoe UI", 18, "bold"), text_color="#a6adc8")

        self.status_label.pack(pady=5)



        self.unlock_frame = ctk.CTkFrame(self.tab_focus, fg_color="#313244", corner_radius=10)

        self.unlock_msg = ctk.CTkLabel(self.unlock_frame, text="Emergency Unlock: Type exactly as below", text_color="#f9e2af")

        self.random_text_label = ctk.CTkTextbox(self.unlock_frame, height=60, width=500, font=("Consolas", 12))

        self.type_entry = ctk.CTkEntry(self.unlock_frame, placeholder_text="Type here...", width=350, height=40)

        self.unlock_btn = ctk.CTkButton(self.unlock_frame, text="Unlock", width=100, height=40, fg_color="#f38ba8", command=self.verify_unlock)



        # --- STATS TAB ---

        self.stats_title = ctk.CTkLabel(self.tab_stats, text="📊 Your Lifetime Focus Report", font=("Segoe UI", 26, "bold"), text_color="#cba6f7")

        self.stats_title.pack(pady=30)

        

        self.stat_sessions_lbl = ctk.CTkLabel(self.tab_stats, text="0", font=("Segoe UI", 60, "bold"), text_color="#89b4fa")

        self.stat_sessions_lbl.pack(pady=10)

        ctk.CTkLabel(self.tab_stats, text="Total Successful Sessions", font=("Segoe UI", 16)).pack(pady=0)



        self.stat_minutes_lbl = ctk.CTkLabel(self.tab_stats, text="0", font=("Segoe UI", 60, "bold"), text_color="#a6e3a1")

        self.stat_minutes_lbl.pack(pady=30)

        ctk.CTkLabel(self.tab_stats, text="Total Minutes Focused", font=("Segoe UI", 16)).pack(pady=0)

        

        self.update_stats_ui()



        # --- SETTINGS TAB ---

        self.settings_label = ctk.CTkLabel(self.tab_settings, text="⚙️ Preferences", font=("Segoe UI", 24, "bold"))

        self.settings_label.pack(pady=30)

        

        self.autostart_var = ctk.BooleanVar(value=False)

        self.autostart_checkbox = ctk.CTkCheckBox(self.tab_settings, text="Launch RasFocus on System Startup (Registry)", font=("Segoe UI", 16), variable=self.autostart_var, command=lambda: self.set_autostart(self.autostart_var.get()))

        self.autostart_checkbox.pack(pady=20)

        

        ctk.CTkLabel(self.tab_settings, text="Software Information", font=("Segoe UI", 18, "bold"), text_color="#89b4fa").pack(pady=40)

        self.about_text = ctk.CTkLabel(self.tab_settings, text="RasFocus Pro Max - Enterprise Edition\nVersion 2.0.1\n\nDeveloped specifically for deep work and extreme productivity.\n© 2026 RasFocus Inc.", font=("Segoe UI", 14), text_color="#45475a")

        self.about_text.pack(pady=10)



    def update_stats_ui(self):

        self.stat_sessions_lbl.configure(text=str(self.stats_data["total_sessions"]))

        self.stat_minutes_lbl.configure(text=str(self.stats_data["total_minutes"]))



    def set_time(self, minutes):

        self.custom_time.delete(0, "end")

        self.custom_time.insert(0, minutes)



    def start_focus(self, resume_data=None):

        if not resume_data and not self.custom_time.get(): return

        

        self.is_focusing = True

        self.start_btn.configure(state="disabled", fg_color="#45475a", text="🔒 SESSION ACTIVE")

        self.tabview.set("Set Focus")

        

        # Disable inputs

        self.site_entry.configure(state="disabled")

        self.app_entry.configure(state="disabled")

        self.custom_time.configure(state="disabled")

        self.internet_switch.configure(state="disabled")

        self.strict_switch.configure(state="disabled")

        self.hardcore_switch.configure(state="disabled")



        if not resume_data:

            self.total_duration_minutes = int(self.custom_time.get())

            self.end_time = datetime.now() + timedelta(minutes=self.total_duration_minutes)

            self.sites = [s.strip() for s in self.site_entry.get().split(',') if s.strip()]

            self.apps = [a.strip() for a in self.app_entry.get().split(',') if a.strip()]

            internet = self.internet_switch.get()

            strict = self.strict_switch.get()

            hardcore = self.hardcore_switch.get()



            with open(STATE_FILE, 'w') as f:

                json.dump({"end_time": self.end_time.timestamp(), "total_m": self.total_duration_minutes, "sites": self.sites, "apps": self.apps, "internet": internet, "strict": strict, "hardcore": hardcore}, f)

        else:

            self.end_time = datetime.fromtimestamp(resume_data["end_time"])

            self.total_duration_minutes = resume_data.get("total_m", 1)

            self.sites = resume_data["sites"]

            self.apps = resume_data["apps"]

            internet = resume_data.get("internet", False)

            strict = resume_data.get("strict", False)

            hardcore = resume_data.get("hardcore", False)



        if internet:

            subprocess.run(f'netsh advfirewall firewall add rule name="{FIREWALL_RULE_NAME}" dir=out action=block remoteip=any', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)



        if not hardcore:

            self.unlock_text = "I am breaking my commitment. " + "".join(random.choices(string.ascii_letters + string.digits, k=15))

            self.unlock_msg.pack(pady=5)

            self.random_text_label.pack(pady=5)

            self.random_text_label.configure(state="normal")

            self.random_text_label.delete("0.0", "end")

            self.random_text_label.insert("0.0", self.unlock_text)

            self.random_text_label.configure(state="disabled")

            self.type_entry.pack(side="left", padx=15, pady=10)

            self.unlock_btn.pack(side="right", padx=15, pady=10)

            self.unlock_frame.pack(pady=10, padx=20, fill="x")



        threading.Thread(target=self.focus_engine, args=(strict,), daemon=True).start()



    def verify_unlock(self):

        if self.type_entry.get() == self.unlock_text:

            self.stop_focus(completed=False)

        else:

            self.status_label.configure(text="❌ Incorrect Code! Keep Focusing.", text_color="#f38ba8")



    def focus_engine(self, strict):

        strict_apps = self.apps.copy()

        if strict: strict_apps.extend(['taskmgr.exe', 'cmd.exe', 'powershell.exe', 'regedit.exe'])

        total_seconds = self.total_duration_minutes * 60



        while datetime.now() < self.end_time and self.is_focusing:

            try:

                with open(HOSTS_PATH, 'r+') as f:

                    content = f.read()

                    for site in self.sites:

                        if site not in content: f.write(f"{REDIRECT} {site}\n")

                for app in strict_apps:

                    subprocess.run(['taskkill', '/F', '/IM', app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            except: pass

            

            remaining = self.end_time - datetime.now()

            rem_sec = remaining.total_seconds()

            

            # Progress bar logic

            progress_val = max(0, min(1, 1 - (rem_sec / total_seconds)))

            self.progress_bar.set(progress_val)



            hours, remainder = divmod(remaining.seconds, 3600)

            minutes, seconds = divmod(remainder, 60)

            self.status_label.configure(text=f"🔥 Time Remaining: {hours:02d}:{minutes:02d}:{seconds:02d}", text_color="#a6e3a1")

            time.sleep(2)



        if self.is_focusing: self.stop_focus(completed=True)



    def stop_focus(self, completed=True):

        self.is_focusing = False

        subprocess.run(f'netsh advfirewall firewall delete rule name="{FIREWALL_RULE_NAME}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        try:

            with open(HOSTS_PATH, 'r') as f: lines = f.readlines()

            with open(HOSTS_PATH, 'w') as f:

                for line in lines:

                    if not any(site in line for site in self.sites): f.write(line)

        except: pass



        if os.path.exists(STATE_FILE): os.remove(STATE_FILE)

        

        if completed:

            self.save_stats(self.total_duration_minutes)

            self.status_label.configure(text="✅ Session Complete! Stats Updated.", text_color="#89b4fa")

            self.progress_bar.set(1)

        else:

            self.status_label.configure(text="⚠️ Session Aborted.", text_color="#f38ba8")

            self.progress_bar.set(0)



        self.start_btn.configure(state="normal", fg_color="#f38ba8", text="🚀 START FOCUS SESSION")

        self.site_entry.configure(state="normal")

        self.app_entry.configure(state="normal")

        self.custom_time.configure(state="normal")

        self.internet_switch.configure(state="normal")

        self.strict_switch.configure(state="normal")

        self.hardcore_switch.configure(state="normal")

        self.unlock_frame.pack_forget()



    def check_previous_state(self):

        if os.path.exists(STATE_FILE):

            try:

                with open(STATE_FILE, 'r') as f:

                    data = json.load(f)

                    if datetime.now() < datetime.fromtimestamp(data["end_time"]):

                        self.start_focus(resume_data=data)

                    else:

                        os.remove(STATE_FILE)

                        subprocess.run(f'netsh advfirewall firewall delete rule name="{FIREWALL_RULE_NAME}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            except: pass



    def withdraw_to_tray(self):

        self.withdraw()

        image = Image.new('RGB', (64, 64), color=(40, 42, 54))

        menu = (item('Open RasFocus', self.show_window),)

        self.tray_icon = pystray.Icon("RasFocus", image, "RasFocus Background Mode", menu)

        threading.Thread(target=self.tray_icon.run, daemon=True).start()



    def show_window(self):

        self.tray_icon.stop()

        self.deiconify()



if __name__ == "__main__":

    if not ctypes.windll.shell32.IsUserAnAdmin():

        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)

        sys.exit()

    app = FocusApp()

    app.mainloop()
