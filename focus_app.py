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

# Matplotlib for Real Charts (FocusMe Style)
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# থিম - FocusMe এর মতো White/Light Background
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ফাইল পাথ
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
        self.title("RasFocus Pro Max - Elite Edition")
        self.geometry("950x750")
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
            try:
                with open(STATS_FILE, 'r') as f: 
                    return json.load(f)
            except:
                pass
        # Default mock data for the chart to look like FocusMe initially
        return {
            "total_sessions": 0, 
            "total_minutes": 0,
            "category_data": {"Productivity": 41, "Social Media": 23, "Entertainment": 14, "News": 7, "Others": 15}
        }

    def save_stats(self, minutes_focused):
        self.stats_data["total_sessions"] += 1
        self.stats_data["total_minutes"] += int(minutes_focused)
        # Randomly updating chart data for visualization
        self.stats_data["category_data"]["Productivity"] += random.randint(1, 5)
        try:
            with open(STATS_FILE, 'w') as f: 
                json.dump(self.stats_data, f)
        except:
            pass
        self.update_chart()

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
        except:
            pass

    def setup_ui(self):
        # Header - Light theme friendly
        self.header_frame = ctk.CTkFrame(self, fg_color="#3b82f6", corner_radius=0, height=80)
        self.header_frame.pack(fill="x")
        self.title_label = ctk.CTkLabel(self.header_frame, text="⚡ RasFocus Pro Max", font=("Segoe UI", 28, "bold"), text_color="white")
        self.title_label.place(relx=0.5, rely=0.5, anchor="center")

        # Main TabView
        self.tabview = ctk.CTkTabview(self, width=900, height=620, fg_color="#f3f4f6", segmented_button_selected_color="#2563eb")
        self.tabview.pack(pady=10, padx=20)
        
        # Tabs
        self.tab_stats = self.tabview.add("Statistics (Dashboard)")
        self.tab_focus = self.tabview.add("Set Focus Rules")
        self.tab_settings = self.tabview.add("Settings")

        self.setup_statistics_tab()
        self.setup_focus_tab()
        self.setup_settings_tab()

    def setup_statistics_tab(self):
        """FocusMe স্টাইলের ড্যাশবোর্ড ও চার্ট"""
        self.tab_stats.grid_columnconfigure(0, weight=2)
        self.tab_stats.grid_columnconfigure(1, weight=1)

        # Left Side: Table / Data View
        self.table_frame = ctk.CTkFrame(self.tab_stats, fg_color="white", corner_radius=10)
        self.table_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(self.table_frame, text="Web & App Statistics", font=("Segoe UI", 18, "bold"), text_color="#1f2937").pack(pady=10, anchor="w", padx=20)
        
        # Mock Table Header
        header_frame = ctk.CTkFrame(self.table_frame, fg_color="#e5e7eb", corner_radius=5)
        header_frame.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(header_frame, text="NAME", font=("Segoe UI", 12, "bold"), text_color="#4b5563", width=200, anchor="w").pack(side="left", padx=10)
        ctk.CTkLabel(header_frame, text="TIME SPENT", font=("Segoe UI", 12, "bold"), text_color="#4b5563", width=100).pack(side="left", padx=10)
        
        # Mock List of Sites
        sites_mock = [("facebook.com", "21m 6s"), ("youtube.com", "11m 59s"), ("instagram.com", "7m 4s"), ("twitter.com", "4m 19s")]
        for site, t_spent in sites_mock:
            row = ctk.CTkFrame(self.table_frame, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=2)
            ctk.CTkLabel(row, text=f"🔴 {site}", font=("Segoe UI", 14), text_color="#374151", width=200, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row, text=t_spent, font=("Segoe UI", 14), text_color="#6b7280", width=100).pack(side="left", padx=10)

        # Right Side: Matplotlib Donut Chart
        self.chart_frame = ctk.CTkFrame(self.tab_stats, fg_color="white", corner_radius=10)
        self.chart_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(self.chart_frame, text="CHART OVERVIEW", font=("Segoe UI", 14, "bold"), text_color="#6b7280").pack(pady=10)
        
        self.fig = Figure(figsize=(4, 4), dpi=100)
        self.fig.patch.set_facecolor('white')
        self.ax = self.fig.add_subplot(111)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(pady=10)
        
        self.update_chart()

        # Bottom Summary
        self.summary_frame = ctk.CTkFrame(self.tab_stats, fg_color="white", corner_radius=10)
        self.summary_frame.grid(row=1, column=0, columnspan=2, pady=10, padx=10, sticky="ew")
        self.stat_sessions_lbl = ctk.CTkLabel(self.summary_frame, text=f"Total Sessions: {self.stats_data['total_sessions']}", font=("Segoe UI", 16, "bold"), text_color="#2563eb")
        self.stat_sessions_lbl.pack(side="left", padx=40, pady=15)
        self.stat_minutes_lbl = ctk.CTkLabel(self.summary_frame, text=f"Total Minutes Blocked: {self.stats_data['total_minutes']}", font=("Segoe UI", 16, "bold"), text_color="#10b981")
        self.stat_minutes_lbl.pack(side="right", padx=40, pady=15)

    def update_chart(self):
        self.ax.clear()
        labels = list(self.stats_data["category_data"].keys())
        sizes = list(self.stats_data["category_data"].values())
        colors = ['#3b82f6', '#10b981', '#fbbf24', '#f43f5e', '#8b5cf6']
        
        # Donut Chart Logic
        wedges, texts, autotexts = self.ax.pie(sizes, labels=None, autopct='%1.0f%%', startangle=90, colors=colors, pctdistance=0.75)
        centre_circle = matplotlib.patches.Circle((0,0),0.50,fc='white')
        self.ax.add_patch(centre_circle)
        self.ax.axis('equal')  
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
            autotext.set_weight('bold')
            
        self.ax.legend(wedges, labels, loc="lower center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False, fontsize=9)
        self.canvas.draw()

    def setup_focus_tab(self):
        """Set Focus Rules Tab (Inputs and Toggles)"""
        self.input_frame = ctk.CTkFrame(self.tab_focus, fg_color="white", corner_radius=10)
        self.input_frame.pack(pady=15, padx=40, fill="x")
        
        ctk.CTkLabel(self.input_frame, text="Blocklist Configuration", font=("Segoe UI", 16, "bold"), text_color="#374151").pack(pady=10, anchor="w", padx=20)
        self.site_entry = ctk.CTkEntry(self.input_frame, placeholder_text="🌐 Websites (e.g: facebook.com, youtube.com)", width=700, height=40, fg_color="#f9fafb", border_color="#d1d5db", text_color="black")
        self.site_entry.pack(pady=10)
        self.app_entry = ctk.CTkEntry(self.input_frame, placeholder_text="📱 Applications (e.g: chrome.exe, telegram.exe)", width=700, height=40, fg_color="#f9fafb", border_color="#d1d5db", text_color="black")
        self.app_entry.pack(pady=10)

        self.features_frame = ctk.CTkFrame(self.tab_focus, fg_color="white", corner_radius=10)
        self.features_frame.pack(pady=10, padx=40, fill="x")
        self.internet_switch = ctk.CTkSwitch(self.features_frame, text="Kill All Internet Connection", font=("Segoe UI", 14, "bold"), text_color="#1f2937", progress_color="#ef4444")
        self.internet_switch.grid(row=0, column=0, padx=40, pady=15)
        self.strict_switch = ctk.CTkSwitch(self.features_frame, text="Strict Mode (Block Task Manager)", font=("Segoe UI", 14, "bold"), text_color="#1f2937", progress_color="#f59e0b")
        self.strict_switch.grid(row=0, column=1, padx=40, pady=15)
        self.hardcore_switch = ctk.CTkSwitch(self.features_frame, text="Hardcore Mode (No Early Unlock)", font=("Segoe UI", 14, "bold"), text_color="#1f2937", progress_color="#8b5cf6")
        self.hardcore_switch.grid(row=1, column=0, columnspan=2, pady=10)

        self.time_frame = ctk.CTkFrame(self.tab_focus, fg_color="white", corner_radius=10)
        self.time_frame.pack(pady=10, padx=40, fill="x")
        ctk.CTkLabel(self.time_frame, text="Schedule Duration", font=("Segoe UI", 16, "bold"), text_color="#374151").pack(pady=10)
        
        self.preset_frame = ctk.CTkFrame(self.time_frame, fg_color="transparent")
        self.preset_frame.pack(pady=5)
        ctk.CTkButton(self.preset_frame, text="15m", width=100, fg_color="#3b82f6", command=lambda: self.set_time("15")).pack(side="left", padx=10)
        ctk.CTkButton(self.preset_frame, text="30m", width=100, fg_color="#3b82f6", command=lambda: self.set_time("30")).pack(side="left", padx=10)
        ctk.CTkButton(self.preset_frame, text="60m", width=100, fg_color="#3b82f6", command=lambda: self.set_time("60")).pack(side="left", padx=10)
        self.custom_time = ctk.CTkEntry(self.preset_frame, placeholder_text="Custom Min", width=100, fg_color="#f9fafb", text_color="black")
        self.custom_time.pack(side="left", padx=10)

        self.start_btn = ctk.CTkButton(self.tab_focus, text="START FOCUS", font=("Segoe UI", 18, "bold"), fg_color="#10b981", hover_color="#059669", height=50, width=400, command=self.start_focus)
        self.start_btn.pack(pady=20)
        
        self.status_label = ctk.CTkLabel(self.tab_focus, text="Ready to boost productivity!", font=("Segoe UI", 14), text_color="#6b7280")
        self.status_label.pack()

        # Unlock Frame
        self.unlock_frame = ctk.CTkFrame(self.tab_focus, fg_color="#fee2e2", corner_radius=10)
        self.unlock_msg = ctk.CTkLabel(self.unlock_frame, text="Emergency Unlock: Type exactly as below", text_color="#b91c1c", font=("Segoe UI", 12, "bold"))
        self.random_text_label = ctk.CTkTextbox(self.unlock_frame, height=50, width=600, fg_color="white", text_color="black")
        self.type_entry = ctk.CTkEntry(self.unlock_frame, placeholder_text="Type here to abort...", width=400, fg_color="white", text_color="black")
        self.unlock_btn = ctk.CTkButton(self.unlock_frame, text="Abort", width=100, fg_color="#ef4444", command=self.verify_unlock)

    def setup_settings_tab(self):
        """Settings and About Tab"""
        self.settings_frame = ctk.CTkFrame(self.tab_settings, fg_color="white", corner_radius=10)
        self.settings_frame.pack(pady=20, padx=40, fill="both", expand=True)
        
        ctk.CTkLabel(self.settings_frame, text="Application Settings", font=("Segoe UI", 20, "bold"), text_color="#1f2937").pack(pady=20)
        self.autostart_var = ctk.BooleanVar(value=False)
        self.autostart_checkbox = ctk.CTkCheckBox(self.settings_frame, text="Launch RasFocus automatically on Windows Startup", font=("Segoe UI", 14), text_color="#374151", variable=self.autostart_var, command=lambda: self.set_autostart(self.autostart_var.get()))
        self.autostart_checkbox.pack(pady=10)
        
        ctk.CTkLabel(self.settings_frame, text="About", font=("Segoe UI", 18, "bold"), text_color="#1f2937").pack(pady=30)
        about_info = "RasFocus Pro Max - Elite Edition\nVersion 3.0\n\nA premium productivity tool designed to eliminate distractions.\n\nDeveloped by Rasel Mia\n© 2026 RasFocus Inc."
        ctk.CTkLabel(self.settings_frame, text=about_info, font=("Segoe UI", 14), text_color="#4b5563", justify="center").pack(pady=10)

    def set_time(self, minutes):
        self.custom_time.delete(0, "end")
        self.custom_time.insert(0, minutes)

    def disable_inputs(self):
        self.site_entry.configure(state="disabled")
        self.app_entry.configure(state="disabled")
        self.custom_time.configure(state="disabled")
        self.internet_switch.configure(state="disabled")
        self.strict_switch.configure(state="disabled")
        self.hardcore_switch.configure(state="disabled")

    def start_focus(self, resume_data=None):
        if not resume_data and not self.custom_time.get(): return
        
        self.is_focusing = True
        self.start_btn.configure(state="disabled", fg_color="#9ca3af", text="SESSION ACTIVE")
        self.disable_inputs()

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
            self.unlock_text = "I am breaking my promise. " + "".join(random.choices(string.ascii_letters + string.digits, k=15))
            self.unlock_msg.pack(pady=5)
            self.random_text_label.pack(pady=5)
            self.random_text_label.configure(state="normal")
            self.random_text_label.delete("0.0", "end")
            self.random_text_label.insert("0.0", self.unlock_text)
            self.random_text_label.configure(state="disabled")
            self.type_entry.pack(side="left", padx=30, pady=10)
            self.unlock_btn.pack(side="right", padx=30, pady=10)
            self.unlock_frame.pack(pady=15, padx=40, fill="x")

        threading.Thread(target=self.focus_engine, args=(strict,), daemon=True).start()

    def verify_unlock(self):
        if self.type_entry.get() == self.unlock_text:
            self.stop_focus(completed=False)
        else:
            self.status_label.configure(text="❌ Incorrect Unlock Code!", text_color="#ef4444")

    def focus_engine(self, strict):
        strict_apps = self.apps.copy()
        if strict: 
            strict_apps.extend(['taskmgr.exe', 'cmd.exe', 'powershell.exe', 'regedit.exe'])

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
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.status_label.configure(text=f"⏳ Time Remaining: {hours:02d}:{minutes:02d}:{seconds:02d}", text_color="#2563eb")
            time.sleep(2)
            
        if self.is_focusing: 
            self.stop_focus(completed=True)

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
            self.stat_sessions_lbl.configure(text=f"Total Sessions: {self.stats_data['total_sessions']}")
            self.stat_minutes_lbl.configure(text=f"Total Minutes Blocked: {self.stats_data['total_minutes']}")
            
        self.start_btn.configure(state="normal", fg_color="#10b981", text="START FOCUS")
        self.status_label.configure(text="Session Complete! Check Statistics." if completed else "Session Aborted.", text_color="#374151")
        
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
            except: pass

    def withdraw_to_tray(self):
        self.withdraw()
        image = Image.new('RGB', (64, 64), color=(59, 130, 246))
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
