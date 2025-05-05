import customtkinter as ctk
from PIL import Image, ImageOps
import os
import openai
import subprocess
import threading
from datetime import datetime

# === OpenAI Key ===
with open("api_key.txt", "r") as f:
    openai.api_key = f.read().strip()

# === File Paths ===
CHAT_LOG    = "chat_history.txt"
REPORT_FILE = "security_report.txt"

class CyberBuddyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CyberBuddy - Chatbot & Security Scanner")
        self.geometry("600x800")
        self.resizable(True, True)
        self.last_scan_output = None

        # === Load Assets ===
        self.title_img = ctk.CTkImage(light_image=Image.open("assets/CyberBuddy_title.png"), size=(700, 230))
        self.bot_icon = ctk.CTkImage(ImageOps.fit(Image.open("assets/bot_icon.png"), (90, 90)), size=(90, 90))
        self.user_icon = ctk.CTkImage(ImageOps.fit(Image.open("assets/user_icon.png"), (90, 90)), size=(90, 90))
        self.send_icon = ctk.CTkImage(Image.open("assets/send_icon.png").resize((60, 60)))

        self.configure(fg_color="#1b1d38")

        # === Title ===
        self.title_label = ctk.CTkLabel(self, image=self.title_img, text="")
        self.title_label.place(relx=0.5, rely=0.01, anchor="n")

        # === Scrollable Chat Frame ===
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#0a0a1e")
        self.scroll_frame.place(relx=0.5, rely=0.55, anchor="center", relwidth=0.97, relheight=0.73)

        # === Entry Area ===
        self.entry_frame = ctk.CTkFrame(self, fg_color="white", width=560, height=60, corner_radius=12)
        self.entry_frame.place(relx=0.5, rely=0.975, anchor="s")

        self.msg_entry = ctk.CTkEntry(self.entry_frame, placeholder_text="Type messages...", width=460, fg_color="white", text_color="black", corner_radius=12, height=30)
        self.msg_entry.place(x=10, y=15)

        self.send_button = ctk.CTkButton(self.entry_frame, image=self.send_icon, text="", width=35, height=35, command=self.send_message, fg_color="white")
        self.send_button.place(x=510, y=12)

    def send_message(self):
        msg = self.msg_entry.get().strip()
        if msg:
            self.add_message(msg, sender="user")
            if msg.lower() == "scan report":
                threading.Thread(target=self.scan).start()
            elif "recommendation" in msg.lower() and self.last_scan_output:
                threading.Thread(target=self.ask_openai, args=("Based on the following scan report, provide recommendations:\n" + self.last_scan_output,)).start()
            else:
                threading.Thread(target=self.ask_openai, args=(msg,)).start()
            self.msg_entry.delete(0, "end")

    def scan(self):
        def run_command(cmd):
            p = subprocess.run(['powershell', '-Command', cmd], capture_output=True, text=True, encoding='utf-8', errors='ignore')
            return p.stdout.strip()

        out = []
        av = run_command('Get-MpComputerStatus|Select -ExpandProperty AMProductName')
        out.append(f"🛡 Antivirus: {av}" if av and "AMProductName" not in av else "⚠ No antivirus or Defender disabled")
        fw = run_command('Get-NetFirewallProfile|Select -ExpandProperty Enabled')
        out.append("🔥 Firewall: ON" if "True" in fw else "🔥 Firewall: OFF")
        upd = run_command('(Get-HotFix|Sort InstalledOn -Descending|Select -ExpandProperty InstalledOn -First 1).ToString("yyyy‑MM‑dd HH:mm:ss")')
        out.append(f"🔄 Last Update: {upd or 'none found'}")
        pwd = run_command('net user $env:UserName|findstr /C:"Password last set"')
        if "Password last set" in pwd:
            when = pwd.split("Password last set")[-1].strip()
            out.append(f"🔑 Password set: {when}")
        else:
            out.append("⚠ Cannot get password date")
        cli = r"C:\\Program Files\\Windows Defender\\MpCmdRun.exe"
        if os.path.exists(cli):
            out.append("🔍 Running malware scan…")
            p = subprocess.run(f'"{cli}" -Scan -ScanType 1', shell=True, capture_output=True, text=True)
            txt = p.stdout + p.stderr
            if "No threats" in txt or p.returncode == 2:
                out.append("✅ No threats detected")
            else:
                thr = [l for l in txt.splitlines() if "Threat" in l]
                out.append("❗ Threats: " + (", ".join(thr) or "possible issues"))
        else:
            out.append("⚠ Defender CLI not found")

        self.last_scan_output = "\n".join(out)

        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write("=== SECURITY REPORT ===\n" + self.last_scan_output)

        self.add_message(self.last_scan_output, sender="bot")

    def ask_openai(self, msg):
        try:
            resp = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are CyberBuddy, a helpful cybersecurity assistant. Provide accurate and detailed recommendations when asked to interpret system scan reports."},
                    {"role": "user", "content": msg}
                ]
            )
            answer = resp.choices[0].message.content.strip()
        except Exception as e:
            answer = f"❌ Chat Error: {e}"
        self.add_message(answer, sender="bot")

    def add_message(self, msg, sender):
        wrapper = ctk.CTkFrame(self.scroll_frame, fg_color="#0a0a1e")
        bubble = ctk.CTkLabel(
            wrapper,
            text=msg,
            fg_color="#3B82F6",
            text_color="white",
            corner_radius=20,
            anchor="w",
            justify="left",
            wraplength=460,
            padx=15,
            pady=10
        )
        icon = self.bot_icon if sender == "bot" else self.user_icon
        icon_label = ctk.CTkLabel(wrapper, image=icon, text="")

        if sender == "user":
            wrapper.grid_columnconfigure(0, weight=1)
            bubble.grid(row=0, column=0, sticky="e", padx=(10, 5))
            icon_label.grid(row=0, column=1, padx=(5, 10))
            wrapper.pack(anchor="e", padx=10, pady=5, fill="x")
        else:
            wrapper.grid_columnconfigure(2, weight=1)
            icon_label.grid(row=0, column=0, padx=(10, 5))
            bubble.grid(row=0, column=1, sticky="w", padx=(5, 0))
            wrapper.pack(anchor="w", padx=10, pady=5, fill="x")

if __name__ == "__main__":
    app = CyberBuddyApp()
    app.mainloop()
