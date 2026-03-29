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
import winshell
from win32com.client import Dispatch
from datetime import datetime, timedelta
import customtkinter as ctk
from PIL import Image
import pystray
from pystray import MenuItem as item

# মডার্ন কালারফুল থিম সেটআপ
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ফাইল পাথ কনফিগারেশন (AppData তে সেভ হবে)
APPDATA_DIR = os.path.join(os.getenv('APPDATA'), 'RasFocus')
if not os.path.exists(APPDATA_DIR):
    os.makedirs(APPDATA_DIR)

STATE_FILE = os.path.join(APPDATA_DIR, 'state.json')
STATS_FILE = os.path.join(APPDATA_DIR, 'stats.json')
HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
REDIRECT = "127.0.0.1"
FIREWALL_RULE_NAME = "RasFocus_Block"

def create_desktop_shortcut():
    """অ্যাপ রান করার সাথে সাথে ডেস্কটপে অটোমেটিক শর্টকাট তৈরি করবে"""
    try:
        desktop = winshell.desktop()
        path = os.path.join(desktop, "RasFocus Pro Max.lnk")
        if not os.path.exists(path):
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(path)
            shortcut.Targetpath = sys.executable
            shortcut.WorkingDirectory = os.path.dirname(sys.executable)
            shortcut.IconLocation = sys.executable
            shortcut.save()
    except Exception as e:
        print(f"Shortcut creation failed: {e}")

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
        
        # অটোমেটিক শর্টকাট চেক
        create_desktop_shortcut() 
        
        self.stats_data = self.load_stats()
        self.setup_ui()
        self.check_previous_state()

    def load_stats(self):
        """আগের ফোকাস সেশনের ডেটা লোড করবে"""
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, 'r') as f: 
                    return json.load(f)
            except:
                pass
        return {"total_sessions": 0, "total_minutes": 0}

    def save_stats(self, minutes_focused):
        """নতুন ফোকাস সেশনের ডেটা সেভ করবে"""
        self.stats_data["total_sessions"] += 1
        self.stats_data["total_minutes"] += int(minutes_focused)
        try:
            with open(STATS_FILE, 'w') as f: 
                json.dump(self.stats_data, f)
        except:
            pass
        self.update_stats_ui()

    def set_autostart(self, enable):
        """ল্যাপটপ অন করলেই অ্যাপ চালু হওয়ার জন্য রেজিস্ট্রি সেটআপ"""
        key = winreg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            registry_key = winreg.OpenKey(key, key_path, 0, winreg.KEY_ALL_ACCESS)
            if enable:
                winreg.SetValueEx(registry_key, "RasFocus", 0, winreg.REG_SZ, sys.executable)
            else:
                winreg.DeleteValue(registry_key, "RasFocus")
            winreg.CloseKey(registry_key)
        except Exception as e:
            print(f"Registry update failed: {e}")

    def setup_ui(self):
        """পুরো ইউজার ইন্টারফেস (UI) সেটআপ"""
        
        # Header Section
        self.header_frame = ctk.CTkFrame(self, fg_color="#1e1e2e", corner_radius=15, height=80)
        self.header_frame.pack(pady=20, padx=20, fill="x")
        self.title_label = ctk.CTkLabel(self.header_frame, text="⚡ RasFocus Pro Max", font=("Segoe UI", 32, "bold"), text_color="#a6e3a1")
        self.title_label.place(relx=0.5, rely=0.5, anchor="center")

        # TabView Setup
        self.tabview = ctk.CTkTabview(self, width=760, height=680)
        self.tabview.pack(pady=5, padx=20)
        self.tab_focus = self.tabview.add("Set Focus")
        self.tab_stats = self.tabview.add("Web Statistics")
        self.tab_settings = self.tabview.add("Settings")

        # ==========================================
        # 1. SET FOCUS TAB (Main Control Panel)
        # ==========================================
        
        # Input Section (Websites & Apps)
        self.input_frame = ctk.CTkFrame(self.tab_focus, fg_color="#282a36", corner_radius=15)
        self.input_frame.pack(pady=15, padx=20, fill="x")
        
        self.site_entry = ctk.CTkEntry(self.input_frame, placeholder_text="🌐 Block Websites (comma separated, e.g: facebook.com)", width=600, height=45)
        self.site_entry.pack(pady=15)
        
        self.app_entry = ctk.CTkEntry(self.input_frame, placeholder_text="📱 Block Apps (e.g. chrome.exe, telegram.exe)", width=600, height=45)
        self.app_entry.pack(pady=10)

        # Features Section (Switches for Strict/Hardcore Mode)
        self.features_frame = ctk.CTkFrame(self.tab_focus, fg_color="transparent")
        self.features_frame.pack(pady=10, padx=20, fill="x")
        
        self.internet_switch = ctk.CTkSwitch(self.features_frame, text="Kill All Internet", font=("Segoe UI", 15, "bold"), progress_color="#f38ba8")
        self.internet_switch.grid(row=0, column=0, padx=40, pady=10)
        
        self.strict_switch = ctk.CTkSwitch(self.features_frame, text="Strict Mode (Block TaskMgr)", font=("Segoe UI", 15, "bold"), progress_color="#fab387")
        self.strict_switch.grid(row=0, column=1, padx=40, pady=10)
        
        self.hardcore_switch = ctk.CTkSwitch(self.features_frame, text="Hardcore (No Unlock)", font=("Segoe UI", 15, "bold"), progress_color="#cba6f7")
        self.hardcore_switch.grid(row=1, column=0, columnspan=2, pady=10)

        # Time Configuration Section
        self.time_frame = ctk.CTkFrame(self.tab_focus, fg_color="#282a36", corner_radius=15)
        self.time_frame.pack(pady=10, padx=20, fill="x")
        
        self.time_label = ctk.CTkLabel(self.time_frame, text="Set Duration (Minutes)", font=("Segoe UI", 16, "bold"))
        self.time_label.pack(pady=5)

        self.preset_frame = ctk.CTkFrame(self.time_frame, fg_color="transparent")
        self.preset_frame.pack(pady=10)
        
        ctk.CTkButton(self.preset_frame, text="15m", width=120, height=40, fg_color="#89b4fa", command=lambda: self.set_time("15")).pack(side="left", padx=20)
        ctk.CTkButton(self.preset_frame, text="30m", width=120, height=40, fg_color="#89b4fa", command=lambda: self.set_time("30")).pack(side="left", padx=20)
        ctk.CTkButton(self.preset_frame, text="60m", width=120, height=40, fg_color="#89b4fa", command=lambda: self.set_time("60")).pack(side="left", padx=20)
        
        self.custom_time = ctk.CTkEntry(self.time_frame, placeholder_text="Custom Min", width=150, height=40, justify="center")
        self.custom_time.pack(pady=10)

        # Action Button & Progress
        self.start_btn = ctk.CTkButton(self.tab_focus, text="🚀 START FOCUS SESSION", font=("Segoe UI", 22, "bold"), fg_color="#f38ba8", hover_color="#d20f39", height=60, width=500, corner_radius=30, command=self.start_focus)
        self.start_btn.pack(pady=15)
        
        self.progress_bar = ctk.CTkProgressBar(self.tab_focus, width=500, height=15, progress_color="#a6e3a1")
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=5)
        
        self.status_label = ctk.CTkLabel(self.tab_focus, text="Ready to focus!", font=("Segoe UI", 18, "bold"), text_color="#a6adc8")
        self.status_label.pack(pady=5)

        # Emergency Unlock Section (Hidden by default)
        self.unlock_frame = ctk.CTkFrame(self.tab_focus, fg_color="#313244", corner_radius=10)
        self.unlock_msg = ctk.CTkLabel(self.unlock_frame, text="Emergency Unlock: Type exactly as below", text_color="#f9e2af")
        
        self.random_text_label = ctk.CTkTextbox(self.unlock_frame, height=60, width=500, font=("Consolas", 12))
        self.type_entry = ctk.CTkEntry(self.unlock_frame, placeholder_text="Type here...", width=350, height=40)
        self.unlock_btn = ctk.CTkButton(self.unlock_frame, text="Unlock", width=100, height=40, fg_color="#f38ba8", command=self.verify_unlock)

        # ==========================================
        # 2. WEB STATISTICS TAB
        # ==========================================
        self.stats_title = ctk.CTkLabel(self.tab_stats, text="📊 Your Lifetime Focus Report", font=("Segoe UI", 26, "bold"), text_color="#cba6f7")
        self.stats_title.pack(pady=30)
        
        self.stat_sessions_lbl = ctk.CTkLabel(self.tab_stats, text="0", font=("Segoe UI", 60, "bold"), text_color="#89b4fa")
        self.stat_sessions_lbl.pack(pady=10)
        ctk.CTkLabel(self.tab_stats, text="Total Successful Sessions", font=("Segoe UI", 16)).pack(pady=0)
        
        self.stat_minutes_lbl = ctk.CTkLabel(self.tab_stats, text="0", font=("Segoe UI", 60, "bold"), text_color="#a6e3a1")
        self.stat_minutes_lbl.pack(pady=30)
        ctk.CTkLabel(self.tab_stats, text="Total Minutes Focused", font=("Segoe UI", 16)).pack(pady=0)
        
        self.update_stats_ui()

        # ==========================================
        # 3. SETTINGS TAB
        # ==========================================
        self.settings_label = ctk.CTkLabel(self.tab_settings, text="⚙️ Preferences", font=("Segoe UI", 24, "bold"))
        self.settings_label.pack(pady=30)
        
        self.autostart_var = ctk.BooleanVar(value=False)
        self.autostart_checkbox = ctk.CTkCheckBox(self.tab_settings, text="Launch RasFocus on System Startup", font=("Segoe UI", 16), variable=self.autostart_var, command=lambda: self.set_autostart(self.autostart_var.get()))
        self.autostart_checkbox.pack(pady=20)
        
        ctk.CTkLabel(self.tab_settings, text="Software Information", font=("Segoe UI", 18, "bold"), text_color="#89b4fa").pack(pady=40)
        
        self.about_text = ctk.CTkLabel(self.tab_settings, text="RasFocus Pro Max - Elite Edition\nVersion 2.0.2\nDeveloped by Rasel Mia\n© 2026 RasFocus Inc.", font=("Segoe UI", 14), text_color="#45475a")
        self.about_text.pack(pady=10)

    def update_stats_ui(self):
        """স্ট্যাটিস্টিক্স ভিউ আপডেট করবে"""
        self.stat_sessions_lbl.configure(text=str(self.stats_data["total_sessions"]))
        self.stat_minutes_lbl.configure(text=str(self.stats_data["total_minutes"]))

    def set_time(self, minutes):
        """টাইম প্রেসেট বাটনের কাজ"""
        self.custom_time.delete(0, "end")
        self.custom_time.insert(0, minutes)

    def disable_inputs(self):
        """ফোকাস চলাকালীন সব ইনপুট ডিসেবল করবে"""
        self.site_entry.configure(state="disabled")
        self.app_entry.configure(state="disabled")
        self.custom_time.configure(state="disabled")
        self.internet_switch.configure(state="disabled")
        self.strict_switch.configure(state="disabled")
        self.hardcore_switch.configure(state="disabled")

    def start_focus(self, resume_data=None):
        """ফোকাস সেশন শুরু করার লজিক"""
        if not resume_data and not self.custom_time.get(): return
        
        self.is_focusing = True
        self.start_btn.configure(state="disabled", fg_color="#45475a", text="🔒 SESSION ACTIVE")
        self.tabview.set("Set Focus")
        self.disable_inputs()

        if not resume_data:
            self.total_duration_minutes = int(self.custom_time.get())
            self.end_time = datetime.now() + timedelta(minutes=self.total_duration_minutes)
            self.sites = [s.strip() for s in self.site_entry.get().split(',') if s.strip()]
            self.apps = [a.strip() for a in self.app_entry.get().split(',') if a.strip()]
            internet = self.internet_switch.get()
            strict = self.strict_switch.get()
            hardcore = self.hardcore_switch.get()
            
            # State সেভ করা হচ্ছে
            with open(STATE_FILE, 'w') as f:
                json.dump({
                    "end_time": self.end_time.timestamp(), 
                    "total_m": self.total_duration_minutes, 
                    "sites": self.sites, 
                    "apps": self.apps, 
                    "internet": internet, 
                    "strict": strict, 
                    "hardcore": hardcore
                }, f)
        else:
            # রিস্টার্ট এর পর রিস্টোর করা হচ্ছে
            self.end_time = datetime.fromtimestamp(resume_data["end_time"])
            self.total_duration_minutes = resume_data.get("total_m", 1)
            self.sites = resume_data["sites"]
            self.apps = resume_data["apps"]
            internet = resume_data.get("internet", False)
            strict = resume_data.get("strict", False)
            hardcore = resume_data.get("hardcore", False)

        # Full Internet Block Feature
        if internet:
            subprocess.run(f'netsh advfirewall firewall add rule name="{FIREWALL_RULE_NAME}" dir=out action=block remoteip=any', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Unlock UI setup (Hardcore mode অফ থাকলে)
        if not hardcore:
            self.unlock_text = "I am breaking my promise. " + "".join(random.choices(string.ascii_letters + string.digits, k=15))
            self.unlock_msg.pack(pady=5)
            self.random_text_label.pack(pady=5)
            self.random_text_label.configure(state="normal")
            self.random_text_label.delete("0.0", "end")
            self.random_text_label.insert("0.0", self.unlock_text)
            self.random_text_label.configure(state="disabled")
            self.type_entry.pack(side="left", padx=15, pady=10)
            self.unlock_btn.pack(side="right", padx=15, pady=10)
            self.unlock_frame.pack(pady=10, padx=20, fill="x")

        # ফোকাস ইঞ্জিন থ্রেডে রান করানো
        threading.Thread(target=self.focus_engine, args=(strict,), daemon=True).start()

    def verify_unlock(self):
        """ইমার্জেন্সি আনলক চেক করবে"""
        if self.type_entry.get() == self.unlock_text:
            self.stop_focus(completed=False)
        else:
            self.status_label.configure(text="❌ Incorrect Code!", text_color="#f38ba8")

    def focus_engine(self, strict):
        """মূল ব্লকিং ইঞ্জিন যা ব্যাকগ্রাউন্ডে চলবে"""
        strict_apps = self.apps.copy()
        if strict: 
            strict_apps.extend(['taskmgr.exe', 'cmd.exe', 'powershell.exe', 'regedit.exe'])
            
        total_seconds = self.total_duration_minutes * 60

        while datetime.now() < self.end_time and self.is_focusing:
            try:
                # ওয়েবসাইট ব্লক
                with open(HOSTS_PATH, 'r+') as f:
                    content = f.read()
                    for site in self.sites:
                        if site not in content: 
                            f.write(f"{REDIRECT} {site}\n")
                            
                # অ্যাপ ব্লক
                for app in strict_apps:
                    subprocess.run(['taskkill', '/F', '/IM', app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except: 
                pass
            
            # প্রোগ্রেস বার এবং টাইম আপডেট
            remaining = self.end_time - datetime.now()
            progress_val = max(0, min(1, 1 - (remaining.total_seconds() / total_seconds)))
            self.progress_bar.set(progress_val)
            
            self.status_label.configure(text=f"🔥 Remaining: {str(remaining).split('.')[0]}", text_color="#a6e3a1")
            time.sleep(2) # প্রতি ২ সেকেন্ড পর পর চেক করবে
            
        if self.is_focusing: 
            self.stop_focus(completed=True)

    def stop_focus(self, completed=True):
        """ফোকাস সেশন শেষ বা বাতিল করার লজিক"""
        self.is_focusing = False
        
        # আনব্লক ইন্টারনেট
        subprocess.run(f'netsh advfirewall firewall delete rule name="{FIREWALL_RULE_NAME}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # আনব্লক সাইটস
        try:
            with open(HOSTS_PATH, 'r') as f: 
                lines = f.readlines()
            with open(HOSTS_PATH, 'w') as f:
                for line in lines:
                    if not any(site in line for site in self.sites): 
                        f.write(line)
        except: 
            pass
            
        # স্টেট মুছে ফেলা
        if os.path.exists(STATE_FILE): 
            os.remove(STATE_FILE)
            
        if completed: 
            self.save_stats(self.total_duration_minutes)
            
        # UI রিসেট
        self.start_btn.configure(state="normal", fg_color="#f38ba8", text="🚀 START FOCUS SESSION")
        self.status_label.configure(text="Session Complete!" if completed else "Aborted.", text_color="#89b4fa")
        
        self.site_entry.configure(state="normal")
        self.app_entry.configure(state="normal")
        self.custom_time.configure(state="normal")
        self.internet_switch.configure(state="normal")
        self.strict_switch.configure(state="normal")
        self.hardcore_switch.configure(state="normal")
        
        self.unlock_frame.pack_forget()

    def check_previous_state(self):
        """অ্যাপ রান করার সময় চেক করবে আগে কোনো সেশন চলছিল কি না"""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    if datetime.now() < datetime.fromtimestamp(data["end_time"]):
                        self.start_focus(resume_data=data)
            except: 
                pass

    def withdraw_to_tray(self):
        """উইন্ডো ক্লোজ করলে সিস্টেমে ট্রিতে চলে যাবে"""
        self.withdraw()
        image = Image.new('RGB', (64, 64), color=(40, 42, 54))
        menu = (item('Open RasFocus', self.show_window),)
        self.tray_icon = pystray.Icon("RasFocus", image, "RasFocus Background Mode", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self):
        """সিস্টেম ট্রে থেকে আবার উইন্ডো ওপেন করবে"""
        self.tray_icon.stop()
        self.deiconify()

if __name__ == "__main__":
    # অ্যাডমিন পারমিশন চেক
    if not ctypes.windll.shell32.IsUserAnAdmin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
        
    app = FocusApp()
    app.mainloop()
