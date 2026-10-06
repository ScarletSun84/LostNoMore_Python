import importlib.util
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
REQUIREMENTS = APP_DIR / "requirements.txt"

def ensure_dependencies():
    required = {
        "PIL": "Pillow",
        "reportlab": "reportlab",
    }
    missing = [package for module, package in required.items()
               if importlib.util.find_spec(module) is None]
    if not missing:
        return
    print("LostNoMore: required packages are missing.")
    print("Installing: " + ", ".join(missing))
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)])
    except subprocess.CalledProcessError:
        print("Automatic installation failed. Try: python -m pip install -r requirements.txt")
        raise SystemExit(1)

ensure_dependencies()

import base64
import hashlib
import io
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

APP_DIR = Path(__file__).resolve().parent

# Standard Tkinter UI helpers. These replace the former Tkinter widgets
# while preserving the LostNoMore layout and appearance as closely as possible.
class _UI:
    """Tkinter-only compatibility helpers with proper native Tk sizing/colors.
    These names are kept so the rest of the application can use one consistent
    widget factory without depending on CustomTkinter.
    """

    class CTk(tk.Tk):
        def configure(self, cnf=None, **kwargs):
            kwargs.pop("fg_color", None)
            if "bg" not in kwargs:
                kwargs["bg"] = BG
            return super().configure(cnf, **kwargs)
        config = configure

    class CTkFrame(tk.Frame):
        def __init__(self, master=None, **kwargs):
            kwargs.pop("corner_radius", None)
            fg = kwargs.pop("fg_color", None)
            border = kwargs.pop("border_color", None)
            bw = kwargs.pop("border_width", 0)
            if fg in (None, "transparent"):
                fg = master.cget("bg") if master is not None else BG
            kwargs["bg"] = fg
            if border is not None and bw:
                kwargs["highlightbackground"] = border
                kwargs["highlightcolor"] = border
                kwargs["highlightthickness"] = bw
                kwargs["bd"] = 0
            super().__init__(master, **kwargs)

    class CTkLabel(tk.Label):
        def __init__(self, master=None, **kwargs):
            kwargs.pop("corner_radius", None)
            fg = kwargs.pop("fg_color", None)
            if fg in (None, "transparent"):
                fg = master.cget("bg") if master is not None else BG
            kwargs["bg"] = fg
            if "text_color" in kwargs:
                kwargs["fg"] = kwargs.pop("text_color")
            kwargs.setdefault("bd", 0)
            kwargs.setdefault("padx", 0)
            kwargs.setdefault("pady", 0)
            # CTk pixel-like widths/heights are converted to Tk text units.
            if isinstance(kwargs.get("width"), int) and kwargs["width"] > 20:
                kwargs["width"] = max(1, kwargs["width"] // 9)
            if isinstance(kwargs.get("height"), int) and kwargs["height"] > 5:
                kwargs["height"] = max(1, kwargs["height"] // 18)
            super().__init__(master, **kwargs)

        def configure(self, cnf=None, **kwargs):
            if "text_color" in kwargs:
                kwargs["fg"] = kwargs.pop("text_color")
            if "fg_color" in kwargs:
                kwargs["bg"] = kwargs.pop("fg_color")
            return super().configure(cnf, **kwargs)
        config = configure

    class CTkButton(tk.Button):
        def __init__(self, master=None, **kwargs):
            kwargs.pop("corner_radius", None)
            hover = kwargs.pop("hover_color", None)
            fg = kwargs.pop("fg_color", None)
            if fg in (None, "transparent"):
                fg = master.cget("bg") if master is not None else PANEL_2
            kwargs["bg"] = fg
            kwargs.setdefault("activebackground", hover or fg)
            if "text_color" in kwargs:
                kwargs["fg"] = kwargs.pop("text_color")
            kwargs.setdefault("activeforeground", kwargs.get("fg", TEXT))
            kwargs.setdefault("relief", "flat")
            kwargs.setdefault("bd", 0)
            kwargs.setdefault("cursor", "hand2")
            kwargs.setdefault("padx", 12)
            kwargs.setdefault("pady", 8)
            # Native Tk uses text units rather than pixels.
            width = kwargs.get("width")
            if isinstance(width, int) and width > 35:
                kwargs["width"] = max(8, width // 9)
            height = kwargs.get("height")
            if isinstance(height, int) and height > 4:
                kwargs["height"] = 2
            super().__init__(master, **kwargs)

    class CTkEntry(tk.Entry):
        def __init__(self, master=None, **kwargs):
            kwargs.pop("corner_radius", None)
            kwargs.pop("placeholder_text", None)
            fg = kwargs.pop("fg_color", None)
            if fg in (None, "transparent"):
                fg = "#111a27"
            kwargs["bg"] = fg
            if "border_color" in kwargs:
                bc = kwargs.pop("border_color")
                kwargs["highlightbackground"] = bc
                kwargs["highlightcolor"] = BLUE_HOVER
                kwargs.setdefault("highlightthickness", 1)
            if "text_color" in kwargs:
                kwargs["fg"] = kwargs.pop("text_color")
            kwargs.setdefault("insertbackground", TEXT)
            kwargs.setdefault("relief", "flat")
            kwargs.setdefault("bd", 0)
            width = kwargs.get("width")
            if isinstance(width, int) and width > 50:
                kwargs["width"] = max(25, width // 9)
            kwargs.pop("height", None)
            super().__init__(master, **kwargs)

    class CTkTextbox(tk.Text):
        def __init__(self, master=None, **kwargs):
            kwargs.pop("corner_radius", None)
            fg = kwargs.pop("fg_color", None)
            if fg in (None, "transparent"):
                fg = "#111a27"
            kwargs["bg"] = fg
            if "border_color" in kwargs:
                bc = kwargs.pop("border_color")
                kwargs["highlightbackground"] = bc
                kwargs["highlightcolor"] = BLUE_HOVER
                kwargs["highlightthickness"] = kwargs.pop("border_width", 1)
            else:
                kwargs.pop("border_width", None)
            if "text_color" in kwargs:
                kwargs["fg"] = kwargs.pop("text_color")
            kwargs.setdefault("insertbackground", TEXT)
            kwargs.setdefault("relief", "flat")
            kwargs.setdefault("bd", 0)
            height = kwargs.get("height")
            if isinstance(height, int) and height > 20:
                kwargs["height"] = max(5, height // 18)
            super().__init__(master, **kwargs)

    class CTkRadioButton(tk.Radiobutton):
        def __init__(self, master=None, **kwargs):
            kwargs.pop("corner_radius", None)
            if "fg_color" in kwargs:
                kwargs["selectcolor"] = kwargs.pop("fg_color")
            kwargs.pop("hover_color", None)
            if "text_color" in kwargs:
                kwargs["fg"] = kwargs.pop("text_color")
            kwargs.setdefault("bg", master.cget("bg") if master is not None else BG)
            kwargs.setdefault("activebackground", kwargs["bg"])
            kwargs.setdefault("activeforeground", kwargs.get("fg", TEXT))
            kwargs.setdefault("selectcolor", PANEL_2)
            kwargs.setdefault("relief", "flat")
            kwargs.setdefault("highlightthickness", 0)
            kwargs.setdefault("cursor", "hand2")
            super().__init__(master, **kwargs)

    class CTkOptionMenu(tk.Menubutton):
        def __init__(self, master, variable, values=None, **kwargs):
            values = list(values or [])
            for k in ("corner_radius", "button_color", "button_hover_color"):
                kwargs.pop(k, None)
            requested_width = kwargs.pop("width", None)
            kwargs.pop("height", None)
            fg = kwargs.pop("fg_color", None)
            bg = fg if fg not in (None, "transparent") else "#111a27"
            text_color = kwargs.pop("text_color", TEXT)
            kwargs.pop("activebackground", None)
            kwargs.pop("activeforeground", None)
            kwargs.setdefault("relief", "flat")
            kwargs.setdefault("bd", 0)
            kwargs.setdefault("highlightthickness", 1)
            kwargs.setdefault("highlightbackground", "#32445e")
            kwargs["bg"] = bg
            kwargs["fg"] = text_color
            kwargs["activebackground"] = "#253650"
            kwargs["activeforeground"] = text_color
            super().__init__(master, textvariable=variable, **kwargs)
            self.variable = variable
            self._menu = tk.Menu(self, tearoff=False,
                                 bg=bg, fg=text_color,
                                 activebackground="#253650",
                                 activeforeground=text_color,
                                 relief="flat", bd=0)
            for value in values:
                self._menu.add_radiobutton(label=value, variable=variable, value=value)
            self.configure(menu=self._menu)
            if requested_width is not None:
                self.configure(width=max(10, int(requested_width) // 9))
    class CTkScrollableFrame(tk.Frame):
        def __init__(self, master=None, **kwargs):
            fg = kwargs.pop("fg_color", None)
            kwargs.pop("corner_radius", None)
            border = kwargs.pop("border_color", None)
            bw = kwargs.pop("border_width", 0)
            if fg in (None, "transparent"):
                fg = master.cget("bg") if master is not None else BG
            kwargs["bg"] = fg
            if border is not None and bw:
                kwargs["highlightbackground"] = border
                kwargs["highlightcolor"] = border
                kwargs["highlightthickness"] = bw
                kwargs["bd"] = 0
            super().__init__(master, **kwargs)

            self._bg = fg
            self.canvas = tk.Canvas(self, bg=fg, highlightthickness=0, bd=0)
            self.scrollbar = tk.Scrollbar(
                self, orient="vertical", command=self.canvas.yview,
                bg="#172131", activebackground="#253650",
                troughcolor=fg, relief="flat", bd=0, width=10
            )
            self.content = tk.Frame(self.canvas, bg=fg)
            self._window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
            self.canvas.configure(yscrollcommand=self.scrollbar.set)

            self.canvas.pack(side="left", fill="both", expand=True)
            self.scrollbar.pack(side="right", fill="y")

            self.content.bind("<Configure>", self._on_content_configure)
            self.canvas.bind("<Configure>", self._on_canvas_configure)
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
            self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux, add="+")
            self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux, add="+")

        def _on_content_configure(self, _event=None):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        def _on_canvas_configure(self, event):
            self.canvas.itemconfigure(self._window, width=event.width)

        def _on_mousewheel(self, event):
            if self.winfo_exists():
                try:
                    top = self.canvas.winfo_rooty()
                    bottom = top + self.canvas.winfo_height()
                    if top <= event.y_root <= bottom:
                        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                except tk.TclError:
                    pass

        def _on_mousewheel_linux(self, event):
            if self.winfo_exists():
                try:
                    top = self.canvas.winfo_rooty()
                    bottom = top + self.canvas.winfo_height()
                    if top <= event.y_root <= bottom:
                        self.canvas.yview_scroll(-1 if event.num == 4 else 1, "units")
                except tk.TclError:
                    pass

        def destroy(self):
            try:
                self.canvas.unbind_all("<MouseWheel>")
                self.canvas.unbind_all("<Button-4>")
                self.canvas.unbind_all("<Button-5>")
            except tk.TclError:
                pass
            super().destroy()


    class CTkImage:
        def __new__(cls, light_image=None, dark_image=None, size=(100, 100), **kwargs):
            image = light_image or dark_image
            return ImageTk.PhotoImage(image.resize(size, Image.LANCZOS)) if image is not None else None

    class CTkFont:
        def __new__(cls, **kwargs):
            family = kwargs.get("family", "Segoe UI")
            size = kwargs.get("size", 12)
            weight = kwargs.get("weight", "normal")
            return (family, size, weight)

    StringVar = tk.StringVar
    CTkToplevel = tk.Toplevel

ui = _UI()
DB_PATH = APP_DIR / "lostnomore.db"
LOGO_PATH = APP_DIR / "lostnomore_logo.png"

# Original LostNoMore website-inspired palette
BG = "#0b1118"
PANEL = "#111923"
PANEL_2 = "#1b2a3d"
BLUE = "#60a5fa"
BLUE_HOVER = "#3b82f6"
TEXT = "#ffffff"
MUTED = "#a8b2c1"
DANGER = "#ef4444"
SUCCESS = "#22c55e"


SITES = [
    "Main/Cainta Campus", "Antipolo Campus", "Binangonan Campus", "Cogeo Campus",
    "San Mateo Campus", "Sumulong Campus", "Taytay Campus", "Others"
]
ITEMS = ["Phone", "Wallet", "Tumbler", "Bags", "Laptop", "Key", "ID Card", "Eyewear", "Jewelry", "Card", "Others"]


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL COLLATE NOCASE,
        phone TEXT DEFAULT '',
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS reports (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL CHECK(type IN ('Lost', 'Found')),
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        site TEXT DEFAULT '',
        location TEXT DEFAULT '',
        date TEXT DEFAULT '',
        items TEXT NOT NULL,
        description TEXT DEFAULT '',
        reward TEXT DEFAULT '',
        image_data TEXT,
        hidden_info INTEGER NOT NULL DEFAULT 0,
        timestamp TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_reports_type ON reports(type);
    CREATE INDEX IF NOT EXISTS idx_reports_email ON reports(email);
    CREATE INDEX IF NOT EXISTS idx_reports_site ON reports(site);
    CREATE INDEX IF NOT EXISTS idx_reports_date ON reports(date);
    """)
    # Ensure the real administrator account always exists and has the
    # expected administrator role/password. This also repairs an older
    # database copy if the account was missing or had the wrong role.
    admin_email = "admin@lostnomore.com"
    admin_password_hash = hash_password("Admin@2026!")
    existing_admin = conn.execute(
        "SELECT id FROM users WHERE email=?", (admin_email,)
    ).fetchone()
    if existing_admin:
        conn.execute(
            "UPDATE users SET name=?, phone=?, password_hash=?, role=? WHERE id=?",
            ("System Administrator", "", admin_password_hash, "admin", existing_admin[0])
        )
    else:
        conn.execute(
            "INSERT INTO users(name,email,phone,password_hash,role,created_at) VALUES(?,?,?,?,?,?)",
            ("System Administrator", admin_email, "", admin_password_hash, "admin", now_iso())
        )
    conn.commit()
    conn.close()


class LostNoMore(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LostNoMore")
        self.geometry("1000x680")
        self.minsize(900, 620)
        self.configure(bg=BG)
        self.current_user = None
        self.logo = self.load_logo()
        self.show_login()

    def load_logo(self):
        if LOGO_PATH.exists():
            try:
                img = Image.open(LOGO_PATH)
                return ui.CTkImage(light_image=img, dark_image=img, size=(70, 70))
            except Exception:
                return None
        return None

    def clear(self):
        for child in self.winfo_children():
            child.destroy()

    def title_label(self, parent, text, size=28):
        return ui.CTkLabel(parent, text=text, text_color=BLUE,
                            font=ui.CTkFont(size=size, weight="bold"))

    def glass(self, parent, **kwargs):
        return ui.CTkFrame(parent, fg_color=PANEL, border_color="#26364d", border_width=1,
                            corner_radius=22, **kwargs)

    def button(self, parent, text, command, width=180, primary=False, **kwargs):
        return ui.CTkButton(
            parent, text=text, command=command, width=width, height=36,
            corner_radius=10,
            fg_color=BLUE if primary else PANEL_2,
            hover_color=BLUE_HOVER if primary else "#253650",
            text_color="#1e3a8a" if primary else TEXT,
            font=ui.CTkFont(size=11, weight="bold"), **kwargs
        )

    def entry(self, parent, placeholder, width=360, **kwargs):
        return ui.CTkEntry(parent, width=width, height=43, corner_radius=18,
                            placeholder_text=placeholder, fg_color="#111a27",
                            border_color="#32445e", text_color=TEXT, **kwargs)

    def show_login(self):
        self.clear()
        self.unbind_all("<Return>")
        self.configure(bg=BG)

        outer = ui.CTkFrame(self, fg_color=BG)
        outer.pack(fill="both", expand=True)

        card = self.glass(outer, width=430, height=540)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        if self.logo:
            ui.CTkLabel(card, image=self.logo, text="", bg=PANEL).pack(pady=(30, 8))
        ui.CTkLabel(card, text="LostNoMore", text_color=BLUE,
                     font=ui.CTkFont(size=27, weight="bold"), bg=PANEL).pack()
        ui.CTkLabel(card, text="Lost & Found Management System", text_color=MUTED,
                     font=ui.CTkFont(size=11), bg=PANEL).pack(pady=(3, 25))

        self.login_email = self.entry(card, "Email", 310)
        self.login_email.pack(pady=7, ipady=4)
        self.login_password = self.entry(card, "Password", 310, show="•")
        self.login_password.pack(pady=7, ipady=4)
        self.login_msg = ui.CTkLabel(card, text="", text_color="#ff6b6b", wraplength=350)
        self.login_msg.pack(pady=(5, 4))
        self.button(card, "LOGIN", self.login, 310, primary=True).pack(pady=9)
        self.button(card, "CREATE ACCOUNT", self.show_create_account, 310).pack(pady=5)
        self.login_password.bind("<Return>", lambda _: self.login())

    def show_create_account(self):
        self.clear()
        card = self.glass(self, width=500, height=650)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)
        if self.logo:
            ui.CTkLabel(card, image=self.logo, text="").pack(pady=(22, 0))
        self.title_label(card, "Create Account", 28).pack(pady=(0, 4))
        ui.CTkLabel(card, text="Register a LostNoMore account", text_color=MUTED).pack(pady=(0, 18))

        self.signup_name = self.entry(card, "Full Name", 380); self.signup_name.pack(pady=6, ipady=3)
        self.signup_email = self.entry(card, "Email", 380); self.signup_email.pack(pady=6, ipady=3)
        self.signup_phone = self.entry(card, "Phone Number", 380); self.signup_phone.pack(pady=6, ipady=3)
        self.signup_password = self.entry(card, "Password", 380, show="•"); self.signup_password.pack(pady=6, ipady=3)
        self.signup_confirm = self.entry(card, "Confirm Password", 380, show="•"); self.signup_confirm.pack(pady=6, ipady=3)
        self.signup_msg = ui.CTkLabel(card, text="", text_color="#ff6b6b", wraplength=380)
        self.signup_msg.pack(pady=8)
        self.button(card, "CREATE ACCOUNT", self.create_account, 380, primary=True).pack(pady=7)
        self.button(card, "BACK TO LOGIN", self.show_login, 380).pack(pady=5)

    def create_account(self):
        name = self.signup_name.get().strip()
        email = self.signup_email.get().strip()
        phone = self.signup_phone.get().strip()
        password = self.signup_password.get()
        confirm = self.signup_confirm.get()
        if len(name) < 2 or len(name) > 50:
            self.signup_msg.configure(text="Please enter a valid name (2–50 characters)."); return
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            self.signup_msg.configure(text="Please enter a valid email address."); return
        if len(password) < 6:
            self.signup_msg.configure(text="Password must be at least 6 characters."); return
        if password != confirm:
            self.signup_msg.configure(text="Passwords do not match."); return
        conn = db()
        try:
            conn.execute("INSERT INTO users(name,email,phone,password_hash,role,created_at) VALUES(?,?,?,?,?,?)",
                         (name, email, phone, hash_password(password), "user", now_iso()))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close(); self.signup_msg.configure(text="An account with that email already exists."); return
        conn.close()
        self.show_login()
        self.login_email.insert(0, email)
        self.login_msg.configure(text="Account created successfully. Please log in.", text_color=SUCCESS)

    def login(self):
        email = self.login_email.get().strip().lower()
        password = self.login_password.get()
        if not email or not password:
            self.login_msg.configure(text="Please enter your email and password.", text_color="#ff6b6b")
            return
        conn = db()
        user = conn.execute("SELECT * FROM users WHERE lower(email)=? AND password_hash=?",
                            (email, hash_password(password))).fetchone()
        conn.close()
        if not user:
            self.login_msg.configure(text="Invalid email or password.", text_color="#ff6b6b")
            return
        self.current_user = dict(user)
        self.show_dashboard()

    def show_dashboard(self):
        self.clear()
        self.grid_columnconfigure(0, weight=0, minsize=195)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ui.CTkFrame(self, width=195, corner_radius=0, fg_color="#080b10")
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        if self.logo:
            ui.CTkLabel(sidebar, image=self.logo, text="").pack(pady=(30, 2))
        ui.CTkLabel(sidebar, text="LostNoMore", text_color=BLUE,
                     font=ui.CTkFont(size=20, weight="bold")).pack(pady=(0, 28))

        self.nav_button(sidebar, "⌂  Dashboard", self.dashboard_page)
        self.nav_button(sidebar, "▣  Lost Item", lambda: self.report_form("Lost"))
        self.nav_button(sidebar, "✓  Found Item", lambda: self.report_form("Found"))
        self.nav_button(sidebar, "☰  View Reports", self.reports_page)
        self.nav_button(sidebar, "▤  Export Reports", self.export_pdf)
        if self.current_user.get("role") == "admin":
            self.nav_button(sidebar, "⚙  Admin", self.admin_page)

        # Keep the account and logout controls anchored at the bottom of the sidebar.
        spacer = ui.CTkFrame(sidebar, fg_color="transparent", height=10)
        spacer.pack(fill="both", expand=True)

        account_frame = ui.CTkFrame(sidebar, fg_color="#0d131c", corner_radius=16)
        account_frame.pack(fill="x", padx=14, pady=(0, 10))
        ui.CTkLabel(account_frame, text=self.current_user["name"], text_color=TEXT,
                     font=ui.CTkFont(size=11, weight="bold"), anchor="w").pack(fill="x", padx=14, pady=(10, 1))
        ui.CTkLabel(account_frame, text=self.current_user["role"].title(), text_color=MUTED,
                     font=ui.CTkFont(size=10), anchor="w").pack(fill="x", padx=14, pady=(0, 10))

        ui.CTkButton(sidebar, text="↪  LOG OUT", height=38, corner_radius=12,
                      fg_color="#4a1f25", hover_color="#7f1d1d", text_color=TEXT,
                      font=ui.CTkFont(size=11, weight="bold"), command=self.logout).pack(fill="x", padx=14, pady=(0, 14))

        self.content = ui.CTkFrame(self, fg_color=BG)
        self.content.grid(row=0, column=1, sticky="nsew", padx=20, pady=18)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)
        self.dashboard_page()

    def logout(self):
        """Sign out the current user and return to the LostNoMore login screen."""
        self.current_user = None
        self.show_login()

    def nav_button(self, parent, text, command):
        ui.CTkButton(parent, text=text, command=command, height=36, corner_radius=10,
                      fg_color="transparent", hover_color="#17243a", text_color=TEXT,
                      anchor="w", font=ui.CTkFont(size=11, weight="bold")).pack(fill="x", padx=14, pady=4)

    def set_content(self):
        for child in self.content.winfo_children(): child.destroy()

    def dashboard_page(self):
        self.set_content()
        self.title_label(self.content, "LostNoMore", 34).grid(row=0, column=0, sticky="w")
        ui.CTkLabel(self.content, text="Lost and Found Management System", text_color=MUTED).grid(row=0, column=0, sticky="w", pady=(48, 0))

        conn = db()
        total = conn.execute("SELECT COUNT(*) n FROM reports").fetchone()["n"]
        lost = conn.execute("SELECT COUNT(*) n FROM reports WHERE type='Lost'").fetchone()["n"]
        found = conn.execute("SELECT COUNT(*) n FROM reports WHERE type='Found'").fetchone()["n"]
        conn.close()

        actions = self.glass(self.content)
        actions.grid(row=1, column=0, sticky="nsew", pady=(30, 0))
        ui.CTkLabel(actions, text="What would you like to do?", text_color=BLUE,
                     font=ui.CTkFont(size=19, weight="bold")).pack(pady=(28, 8))
        ui.CTkLabel(actions, text="Report an item or search existing LostNoMore records.", text_color=MUTED).pack(pady=(0, 25))

        btns = ui.CTkFrame(actions, fg_color="transparent")
        btns.pack(pady=8)
        self.button(btns, "LOST ITEM", lambda: self.report_form("Lost"), 190, primary=True).grid(row=0, column=0, padx=8, pady=8)
        self.button(btns, "FOUND ITEM", lambda: self.report_form("Found"), 190).grid(row=0, column=1, padx=8, pady=8)
        self.button(btns, "VIEW REPORTS", self.reports_page, 190).grid(row=0, column=2, padx=8, pady=8)

        stats = ui.CTkFrame(actions, fg_color="transparent")
        stats.pack(fill="x", padx=30, pady=30)
        for i, (label, value) in enumerate([("TOTAL REPORTS", total), ("LOST", lost), ("FOUND", found)]):
            stats.grid_columnconfigure(i, weight=1)
            card = ui.CTkFrame(stats, fg_color="#111a27", corner_radius=16)
            card.grid(row=0, column=i, padx=6, sticky="ew")
            ui.CTkLabel(card, text=label, text_color=MUTED, font=ui.CTkFont(size=11, weight="bold")).pack(pady=(17, 3))
            ui.CTkLabel(card, text=str(value), text_color=BLUE, font=ui.CTkFont(size=24, weight="bold")).pack(pady=(0, 17))

    def report_form(self, report_type):
        self.set_content()
        self.content.grid_rowconfigure(1, weight=1)
        self.title_label(self.content, f"{report_type} Report", 30).grid(row=0, column=0, sticky="w")
        scroll = ui.CTkScrollableFrame(self.content, fg_color=PANEL, corner_radius=22,
                                        border_color="#26364d", border_width=1)
        scroll.grid(row=1, column=0, sticky="nsew", pady=(18, 0))

        form = ui.CTkFrame(scroll.content, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=28, pady=24)
        form.grid_columnconfigure(0, weight=1)

        ui.CTkLabel(form, text="Personal Information", text_color=BLUE,
                     font=ui.CTkFont(size=19, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 12))
        fields = {}
        for r, (key, placeholder) in enumerate([("name", "Full Name"), ("email", "Email"), ("phone", "Phone Number")], 1):
            fields[key] = self.entry(form, placeholder, 600)
            fields[key].grid(row=r, column=0, sticky="ew", pady=6)
            if self.current_user.get(key if key != "name" else "name"):
                fields[key].insert(0, self.current_user.get(key if key != "name" else "name", ""))

        row = 4
        ui.CTkLabel(form, text="Where was it found?" if report_type == "Found" else "Where did you lose it?",
                     text_color=BLUE, font=ui.CTkFont(size=19, weight="bold")).grid(row=row, column=0, sticky="w", pady=(20, 10)); row += 1
        site_var = ui.StringVar(value="")
        site_frame = ui.CTkFrame(form, fg_color="transparent"); site_frame.grid(row=row, column=0, sticky="ew"); row += 1
        for i, site in enumerate(SITES):
            site_frame.grid_columnconfigure(i % 4, weight=1)
            ui.CTkRadioButton(site_frame, text=site, value=site, variable=site_var,
                               fg_color=BLUE_HOVER, hover_color=BLUE_HOVER, text_color=TEXT).grid(row=i // 4, column=i % 4, padx=4, pady=6, sticky="w")

        location = self.entry(form, "Specific Location (e.g., Room 201, Near Entrance)", 600)
        location.grid(row=row, column=0, sticky="ew", pady=8); row += 1

        date = None
        reward = None
        if report_type == "Lost":
            date = self.entry(form, "Date Lost (YYYY-MM-DD)", 600)
            date.grid(row=row, column=0, sticky="ew", pady=8); row += 1
            reward = self.entry(form, "Reward (Optional)", 600)
            reward.grid(row=row, column=0, sticky="ew", pady=8); row += 1

        ui.CTkLabel(form, text="Found Item?" if report_type == "Found" else "What Went Missing?",
                     text_color=BLUE, font=ui.CTkFont(size=19, weight="bold")).grid(row=row, column=0, sticky="w", pady=(18, 10)); row += 1
        item_var = ui.StringVar(value="")
        item_frame = ui.CTkFrame(form, fg_color="transparent"); item_frame.grid(row=row, column=0, sticky="ew"); row += 1
        for i, item in enumerate(ITEMS):
            item_frame.grid_columnconfigure(i % 4, weight=1)
            ui.CTkRadioButton(item_frame, text=item, value=item, variable=item_var,
                               fg_color=BLUE_HOVER, hover_color=BLUE_HOVER, text_color=TEXT).grid(row=i // 4, column=i % 4, padx=4, pady=6, sticky="w")

        others = self.entry(form, "If Others, specify item", 600)
        others.grid(row=row, column=0, sticky="ew", pady=8); row += 1
        desc = ui.CTkTextbox(form, height=120, corner_radius=16, fg_color="#111a27", border_color="#32445e", border_width=1)
        desc.grid(row=row, column=0, sticky="ew", pady=8); row += 1
        desc.insert("1.0", "Description")

        image_path = {"value": None}
        image_label = ui.CTkLabel(form, text="No image selected", text_color=MUTED)
        image_label.grid(row=row, column=0, sticky="w", pady=(2, 6)); row += 1

        def choose_image():
            from tkinter import filedialog
            path = filedialog.askopenfilename(title="Select item image", filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")])
            if path:
                image_path["value"] = path
                image_label.configure(text=Path(path).name, text_color=BLUE)

        self.button(form, "UPLOAD IMAGE (OPTIONAL)", choose_image, 220).grid(row=row, column=0, sticky="w", pady=6); row += 1
        msg = ui.CTkLabel(form, text="", text_color="#ff6b6b", wraplength=600)
        msg.grid(row=row, column=0, sticky="w", pady=6); row += 1

        actions = ui.CTkFrame(form, fg_color="transparent"); actions.grid(row=row, column=0, sticky="w", pady=12)
        self.button(actions, "BACK", self.dashboard_page, 140).pack(side="left", padx=(0, 8))

        def submit():
            name, email, phone = fields["name"].get().strip(), fields["email"].get().strip(), fields["phone"].get().strip()
            site, loc, item = site_var.get(), location.get().strip(), item_var.get()
            item_other = others.get().strip()
            description = desc.get("1.0", "end").strip()
            if description == "Description": description = ""
            if not name or not email or not phone or not site or not loc or not item:
                msg.configure(text="Please complete all required fields."); return
            if item == "Others":
                if not item_other:
                    msg.configure(text="Please specify the item."); return
                item = item_other
            report_date = date.get().strip() if date else ""
            report_reward = reward.get().strip() if reward else ""
            image_data = None
            if image_path["value"]:
                try:
                    with open(image_path["value"], "rb") as f:
                        image_data = base64.b64encode(f.read()).decode("ascii")
                except OSError:
                    pass
            conn = db()
            conn.execute("""INSERT INTO reports(id,type,name,email,phone,site,location,date,items,description,reward,image_data,hidden_info,timestamp)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (str(uuid.uuid4()), report_type, name, email, phone, site, loc, report_date,
                          item, description, report_reward, image_data, 0, now_iso()))
            conn.commit(); conn.close()
            self.show_message("Report Submitted", f"Your {report_type.lower()} report was submitted successfully.")
            self.dashboard_page()

        self.button(actions, "SUBMIT", submit, 160, primary=True).pack(side="left")

    def reports_page(self):
        self.set_content()
        self.content.grid_rowconfigure(2, weight=1)
        self.title_label(self.content, "All Reports", 30).grid(row=0, column=0, sticky="w")

        bar = ui.CTkFrame(self.content, fg_color=PANEL, corner_radius=14)
        bar.grid(row=1, column=0, sticky="ew", pady=15)
        self.search_var = ui.StringVar()
        search = self.entry(bar, "Search reports...", 320)
        search.configure(textvariable=self.search_var)
        search.pack(side="left", padx=12, pady=10)

        self.filter_var = ui.StringVar(value="All")
        ui.CTkOptionMenu(
            bar, values=["All", "Lost", "Found"], variable=self.filter_var,
            fg_color=PANEL_2, button_color=BLUE_HOVER,
            button_hover_color="#2563eb", width=110, height=34
        ).pack(side="left", padx=6)
        self.button(bar, "SEARCH", self.load_reports, 105, primary=True).pack(side="left", padx=6)
        self.button(bar, "SHOW ALL", self.show_all_reports, 105).pack(side="left", padx=6)
        self.button(bar, "BACK", self.dashboard_page, 95).pack(side="right", padx=12)

        holder = ui.CTkFrame(self.content, fg_color=PANEL, corner_radius=14,
                             border_color="#26364d", border_width=1)
        holder.grid(row=2, column=0, sticky="nsew")
        holder.grid_rowconfigure(0, weight=1)
        holder.grid_columnconfigure(0, weight=1)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "LostNoMore.Treeview",
            background="#111923", foreground=TEXT,
            fieldbackground="#111923", rowheight=34,
            borderwidth=0, relief="flat", font=("Segoe UI", 10)
        )
        style.configure(
            "LostNoMore.Treeview.Heading",
            background="#1b2a3d", foreground=TEXT,
            font=("Segoe UI", 10, "bold"), relief="flat", padding=(8, 8)
        )
        style.map("LostNoMore.Treeview",
                  background=[("selected", "#2563eb")],
                  foreground=[("selected", "white")])

        columns = ("type", "item", "reporter", "site", "location", "date", "email")
        self.report_tree = ttk.Treeview(holder, columns=columns, show="headings",
                                        style="LostNoMore.Treeview", selectmode="browse")
        headings = {
            "type": "TYPE", "item": "ITEM", "reporter": "REPORTED BY",
            "site": "CAMPUS", "location": "LOCATION", "date": "DATE", "email": "EMAIL"
        }
        widths = {"type": 80, "item": 150, "reporter": 160, "site": 190,
                  "location": 150, "date": 105, "email": 210}
        for col in columns:
            self.report_tree.heading(col, text=headings[col])
            self.report_tree.column(col, width=widths[col], minwidth=80,
                                    anchor="w", stretch=True)
        self.report_tree.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(holder, orient="vertical", command=self.report_tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.report_tree.configure(yscrollcommand=scroll.set)

        # Horizontal scrolling keeps all report columns accessible on smaller screens.
        hscroll = ttk.Scrollbar(holder, orient="horizontal", command=self.report_tree.xview)
        hscroll.grid(row=1, column=0, sticky="ew")
        self.report_tree.configure(xscrollcommand=hscroll.set)

        bottom = ui.CTkFrame(self.content, fg_color="transparent")
        bottom.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.report_count_label = ui.CTkLabel(bottom, text="", text_color=MUTED,
                                               font=ui.CTkFont(size=10))
        self.report_count_label.pack(side="left")
        ui.CTkLabel(bottom, text="Double-click a report to view its details.",
                    text_color=MUTED, font=ui.CTkFont(size=10)).pack(side="right")

        self.report_tree.bind("<Double-1>", self.show_report_details)

        # Admin-only report deletion controls. Regular users can view/search reports
        # but cannot delete them.
        if self.current_user and self.current_user.get("role") == "admin":
            delete_bar = ui.CTkFrame(self.content, fg_color="transparent")
            delete_bar.grid(row=4, column=0, sticky="ew", pady=(8, 0))
            self.button(delete_bar, "DELETE SELECTED REPORT", self.delete_selected_report, 220).pack(side="left")
            ui.CTkLabel(delete_bar, text="Select a report first. Deletion is permanent.",
                         text_color="#fca5a5", font=ui.CTkFont(size=10)).pack(side="left", padx=12)

        self.load_reports()

    def show_all_reports(self):
        self.search_var.set("")
        self.filter_var.set("All")
        self.load_reports()

    def load_reports(self):
        if not hasattr(self, "report_tree") or not self.report_tree.winfo_exists():
            return
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)

        q = getattr(self, "search_var", ui.StringVar()).get().strip()
        kind = getattr(self, "filter_var", ui.StringVar(value="All")).get()
        conn = db()
        sql = "SELECT * FROM reports WHERE 1=1"
        params = []
        if kind != "All":
            sql += " AND type=?"
            params.append(kind)
        if q:
            like = f"%{q}%"
            sql += " AND (name LIKE ? OR email LIKE ? OR items LIKE ? OR location LIKE ? OR site LIKE ? OR type LIKE ? OR description LIKE ?)"
            params += [like] * 7
        sql += " ORDER BY timestamp DESC"
        rows = conn.execute(sql, params).fetchall()
        conn.close()

        for row in rows:
            iid = self.report_tree.insert(
                "", "end", iid=str(row["id"]),
                values=(row["type"], row["items"], row["name"], row["site"],
                        row["location"], row["date"] or "N/A", row["email"])
            )
            if row["type"] == "Lost":
                self.report_tree.item(iid, tags=("lost",))
            else:
                self.report_tree.item(iid, tags=("found",))
        self.report_tree.tag_configure("lost", foreground="#93c5fd")
        self.report_tree.tag_configure("found", foreground="#86efac")

        # Make sure the first rows are visible immediately after loading.
        if rows:
            self.report_tree.selection_set(str(rows[0]["id"]))
            self.report_tree.see(str(rows[0]["id"]))
            self.report_tree.selection_remove(str(rows[0]["id"]))

        if hasattr(self, "report_count_label"):
            total = len(rows)
            label = "report" if total == 1 else "reports"
            self.report_count_label.configure(text=f"Showing {total} {label}")

    def show_report_details(self, _event=None):
        if not hasattr(self, "report_tree"):
            return
        selected = self.report_tree.selection()
        if not selected:
            return
        rid = selected[0]
        conn = db()
        row = conn.execute("SELECT * FROM reports WHERE id=?", (rid,)).fetchone()
        conn.close()
        if not row:
            return
        details = (
            f"Report Type: {row['type']}\n"
            f"Item: {row['items']}\n"
            f"Reported By: {row['name']}\n"
            f"Email: {row['email']}\n"
            f"Phone: {row['phone']}\n"
            f"Campus: {row['site']}\n"
            f"Location: {row['location']}\n"
            f"Date: {row['date'] or 'N/A'}\n"
            f"Reward: {row['reward'] or 'None'}\n\n"
            f"Description:\n{row['description'] or 'No description provided.'}"
        )
        messagebox.showinfo(f"{row['type']} Report — {row['items']}", details, parent=self)

    def delete_selected_report(self):
        if not self.current_user or self.current_user.get("role") != "admin":
            messagebox.showerror("Access Denied", "Only an administrator can delete reports.", parent=self)
            return
        selected = self.report_tree.selection() if hasattr(self, "report_tree") else ()
        if not selected:
            messagebox.showwarning("No Report Selected", "Select a report before deleting it.", parent=self)
            return
        rid = selected[0]
        conn = db(); row = conn.execute("SELECT type, items, name FROM reports WHERE id=?", (rid,)).fetchone(); conn.close()
        if not row:
            self.load_reports(); return
        if not messagebox.askyesno("Delete Report",
                                   f"Delete this {row['type'].lower()} report?\n\nItem: {row['items']}\nReported by: {row['name']}\n\nThis cannot be undone.",
                                   parent=self):
            return
        self.delete_report(rid)

    def delete_report(self, rid):
        if not self.current_user or self.current_user.get("role") != "admin":
            return
        conn = db()
        conn.execute("DELETE FROM reports WHERE id=?", (rid,))
        conn.commit(); conn.close()
        self.load_reports()

    def admin_page(self):
        self.set_content()
        self.content.grid_rowconfigure(2, weight=1)
        self.title_label(self.content, "Admin Panel", 30).grid(row=0, column=0, sticky="w")

        conn = db()
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        reports = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        conn.close()

        summary = self.glass(self.content)
        summary.grid(row=1, column=0, sticky="ew", pady=(18, 12))
        ui.CTkLabel(summary, text=f"Registered Users: {users}    |    Total Reports: {reports}",
                     text_color=BLUE, font=ui.CTkFont(size=17, weight="bold")).pack(anchor="w", padx=20, pady=14)

        users_box = self.glass(self.content)
        users_box.grid(row=2, column=0, sticky="nsew")
        users_box.grid_rowconfigure(1, weight=1); users_box.grid_columnconfigure(0, weight=1)
        ui.CTkLabel(users_box, text="ACCOUNT MANAGEMENT", text_color=BLUE,
                     font=ui.CTkFont(size=17, weight="bold")).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 8))

        user_holder = tk.Frame(users_box, bg=PANEL)
        user_holder.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 10))
        user_holder.grid_rowconfigure(0, weight=1); user_holder.grid_columnconfigure(0, weight=1)
        cols = ("id", "name", "email", "phone", "role", "created")
        style = ttk.Style(self)
        style.configure("LostNoMore.Users.Treeview", background="#111923", foreground=TEXT,
                        fieldbackground="#111923", rowheight=32, font=("Segoe UI", 10))
        style.configure("LostNoMore.Users.Treeview.Heading", background="#1b2a3d", foreground=TEXT,
                        font=("Segoe UI", 10, "bold"), padding=(7, 7))
        style.map("LostNoMore.Users.Treeview", background=[("selected", "#2563eb")], foreground=[("selected", "white")])
        self.user_tree = ttk.Treeview(user_holder, columns=cols, show="headings", selectmode="browse", style="LostNoMore.Users.Treeview")
        heads = {"id":"ID", "name":"NAME", "email":"EMAIL", "phone":"PHONE", "role":"ROLE", "created":"CREATED"}
        widths = {"id":55, "name":180, "email":230, "phone":130, "role":90, "created":180}
        for col in cols:
            self.user_tree.heading(col, text=heads[col]); self.user_tree.column(col, width=widths[col], minwidth=60, anchor="w")
        self.user_tree.grid(row=0, column=0, sticky="nsew")
        uscroll = ttk.Scrollbar(user_holder, orient="vertical", command=self.user_tree.yview); uscroll.grid(row=0, column=1, sticky="ns")
        self.user_tree.configure(yscrollcommand=uscroll.set)

        actions = ui.CTkFrame(users_box, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
        self.button(actions, "DELETE SELECTED ACCOUNT", self.delete_selected_account, 230).pack(side="left")
        self.button(actions, "MANAGE REPORTS", self.reports_page, 180, primary=True).pack(side="left", padx=8)
        ui.CTkLabel(actions, text="You cannot delete the currently logged-in account.",
                     text_color="#fca5a5", font=ui.CTkFont(size=10)).pack(side="left", padx=8)
        self.load_users()

    def load_users(self):
        if not hasattr(self, "user_tree") or not self.user_tree.winfo_exists():
            return
        for item in self.user_tree.get_children(): self.user_tree.delete(item)
        conn = db(); rows = conn.execute("SELECT id,name,email,phone,role,created_at FROM users ORDER BY id").fetchall(); conn.close()
        for row in rows:
            self.user_tree.insert("", "end", iid=str(row["id"]),
                                   values=(row["id"], row["name"], row["email"], row["phone"], row["role"], row["created_at"][:19].replace("T", " ")))

    def delete_selected_account(self):
        if not self.current_user or self.current_user.get("role") != "admin":
            messagebox.showerror("Access Denied", "Only an administrator can delete accounts.", parent=self); return
        selected = self.user_tree.selection() if hasattr(self, "user_tree") else ()
        if not selected:
            messagebox.showwarning("No Account Selected", "Select an account before deleting it.", parent=self); return
        uid = int(selected[0])
        conn = db(); row = conn.execute("SELECT id,name,email,role FROM users WHERE id=?", (uid,)).fetchone(); conn.close()
        if not row: self.load_users(); return
        if str(row["id"]) == str(self.current_user.get("id")):
            messagebox.showerror("Cannot Delete", "You cannot delete the account currently logged in.", parent=self); return
        if row["role"] == "admin":
            conn = db(); admin_count = conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]; conn.close()
            if admin_count <= 1:
                messagebox.showerror("Cannot Delete", "The system must keep at least one administrator account.", parent=self); return
        if not messagebox.askyesno("Delete Account",
                                   f"Delete this account permanently?\n\nName: {row['name']}\nEmail: {row['email']}\nRole: {row['role']}\n\nThis cannot be undone.",
                                   parent=self): return
        conn = db(); conn.execute("DELETE FROM users WHERE id=?", (uid,)); conn.commit(); conn.close()
        self.load_users()

    def export_pdf(self):
        conn = db(); rows = conn.execute("SELECT * FROM reports ORDER BY timestamp DESC").fetchall(); conn.close()
        path = APP_DIR / "LostNoMore_Reports.pdf"
        pdf = canvas.Canvas(str(path), pagesize=letter)
        width, height = letter
        y = height - 45
        pdf.setTitle("LostNoMore Reports")
        pdf.setFont("Helvetica-Bold", 18); pdf.drawString(40, y, "LostNoMore - Reports"); y -= 28
        pdf.setFont("Helvetica", 8)
        for row in rows:
            lines = [f"[{row['type']}] {row['items']} | {row['name']} | {row['site']}",
                     f"Location: {row['location']} | Date: {row['date'] or 'N/A'} | Email: {row['email']}"]
            for line in lines:
                if y < 45: pdf.showPage(); y = height - 45; pdf.setFont("Helvetica", 8)
                pdf.drawString(40, y, line[:125]); y -= 13
            y -= 4
        pdf.save(); self.show_message("PDF Exported", f"Saved as:\n{path}")

    def show_message(self, title, message):
        win = ui.CTkToplevel(self); win.title(title); win.geometry("440x210"); win.transient(self); win.grab_set()
        ui.CTkLabel(win, text=message, justify="center", wraplength=380, text_color=TEXT).pack(expand=True, padx=20)
        self.button(win, "OK", win.destroy, 120, primary=True).pack(pady=20)


if __name__ == "__main__":
    init_db()
    app = LostNoMore()
    app.mainloop()
