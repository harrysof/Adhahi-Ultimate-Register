# -*- coding: utf-8 -*-
"""
adhahi.dz – Auto-Register Bot  (GUI)
=====================================
Left panel  : credentials + wilaya selection + controls
Right panel : live 24/7 log

pip install selenium webdriver-manager
"""

import json, os, sys, threading, time, tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import urllib.request, urllib.error
from datetime import datetime

def resource_path(filename: str) -> str:
    """Resolve asset paths for both normal run and PyInstaller exe."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, filename)

CONFIG_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adhahi_config.json")
API_URL      = "https://adhahi.dz/api/v1/public/wilaya-quotas"
REGISTER_URL = "https://adhahi.dz/register"

# Cache ChromeDriver path once at startup — avoids re-downloading on every browser launch
_CHROMEDRIVER_PATH = None
def _get_chromedriver_path():
    global _CHROMEDRIVER_PATH
    if _CHROMEDRIVER_PATH is None:
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            os.environ["WDM_LOG"] = "0"
            _CHROMEDRIVER_PATH = ChromeDriverManager().install()
        except Exception as e:
            raise RuntimeError(f"ChromeDriver setup failed: {e}")
    return _CHROMEDRIVER_PATH

ALL_WILAYAS = [
    ("01","Adrar"),          ("02","Chlef"),           ("03","Laghouat"),
    ("04","Oum El Bouaghi"), ("05","Batna"),            ("06","Béjaïa"),
    ("07","Biskra"),         ("08","Béchar"),           ("09","Blida"),
    ("10","Bouira"),         ("11","Tamanrasset"),      ("12","Tébessa"),
    ("13","Tlemcen"),        ("14","Tiaret"),           ("15","Tizi Ouzou"),
    ("16","Alger"),          ("17","Djelfa"),           ("18","Jijel"),
    ("19","Sétif"),          ("20","Saïda"),            ("21","Skikda"),
    ("22","Sidi Bel Abbès"), ("23","Annaba"),           ("24","Guelma"),
    ("25","Constantine"),    ("26","Médéa"),            ("27","Mostaganem"),
    ("28","M'Sila"),         ("29","Mascara"),          ("30","Ouargla"),
    ("31","Oran"),           ("32","El Bayadh"),        ("33","Illizi"),
    ("34","Bordj Bou Arréridj"), ("35","Boumerdès"),   ("36","El Tarf"),
    ("37","Tindouf"),        ("38","Tissemsilt"),       ("39","El Oued"),
    ("40","Khenchela"),      ("41","Souk Ahras"),       ("42","Tipaza"),
    ("43","Mila"),           ("44","Aïn Defla"),        ("45","Naâma"),
    ("46","Aïn Témouchent"), ("47","Ghardaïa"),         ("48","Relizane"),
    ("49","Timimoun"),       ("50","Bordj Badji Mokhtar"), ("51","Ouled Djellal"),
    ("52","Béni Abbès"),     ("53","In Salah"),         ("54","In Guezzam"),
    ("55","Touggourt"),      ("56","Djanet"),           ("57","El M'Ghair"),
    ("58","El Meniaa"),
]

DEFAULT_CFG = {
    "nin":"", "cni":"", "phone":"", "email":"", "password":"",
    "payment":"cash", "bot_token":"", "chat_id":"",
    "target_wilayas": ["16","35","09","42","10","15","26","44","02","54"],
    "check_interval": 2,
}

# ── Colour palette (GitHub-dark inspired) ─────────────────────────
BG      = "#0d1117"
PANEL   = "#161b22"
BORDER  = "#30363d"
ACCENT  = "#1f6feb"
GREEN   = "#3fb950"
YELLOW  = "#d29922"
RED     = "#f85149"
MUTED   = "#8b949e"
TEXT    = "#e6edf3"
ENTRY   = "#010409"

# ─────────────────────────────────────────────────────────────────
def now():  return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def hms():  return datetime.now().strftime("%H:%M:%S")

def load_cfg():
    if os.path.exists(CONFIG_FILE):
        try:
            d = json.load(open(CONFIG_FILE, encoding="utf-8"))
            c = DEFAULT_CFG.copy(); c.update(d); return c
        except: pass
    return DEFAULT_CFG.copy()

def save_cfg(c):
    json.dump(c, open(CONFIG_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

def fetch_quotas(retries=2, timeout=20):
    """Fetch quota data with silent retries on timeout."""
    req = urllib.request.Request(API_URL, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    })
    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(2)  # brief pause before retry
    raise last_err

def available_wilayas(data, targets):
    avail = {str(e.get("wilayaCode","")).zfill(2): e.get("available",False) for e in data}
    return [str(w).zfill(2) for w in targets if avail.get(str(w).zfill(2), False)]

def send_telegram(token, chat_id, text):
    if not token or not chat_id: return
    try:
        p = json.dumps({"chat_id":chat_id,"text":text,"parse_mode":"HTML"}).encode()
        urllib.request.urlopen(urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=p, headers={"Content-Type":"application/json"}, method="POST"
        ), timeout=10)
    except: pass


# ── Selenium fill_and_submit ──────────────────────────────────────
def fill_and_submit(cfg, wilaya, log_fn):
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.service import Service
    except ImportError:
        log_fn("ERR", "selenium / webdriver-manager not installed!"); return

    p = cfg.copy(); p["wilaya"] = wilaya; tag = f"[W{wilaya}]"

    try:
        log_fn("INFO", f"{tag} Opening Chrome …")

        opts = webdriver.ChromeOptions()
        opts.add_argument("--start-maximized")
        log_fn("INFO", f"{tag} Locating ChromeDriver …")
        driver = webdriver.Chrome(
            service=Service(_get_chromedriver_path()),
            options=opts)
        log_fn("OK",   f"{tag} Chrome launched")
        wait = WebDriverWait(driver, 30)

    except Exception as e:
        log_fn("ERR", f"{tag} ❌ Failed to launch Chrome: {e}")
        log_fn("ERR", f"{tag}    Make sure Google Chrome is installed on this PC.")
        return

    def jc(el):
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.2)
        driver.execute_script("arguments[0].click();", el)

    def combo(fid, search, label):
        inp = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"#{fid}")))
        jc(inp); time.sleep(0.3)
        inp.send_keys(Keys.CONTROL+"a"); inp.send_keys(Keys.DELETE)
        inp.send_keys(search); time.sleep(2.0)
        try:
            jc(wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,
                "li[role='option']:first-child, [role='listbox'] li:first-child"))))
        except:
            inp.send_keys(Keys.ARROW_DOWN); time.sleep(0.3); inp.send_keys(Keys.RETURN)
        log_fn("OK", f"{tag} ✓ {label}")

    try:
        driver.get(REGISTER_URL)
        log_fn("OK", f"{tag} Page loaded")

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,"#reg-nin"))).send_keys(p["nin"])
        log_fn("OK", f"{tag} NIN filled")
        driver.find_element(By.CSS_SELECTOR,"#reg-cni").send_keys(p["cni"])
        log_fn("OK", f"{tag} CNI filled")
        driver.find_element(By.CSS_SELECTOR,"#reg-phone").send_keys(p["phone"])
        log_fn("OK", f"{tag} Phone filled")
        if p.get("email"):
            driver.find_element(By.CSS_SELECTOR,"#reg-email").send_keys(p["email"])
            log_fn("OK", f"{tag} Email filled")
        driver.find_element(By.CSS_SELECTOR,"#reg-password").send_keys(p["password"])
        driver.find_element(By.CSS_SELECTOR,"#reg-confirm-password").send_keys(p["password"])
        log_fn("OK", f"{tag} Password filled")

        combo("reg-wilaya", p["wilaya"], f"Wilaya {p['wilaya']}")
        time.sleep(2)
        try:    combo("reg-commune","","Commune (first available)")
        except: log_fn("WARN", f"{tag} Commune step unavailable")

        time.sleep(1.5)
        try:
            radios = wait.until(lambda d: d.find_elements(By.CSS_SELECTOR,"[role='radio']"))
            idx = {"cash":0,"tpe":1,"online":2}.get(p.get("payment","cash").lower(), 0)
            jc(radios[idx] if idx < len(radios) else radios[0])
            log_fn("OK", f"{tag} Payment: {p.get('payment','cash')}")
        except Exception as e:
            log_fn("WARN", f"{tag} Payment select failed: {e}")

        time.sleep(0.5)
        try:
            cb = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR,"#reg-law-1807-checkbox")))
            if not cb.is_selected(): jc(cb)
            log_fn("OK", f"{tag} Privacy checkbox checked")
        except Exception as e:
            log_fn("WARN", f"{tag} Checkbox error: {e}")

        # ── CAPTCHA + Submit — done manually by user ──────────
        log_fn("INFO", f"{tag} 🔒 CAPTCHA + Submit — please complete in Chrome")
        send_telegram(cfg["bot_token"], cfg["chat_id"],
            f"🔒 CAPTCHA needed – Wilaya {wilaya}\nFill CAPTCHA & submit in browser\n⏰ {now()}")

    except Exception as e:
        log_fn("ERR", f"{tag} Browser error: {e}")
        send_telegram(cfg["bot_token"], cfg["chat_id"],
            f"❌ Error – Wilaya {wilaya}: {e}")
    finally:
        log_fn("INFO", f"{tag} Browser left open — close manually when done")


# ══════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("adhahi.dz  —  Auto-Register Bot")
        self.configure(bg=BG)
        self.minsize(1100, 660)
        self.geometry("1280x760")
        try:
            self.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass  # icon.ico not found — falls back to default feather

        self.cfg      = load_cfg()
        self._running  = False
        self._api_active = set() # wilayas currently open in the API
        self._attempt  = 0

        # tkinter vars
        self._fvars: dict[str, tk.StringVar]   = {}
        self._wvars: dict[str, tk.BooleanVar]  = {}
        self._pay   = tk.StringVar(value=self.cfg.get("payment","cash"))
        self._ivar  = tk.IntVar(value=self.cfg.get("check_interval",2))

        self._build()
        self._load_fields()
        self.protocol("WM_DELETE_WINDOW", self._quit)

    # ─────────────────────────────────────────────────────────────
    # BUILD
    # ─────────────────────────────────────────────────────────────
    def _build(self):
        # Two-pane horizontal split
        pane = tk.PanedWindow(self, orient="horizontal",
                              bg=BORDER, sashwidth=3, sashrelief="flat", bd=0)
        pane.pack(fill="both", expand=True)

        left  = tk.Frame(pane, bg=PANEL, width=430)
        right = tk.Frame(pane, bg=BG)

        pane.add(left,  minsize=360, stretch="never")
        pane.add(right, minsize=420, stretch="always")

        self._build_left(left)
        self._build_right(right)

    # ══════════════════════════════════════════════════════════════
    #  LEFT PANEL
    # ══════════════════════════════════════════════════════════════
    def _build_left(self, parent):
        # ── header bar ───────────────────────────────────────────
        hdr = tk.Frame(parent, bg="#0f2942", pady=10, padx=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🐑  adhahi.dz Bot",
                 bg="#0f2942", fg=TEXT, font=("Segoe UI",13,"bold")).pack(side="left")

        # ── scrollable content ───────────────────────────────────
        canvas = tk.Canvas(parent, bg=PANEL, highlightthickness=0, bd=0)
        vsb    = tk.Scrollbar(parent, orient="vertical", command=canvas.yview,
                              bg=PANEL, troughcolor=PANEL)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        body = tk.Frame(canvas, bg=PANEL)
        win  = canvas.create_window((0,0), window=body, anchor="nw")

        body.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # ── SECTION: Credentials ─────────────────────────────────
        self._sep(body, "🔐  Credentials")
        for lbl, key, secret in [
            ("NIN  (18 digits)",  "nin",      False),
            ("CNI  (9 digits)",   "cni",      False),
            ("Phone",             "phone",    False),
            ("Email  (optional)", "email",    False),
            ("Password",          "password", False),
        ]:
            self._entry_row(body, lbl, key, secret)

        # payment
        tk.Label(body, text="Payment method", bg=PANEL, fg=MUTED,
                 font=("Segoe UI",9)).pack(anchor="w", padx=16, pady=(2,1))
        pf = tk.Frame(body, bg=PANEL); pf.pack(anchor="w", padx=16, pady=(0,10))
        for val, lbl in [("cash","💵 Cash"),("tpe","💳 TPE"),("online","🌐 Online")]:
            tk.Radiobutton(pf, text=lbl, variable=self._pay, value=val,
                           bg=PANEL, fg=TEXT, selectcolor=ACCENT,
                           activebackground=PANEL, font=("Segoe UI",9),
                           cursor="hand2").pack(side="left", padx=(0,8))

        # ── SECTION: Telegram ────────────────────────────────────
        self._sep(body, "📣  Telegram  (optional — get phone alerts)")
        self._entry_row(body, "Bot Token",  "bot_token", False)
        self._entry_row(body, "Chat ID",    "chat_id",   False)

        tk.Button(body, text="🔔  Test Notification",
                  bg=BORDER, fg=TEXT, activebackground="#444c56",
                  relief="flat", font=("Segoe UI",9), cursor="hand2",
                  command=self._test_tg).pack(anchor="w", padx=16, pady=(0,12))

        # ── SECTION: Wilayas ─────────────────────────────────────
        self._sep(body, "🗺  Target Wilayas  (check all you want to monitor)")

        # select-all / none helpers
        sbf = tk.Frame(body, bg=PANEL); sbf.pack(anchor="w", padx=16, pady=(0,4))
        tk.Button(sbf, text="✔ All",   width=7, bg=BORDER, fg=TEXT, relief="flat",
                  font=("Segoe UI",8), cursor="hand2",
                  command=lambda: self._sel_all(True)).pack(side="left", padx=(0,4))
        tk.Button(sbf, text="✘ None",  width=7, bg=BORDER, fg=TEXT, relief="flat",
                  font=("Segoe UI",8), cursor="hand2",
                  command=lambda: self._sel_all(False)).pack(side="left")

        wf = tk.Frame(body, bg=PANEL); wf.pack(fill="x", padx=14, pady=(0,12))
        COLS = 2
        for i, (code, name) in enumerate(ALL_WILAYAS):
            row, col = divmod(i, COLS)
            v = tk.BooleanVar(value=(code in self.cfg.get("target_wilayas",[])))
            self._wvars[code] = v
            tk.Checkbutton(wf, text=f"  {code} – {name}", variable=v,
                           bg=PANEL, fg=TEXT, selectcolor=ACCENT,
                           activebackground=PANEL, font=("Segoe UI",9),
                           cursor="hand2").grid(row=row, column=col, sticky="w", pady=1)
        wf.columnconfigure(0, weight=1); wf.columnconfigure(1, weight=1)

        # ── SECTION: Settings ────────────────────────────────────
        self._sep(body, "⚙️  Settings")
        sf = tk.Frame(body, bg=PANEL); sf.pack(anchor="w", padx=16, pady=(2,14))
        tk.Label(sf, text="Poll every", bg=PANEL, fg=MUTED,
                 font=("Segoe UI",9)).pack(side="left")
        tk.Spinbox(sf, from_=1, to=60, width=4, textvariable=self._ivar,
                   bg=ENTRY, fg=TEXT, insertbackground=TEXT,
                   buttonbackground=BORDER, relief="flat",
                   font=("Consolas",10)).pack(side="left", padx=6)
        tk.Label(sf, text="seconds", bg=PANEL, fg=MUTED,
                 font=("Segoe UI",9)).pack(side="left")

        # ── Control buttons ───────────────────────────────────────
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", padx=12, pady=(4,10))
        bf = tk.Frame(body, bg=PANEL); bf.pack(fill="x", padx=14, pady=(0,16))

        self._btn_start = tk.Button(bf, text="▶  Start Monitoring", width=18,
            bg=GREEN, fg="#000", activebackground="#2ea043",
            font=("Segoe UI",11,"bold"), relief="flat", cursor="hand2",
            command=self._start)
        self._btn_start.pack(side="left", padx=(0,8))

        self._btn_stop = tk.Button(bf, text="■  Stop", width=9,
            bg=RED, fg=TEXT, activebackground="#da3633",
            font=("Segoe UI",11,"bold"), relief="flat", cursor="hand2",
            state="disabled", command=self._stop)
        self._btn_stop.pack(side="left", padx=(0,8))

        tk.Button(bf, text="💾", width=3,
            bg=BORDER, fg=TEXT, activebackground="#444c56",
            font=("Segoe UI",11), relief="flat", cursor="hand2",
            command=self._save).pack(side="left")

    def _sep(self, parent, title):
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=12, pady=(14,0))
        tk.Label(parent, text=title, bg=PANEL, fg=GREEN,
                 font=("Segoe UI",10,"bold")).pack(anchor="w", padx=14, pady=(5,5))

    def _entry_row(self, parent, label, key, secret):
        tk.Label(parent, text=label, bg=PANEL, fg=MUTED,
                 font=("Segoe UI",9)).pack(anchor="w", padx=16, pady=(0,1))
        v = tk.StringVar(); self._fvars[key] = v
        tk.Entry(parent, textvariable=v, show="●" if secret else "",
                 bg=ENTRY, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=6, font=("Consolas",10),
                 highlightthickness=1,
                 highlightbackground=BORDER,
                 highlightcolor=ACCENT).pack(fill="x", padx=16, pady=(0,7))

    # ══════════════════════════════════════════════════════════════
    #  RIGHT PANEL  —  live log
    # ══════════════════════════════════════════════════════════════
    def _build_right(self, parent):
        # ── title bar ────────────────────────────────────────────
        top = tk.Frame(parent, bg=BG, padx=14, pady=8)
        top.pack(fill="x")

        tk.Label(top, text="📋  Live Log",
                 bg=BG, fg=TEXT, font=("Segoe UI",12,"bold")).pack(side="left")

        self._dot = tk.Label(top, text="⬤  Idle",
                             bg=BG, fg=MUTED, font=("Segoe UI",10,"bold"))
        self._dot.pack(side="left", padx=(16,0))

        self._poll_lbl = tk.Label(top, text="",
                                   bg=BG, fg=MUTED, font=("Consolas",9))
        self._poll_lbl.pack(side="left", padx=(12,0))

        tk.Button(top, text="🗑  Clear log",
                  bg=BORDER, fg=TEXT, activebackground="#444c56",
                  relief="flat", font=("Segoe UI",9), cursor="hand2",
                  command=self._clear).pack(side="right")

        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")

        # ── log text box ─────────────────────────────────────────
        self._log_box = scrolledtext.ScrolledText(
            parent, state="disabled", wrap="word",
            bg="#010409", fg="#c9d1d9",
            font=("Consolas",9), relief="flat", bd=0,
            insertbackground=TEXT, padx=10, pady=8)
        self._log_box.pack(fill="both", expand=True)

        # colour tags
        self._log_box.tag_config("ts",     foreground="#484f58")
        self._log_box.tag_config("OK",     foreground=GREEN)
        self._log_box.tag_config("INFO",   foreground="#79c0ff")
        self._log_box.tag_config("WARN",   foreground=YELLOW)
        self._log_box.tag_config("ERR",    foreground=RED)
        self._log_box.tag_config("FOUND",  foreground="#ffa657",
                                  font=("Consolas",10,"bold"))
        self._log_box.tag_config("SYSTEM", foreground="#484f58",
                                  font=("Consolas",9,"italic"))

        # ── status bar ───────────────────────────────────────────
        sb = tk.Frame(parent, bg=PANEL, pady=4, padx=12)
        sb.pack(fill="x")
        self._sb_msg  = tk.Label(sb, text="Not running.",
                                  bg=PANEL, fg=MUTED, font=("Segoe UI",8))
        self._sb_msg.pack(side="left")
        self._sb_time = tk.Label(sb, text="",
                                  bg=PANEL, fg=MUTED, font=("Consolas",8))
        self._sb_time.pack(side="right")

    # ─────────────────────────────────────────────────────────────
    # FIELD HELPERS
    # ─────────────────────────────────────────────────────────────
    def _load_fields(self):
        for k,v in self._fvars.items():
            v.set(self.cfg.get(k,""))
        self._pay.set(self.cfg.get("payment","cash"))
        self._ivar.set(self.cfg.get("check_interval",2))
        tgt = set(self.cfg.get("target_wilayas",[]))
        for code,bv in self._wvars.items():
            bv.set(code in tgt)

    def _collect(self) -> dict:
        c = {k: v.get().strip() for k,v in self._fvars.items()}
        c["payment"]         = self._pay.get()
        c["check_interval"]  = self._ivar.get()
        c["target_wilayas"]  = [code for code,_ in ALL_WILAYAS
                                 if self._wvars[code].get()]
        return c

    def _sel_all(self, val: bool):
        for bv in self._wvars.values(): bv.set(val)

    def _save(self):
        self.cfg = self._collect()
        save_cfg(self.cfg)
        self.log("SYSTEM", "Config saved  ✓")

    # ─────────────────────────────────────────────────────────────
    # LOGGING
    # ─────────────────────────────────────────────────────────────
    def log(self, level: str, msg: str):
        def _do():
            b = self._log_box
            b.configure(state="normal")
            b.insert("end", f"[{hms()}] ", "ts")
            b.insert("end", f"{level:<6}", level)
            b.insert("end", f"{msg}\n")
            b.see("end")
            b.configure(state="disabled")
        self.after(0, _do)

    def _clear(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0","end")
        self._log_box.configure(state="disabled")

    # ─────────────────────────────────────────────────────────────
    # STATUS
    # ─────────────────────────────────────────────────────────────
    def _set_dot(self, text, color):
        self.after(0, lambda: self._dot.configure(text=text, fg=color))

    def _set_sb(self, msg="", time_=""):
        self.after(0, lambda: (
            self._sb_msg.configure(text=msg),
            self._sb_time.configure(text=time_)))

    def _tick(self):
        """Update poll counter every second while running."""
        if not self._running: return
        self.after(0, lambda: self._poll_lbl.configure(
            text=f"  polls: {self._attempt}"))
        self.after(1000, self._tick)

    # ─────────────────────────────────────────────────────────────
    # TELEGRAM TEST
    # ─────────────────────────────────────────────────────────────
    def _test_tg(self):
        t = self._fvars["bot_token"].get().strip()
        c = self._fvars["chat_id"].get().strip()
        if not t or not c:
            messagebox.showwarning("Telegram","Fill Bot Token and Chat ID first."); return
        send_telegram(t, c, f"✅ <b>Test OK!</b>\nadhahi bot is alive.\n⏰ {now()}")
        messagebox.showinfo("Telegram","Message sent! Check your phone.")

    # ─────────────────────────────────────────────────────────────
    # START / STOP
    # ─────────────────────────────────────────────────────────────
    def _start(self):
        self.cfg = self._collect()

        for k, lbl in [("nin","NIN"),("cni","CNI"),
                        ("phone","Phone"),("password","Password")]:
            if not self.cfg.get(k):
                messagebox.showerror("Missing field", f"Please fill in your {lbl}.")
                return
        if not self.cfg["target_wilayas"]:
            messagebox.showerror("No wilayas","Select at least one wilaya."); return

        save_cfg(self.cfg)
        self._running  = True
        self._attempt  = 0
        self._api_active = set()

        self._btn_start.configure(state="disabled")
        self._btn_stop.configure(state="normal")
        self._set_dot("⬤  Running", GREEN)
        self._set_sb(
            f"Monitoring {len(self.cfg['target_wilayas'])} wilaya(s)  •  "
            f"interval: {self.cfg['check_interval']}s")

        self.log("SYSTEM", "━"*52)
        self.log("SYSTEM", f"Bot started — {now()}")
        self.log("INFO",   f"Watching: {self.cfg['target_wilayas']}")
        self.log("INFO",   f"Poll interval: {self.cfg['check_interval']}s")
        self.log("SYSTEM", "━"*52)

        send_telegram(self.cfg["bot_token"], self.cfg["chat_id"],
            f"🤖 <b>Bot started</b>\nWilayas: {self.cfg['target_wilayas']}\n⏰ {now()}")

        threading.Thread(target=self._poll_loop, daemon=True).start()
        self._tick()
        # Pre-warm ChromeDriver in background so first detection launches instantly
        threading.Thread(target=self._warmup_driver, daemon=True).start()

    def _warmup_driver(self):
        """Resolve ChromeDriver path in background so first browser launch is instant."""
        try:
            _get_chromedriver_path()
            self.log("SYSTEM", "ChromeDriver ready ✓")
        except Exception as e:
            self.log("WARN", f"ChromeDriver pre-warm failed: {e}")

    def _stop(self):
        self._running = False
        self._btn_start.configure(state="normal")
        self._btn_stop.configure(state="disabled")
        self._set_dot("⬤  Stopped", RED)
        self._poll_lbl.configure(text="")
        self._set_sb("Stopped.")
        self.log("SYSTEM", f"Bot stopped — {now()}")

    # ─────────────────────────────────────────────────────────────
    # POLL LOOP  (background thread — never stops until _stop())
    # ─────────────────────────────────────────────────────────────
    def _poll_loop(self):
        while self._running:
            self._attempt += 1
            ts = hms()
            try:
                data  = fetch_quotas()
                avail = available_wilayas(data, self.cfg["target_wilayas"])

                avail_set = set(avail)
                newly_available = avail_set - self._api_active
                
                if newly_available:
                    for w in newly_available:
                        self.log("FOUND", f"🎉  WILAYA {w} IS OPEN!  Launching browser …")
                        send_telegram(
                            self.cfg["bot_token"], self.cfg["chat_id"],
                            f"🚨 <b>WILAYA {w} AVAILABLE!</b>\n⏰ {now()}")
                        snap = self.cfg.copy(); ww = w
                        def _run(w=ww, c=snap):
                            try:
                                fill_and_submit(c, w, self.log)
                            except Exception as e:
                                self.log("ERR", f"[W{w}] Unhandled thread error: {e}")
                        threading.Thread(target=_run, daemon=True).start()

                self._api_active = avail_set

                if avail_set:
                    self.log("INFO", f"Poll #{self._attempt:04d}  [{ts}]  — Open slots: {', '.join(avail)}")
                else:
                    self.log("INFO", f"Poll #{self._attempt:04d}  [{ts}]  — no open slots yet")

                self.after(0, lambda t=ts: self._sb_time.configure(
                    text=f"last poll: {t}"))

            except urllib.error.HTTPError as e:
                self.log("WARN", f"Poll #{self._attempt:04d}  HTTP {e.code}: {e.reason}")
            except urllib.error.URLError as e:
                self.log("WARN", f"Poll #{self._attempt:04d}  Network hiccup: {e.reason} — will retry next poll")
            except Exception as e:
                self.log("ERR",  f"Poll #{self._attempt:04d}  {e}")

            # interruptible sleep (checks every 250 ms)
            for _ in range(self._ivar.get() * 4):
                if not self._running: break
                time.sleep(0.25)

    # ─────────────────────────────────────────────────────────────
    def _quit(self):
        self._running = False
        self.destroy()


if __name__ == "__main__":
    App().mainloop()