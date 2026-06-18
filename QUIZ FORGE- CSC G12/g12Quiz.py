import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import urllib.parse
import json
import os
import html
import time
import random
import datetime
# ─────────────────────────── CONSTANTS ───────────────────────────
APP_TITLE          = "QUIZ FORGE"
DATA_FILE          = "quiz_leaderboard.json"
FONT_MONO          = "Consolas"
QUESTION_BANK_FILE = "questions.json"
C = {
    "bg":         "#0d0d0d",
    "bg2":        "#141414",
    "bg3":        "#1a1a1a",
    "panel":      "#1f1f1f",
    "border":     "#2a2a2a",
    "accent":     "#f5a623",
    "accent_dim": "#b37a1a",
    "accent_dark":"#3d2800",
    "red":        "#e05252",
    "red_dark":   "#3d1414",
    "green":      "#5ec96e",
    "green_dark": "#0d2d12",
    "fg":         "#e8e8e8",
    "fg_dim":     "#888888",
    "fg_faint":   "#444444",
    "white":      "#ffffff",
    "radio_sel":  "#f5a623",
}
DARK_THEME = {
    "bg":         "#0d0d0d",
    "bg2":        "#141414",
    "bg3":        "#1a1a1a",
    "panel":      "#1f1f1f",
    "border":     "#2a2a2a",
    "accent":     "#f5a623",
    "accent_dim": "#b37a1a",
    "accent_dark":"#3d2800",
    "red":        "#e05252",
    "red_dark":   "#3d1414",
    "green":      "#5ec96e",
    "green_dark": "#0d2d12",
    "fg":         "#e8e8e8",
    "fg_dim":     "#888888",
    "fg_faint":   "#444444",
    "white":      "#ffffff",
    "radio_sel":  "#f5a623",
}
LIGHT_THEME = {
    "bg":         "#f5f5f5",
    "bg2":        "#ffffff",
    "bg3":        "#eeeeee",
    "panel":      "#ffffff",
    "border":     "#d0d0d0",
    "accent":     "#0a84ff",
    "accent_dim": "#0066cc",
    "accent_dark":"#cce4ff",
    "red":        "#d32f2f",
    "red_dark":   "#ffebee",
    "green":      "#2e7d32",
    "green_dark": "#e8f5e9",
    "fg":         "#111111",
    "fg_dim":     "#555555",
    "fg_faint":   "#888888",
    "white":      "#ffffff",
    "radio_sel":  "#0a84ff",
}
THEMES = {"Dark": DARK_THEME, "Light": LIGHT_THEME}
CATEGORIES = {
    "Any Category":    0,
    "General Knowledge": 9,
    "Books":           10,
    "Film":            11,
    "Music":           12,
    "Science & Nature":17,
    "Computers":       18,
    "Mathematics":     19,
    "History":         23,
    "Geography":       22,
    "Politics":        24,
    "Art":             25,
    "Animals":         27,
    "Vehicles":        28,
    "Sports":          21,
}
DIFFICULTIES = ["Easy", "Medium", "Hard"]
Q_COUNTS     = ["10", "20", "30", "Custom"]
Q_TYPES      = ["Multiple Choice", "True / False"]
GAME_MODES   = ["Practice", "Timed", "Sudden Death"]
MAX_QUESTIONS = 30 
# ─────────────────────────── LEADERBOARD ─────────────────────────
def load_leaderboard():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []
def save_leaderboard(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[LEADERBOARD] Save failed: {e}")
def add_score(entry: dict):
    lb = load_leaderboard()
    lb.append(entry)
    lb.sort(key=lambda x: (-x["score"], x.get("time", 9999)))
    lb = lb[:20]
    save_leaderboard(lb)
# ─────────────────────────── QUESTION BANK ───────────────────────
def load_question_bank():
    try:
        with open(QUESTION_BANK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
def get_local_questions(category, difficulty, amount):
    bank = load_question_bank()
    pool = []

    # 1. Try to get questions from the specific category
    if category == "Any Category" or category not in bank:
        # Pool EVERYTHING if "Any Category" is picked
        for cat_qs in bank.values():
            pool.extend(cat_qs)
    else:
        pool = bank.get(category, [])
    filtered = [q for q in pool if q.get("difficulty", "").lower() == difficulty.lower()]
    if len(filtered) < amount:
        filtered = pool
    if not filtered:
        for cat_qs in bank.values():
            filtered.extend(cat_qs)

    random.shuffle(filtered)
    for q in filtered:
        if "answers" in q:
            random.shuffle(q["answers"]) 
            
    return filtered[:amount]
# ─────────────────────────── API ─────────────────────────────────
def fetch_questions(amount, category_id, difficulty, q_type):
    base   = "https://opentdb.com/api.php?"
    params = {"amount": amount, "type": q_type}
    if category_id:
        params["category"] = category_id
    if difficulty and difficulty.lower() != "any":
        params["difficulty"] = difficulty.lower()
    url = base + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data["response_code"] == 0:
                return data["results"], None
            return None, "Not enough questions from API."
    except Exception:
        return None, "Offline"
def parse_question(raw):
    q_text  = html.unescape(raw["question"])
    correct = html.unescape(raw["correct_answer"])
    wrongs  = [html.unescape(a) for a in raw["incorrect_answers"]]
    all_ans = wrongs + [correct]
    random.shuffle(all_ans)
    return {
        "question":   q_text,
        "correct":    correct,
        "answers":    all_ans,
        "category":   html.unescape(raw["category"]),
        "difficulty": raw["difficulty"],
    }
def get_questions(cfg):
    """
    Fetch strategy:
      1. Try API for the full amount requested.
      2. If API returns fewer than needed (or fails), fill the gap from
         the local bank.
      3. If combined total is still zero, return None.
    Returns (questions_list, source_note) or (None, error_msg).
    """
    amount   = cfg["amount"]
    cat      = cfg["category"]
    cat_id   = cfg["category_id"]
    diff     = cfg["difficulty"]
    q_type   = cfg["q_type"]
    api_qs, api_err = None, "Offline"
    try:
        api_qs, api_err = fetch_questions(amount, cat_id, diff, q_type)
    except:
        pass

    api_parsed = [parse_question(q) for q in api_qs] if api_qs else []
    if len(api_parsed) >= amount:
        return api_parsed[:amount], None
    needed = amount - len(api_parsed)
    local_qs = get_local_questions(cat, diff, needed)
    
    combined = api_parsed + local_qs
    
    if combined:
        return combined[:amount], None
    return None, "System Error: No questions found locally or online."
# ─────────────────────────── WIDGETS ─────────────────────────────
def styled_button(parent, text, command, style="primary", width=18):
    if style == "primary":
        bg, fg, abg = C["accent"], C["bg"], C["accent_dim"]
    elif style == "danger":
        bg, fg, abg = C["red"], C["white"], "#a03030"
    elif style == "ghost":
        bg, fg, abg = C["bg3"], C["fg_dim"], C["border"]
    else:
        bg, fg, abg = C["panel"], C["fg"], C["bg3"]
    return tk.Button(
        parent, text=text, command=command,
        font=(FONT_MONO, 10, "bold"),
        bg=bg, fg=fg,
        activebackground=abg, activeforeground=fg,
        relief="flat", bd=0, cursor="hand2",
        width=width, pady=8,
        highlightthickness=1,
        highlightbackground=C["border"],
        highlightcolor=C["accent"],
    )
def panel_frame(parent, bg=None):
    return tk.Frame(parent, bg=bg or C["panel"],
                    highlightthickness=1,
                    highlightbackground=C["border"])
def separator(parent):
    return tk.Frame(parent, bg=C["border"], height=1)
def add_footer(parent):
    tk.Label(
        parent,
        text="◆ Developed by CSC GROUP 12 ◆",
        font=("Segoe UI", 10, "bold"),
        fg=C["accent"],
        bg=C["bg"],
    ).place(relx=1, rely=1, anchor="se", x=-12, y=-12)  
# ─────────────────────────── APP ─────────────────────────────────
class QuizForge(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.resizable(True, True)
        self.minsize(820, 600)
        try:
            self.state("zoomed")
        except Exception:
            self.attributes("-zoomed", True)
        self.configure(bg=C["bg"])
        self._center(900, 660)
        self._current_frame = None
        self.player_name    = "Player"
        self.current_theme  = "Dark"
        self._theme_btn = tk.Button(
            self,
            text="☀  LIGHT",
            font=(FONT_MONO, 9, "bold"),
            bg=C["bg3"], fg=C["fg_dim"],
            activebackground=C["border"],
            activeforeground=C["fg"],
            relief="flat", bd=0, cursor="hand2",
            padx=10, pady=4,
            command=self._toggle_theme,
        )
        self._theme_btn.place(relx=1.0, rely=0.0, anchor="ne", x=-8, y=8)
        self.bind("<Configure>", self._on_resize)
        self.show_home()
    def _center(self, w, h):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
    def _on_resize(self, event):
        """Keep theme button pinned to top-right on window resize."""
        self._theme_btn.lift()
    def _toggle_theme(self):
        if self.current_theme == "Dark":
            self.current_theme = "Light"
            new_label = "🌙  DARK"
        else:
            self.current_theme = "Dark"
            new_label = "☀  LIGHT"
        for k, v in THEMES[self.current_theme].items():
            C[k] = v
        self.configure(bg=C["bg"])
        self._theme_btn.config(
            text=new_label,
            bg=C["bg3"], fg=C["fg_dim"],
            activebackground=C["border"],
        )
        if self._current_frame:
            cls  = type(self._current_frame)
            args = getattr(self._current_frame, "_init_args", ())
            self._switch(cls, *args)
    def _switch(self, frame_cls, *args, **kwargs):
        if self._current_frame:
            self._current_frame.destroy()
        frame = frame_cls(self, *args, **kwargs)
        frame._init_args = args      
        frame.pack(fill="both", expand=True)
        self._current_frame = frame
        self._theme_btn.lift() 

    def show_home(self):        self._switch(HomeScreen)
    def show_name(self):        self._switch(NameScreen)
    def show_setup(self):       self._switch(SetupScreen)
    def show_leaderboard(self): self._switch(LeaderboardScreen)
    def show_loading(self, cfg):              self._switch(LoadingScreen, cfg)
    def show_quiz(self, questions, cfg):      self._switch(QuizScreen, questions, cfg)
    def show_results(self, result_data, cfg): self._switch(ResultScreen, result_data, cfg)
# ─────────────────────────── HOME ────────────────────────────────
class HomeScreen(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=C["bg"])
        self._build()
    def _build(self):
        tk.Frame(self, bg=C["accent"], height=4).pack(fill="x")
        tk.Frame(self, bg=C["bg2"], height=2).pack(fill="x")
        ctr = tk.Frame(self, bg=C["bg"])
        ctr.pack(expand=True)
        logo_lines = [
            "  ██████  ██    ██ ██ ███████     ███████  ██████  ██████   ██████  ███████ ",
            " ██    ██ ██    ██ ██    ███       ██      ██    ██ ██   ██ ██       ██     ",
            " ██    ██ ██    ██ ██   ███        █████   ██    ██ ██████  ██   ███ █████  ",
            " ██ ▄▄ ██ ██    ██ ██  ███         ██      ██    ██ ██   ██ ██    ██ ██     ",
            "  ██████   ██████  ██ ███████      ██       ██████  ██   ██  ██████  ███████",
        ]
        lf = tk.Frame(ctr, bg=C["bg"])
        lf.pack(pady=(40, 4))
        for i, line in enumerate(logo_lines):
            tk.Label(lf, text=line, font=("Courier New", 10, "bold"),
                     bg=C["bg"],
                     fg=C["accent"] if i % 2 == 0 else C["accent_dim"]).pack()

        tk.Label(ctr, text="[ TEST YOUR KNOWLEDGE. TRACK YOUR PROGRESS. ]",
                 font=(FONT_MONO, 9), bg=C["bg"], fg=C["fg_dim"]).pack(pady=(4, 28))

        modes_frame = tk.Frame(ctr, bg=C["bg"])
        modes_frame.pack()
        for i, (title, desc) in enumerate([
            ("⏱  TIMED",        "Race against the clock.\nEach question has 20s."),
            ("📖  PRACTICE",    "No timer. No pressure.\nLearn at your own pace."),
            ("☠  SUDDEN DEATH", "One wrong answer\nand it's all over."),
        ]):
            card = panel_frame(modes_frame)
            card.grid(row=0, column=i, padx=8, ipadx=12, ipady=12)
            tk.Label(card, text=title, font=(FONT_MONO, 9, "bold"),
                     bg=C["panel"], fg=C["accent"]).pack(pady=(8, 2))
            tk.Label(card, text=desc, font=(FONT_MONO, 8),
                     bg=C["panel"], fg=C["fg_dim"], justify="center").pack(padx=10, pady=(0, 8))

        btn_frame = tk.Frame(ctr, bg=C["bg"])
        btn_frame.pack(pady=28)
        styled_button(btn_frame, "▶  START QUIZ",
                      self.master.show_name, "primary", 20).pack(side="left", padx=8)
        styled_button(btn_frame, "🏆  LEADERBOARD",
                      self.master.show_leaderboard, "secondary", 20).pack(side="left", padx=8)
        add_footer(self)
# ─────────────────────────── NAME ENTRY ──────────────────────────
class NameScreen(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=C["bg"])
        self.name_var = tk.StringVar(
            value=master.player_name if master.player_name != "Player" else "")
        self._build()
    def _build(self):
        tk.Frame(self, bg=C["accent"], height=4).pack(fill="x")

        hdr = tk.Frame(self, bg=C["bg2"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="◈  WHO ARE YOU?",
                 font=(FONT_MONO, 13, "bold"),
                 bg=C["bg2"], fg=C["accent"], padx=20).pack(side="left", pady=12)
        styled_button(hdr, "← BACK",
                      self.master.show_home, "ghost", 10).pack(side="right", padx=15, pady=8)
        ctr = tk.Frame(self, bg=C["bg"])
        ctr.pack(expand=True)
        tk.Label(ctr, text="⬡",
                 font=(FONT_MONO, 42), bg=C["bg"], fg=C["accent"]).pack(pady=(0, 8))
        add_footer(self)
        tk.Label(ctr,
                 text="Enter your name before the quiz starts.\nIt will appear on the leaderboard.",
                 font=(FONT_MONO, 10), bg=C["bg"], fg=C["fg_dim"],
                 justify="center").pack(pady=(0, 24))
        input_panel = panel_frame(ctr)
        input_panel.pack(ipadx=30, ipady=20)
        tk.Label(input_panel, text="  PLAYER NAME",
                 font=(FONT_MONO, 9, "bold"),
                 bg=C["panel"], fg=C["accent"]).pack(anchor="w", pady=(10, 4))
        separator(input_panel).pack(fill="x", padx=8, pady=(0, 10))
        self.entry = tk.Entry(
            input_panel,
            textvariable=self.name_var,
            font=(FONT_MONO, 14, "bold"),
            width=22,
            bg=C["bg2"], fg=C["accent"],
            insertbackground=C["accent"],
            relief="flat", bd=0,
            highlightthickness=2,
            highlightbackground=C["border"],
            highlightcolor=C["accent"],
        )
        self.entry.pack(padx=12, pady=(0, 6))
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda e: self._proceed())
        tk.Label(input_panel,
                 text="  Max 20 characters. Letters, numbers, spaces, _ - . only.",
                 font=(FONT_MONO, 8), bg=C["panel"], fg=C["fg_faint"]).pack(
                     anchor="w", padx=8, pady=(0, 10))
        self.error_lbl = tk.Label(ctr, text="",
                                  font=(FONT_MONO, 9),
                                  bg=C["bg"], fg=C["red"])
        self.error_lbl.pack(pady=6)
        styled_button(ctr, "CONTINUE  ▶",
                      self._proceed, "primary", 20).pack(pady=4)
        tk.Label(ctr,
                 text="Step 1 of 2  —  Name  →  Configure  →  Play",
                 font=(FONT_MONO, 8), bg=C["bg"], fg=C["fg_faint"]).pack(pady=(14, 0))
    def _proceed(self):
        raw = self.name_var.get().strip()
        if not raw:
            self.error_lbl.config(text="✗  Name cannot be empty.")
            return
        if len(raw) > 20:
            self.error_lbl.config(text="✗  Name too long (max 20 chars).")
            return
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-.")
        if not all(c in allowed for c in raw):
            self.error_lbl.config(text="✗  Use letters, numbers, spaces, _ - . only.")
            return
        self.master.player_name = raw
        self.master.show_setup()
# ─────────────────────────── SETUP ───────────────────────────────
class SetupScreen(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=C["bg"])
        self.cat_var   = tk.StringVar(value="General Knowledge")
        self.diff_var  = tk.StringVar(value="Easy")
        self.count_var = tk.StringVar(value="10")
        self.type_var  = tk.StringVar(value="Multiple Choice")
        self.mode_var  = tk.StringVar(value="Practice")
        self.custom_q  = tk.StringVar(value="15")
        self._build()
    def _build(self):
        tk.Frame(self, bg=C["accent"], height=4).pack(fill="x")
        title_bar = tk.Frame(self, bg=C["bg2"])
        title_bar.pack(fill="x")
        tk.Label(title_bar,
                 text=f"  ◈  QUIZ CONFIGURATION  —  {self.master.player_name}",
                 font=(FONT_MONO, 12, "bold"),
                 bg=C["bg2"], fg=C["accent"], anchor="w", padx=10).pack(side="left", pady=10)
        add_footer(self)
        styled_button(title_bar, "← BACK",
                      self.master.show_name, "ghost", 10).pack(side="right", padx=15, pady=8)
        step_bar = tk.Frame(self, bg=C["bg3"])
        step_bar.pack(fill="x", padx=24, pady=(8, 2))
        tk.Label(step_bar,
                 text="  Step 2 of 2  —  Configure your quiz, then hit FORGE.",
                 font=(FONT_MONO, 8), bg=C["bg3"], fg=C["fg_dim"]).pack(anchor="w", pady=4)
        outer = tk.Frame(self, bg=C["bg"])
        outer.pack(expand=True, padx=24, pady=8, fill="both")
        left = tk.Frame(outer, bg=C["bg"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        self._section(left, "CATEGORY", list(CATEGORIES.keys()), self.cat_var)
        self._section(left, "DIFFICULTY", DIFFICULTIES, self.diff_var)
        right = tk.Frame(outer, bg=C["bg"])
        right.pack(side="right", fill="both", expand=True, padx=(12, 0))
        self._section(right, "QUESTION TYPE", Q_TYPES, self.type_var)
        self._section(right, "GAME MODE", GAME_MODES, self.mode_var)
        self._count_section(right)
        bottom = tk.Frame(self, bg=C["bg"])
        bottom.pack(pady=10)
        tk.Label(bottom,
                 font=(FONT_MONO, 8), bg=C["bg"], fg=C["accent_dim"]).pack(pady=(0, 6))
        styled_button(bottom, "▶  FORGE THE QUIZ",
                      self._start, "primary", 22).pack()
    def _radio(self, parent, text, variable, value, command=None):
        """Create a single radio button with correct theme colours."""
        rb = tk.Radiobutton(
            parent,
            text=text,
            variable=variable,
            value=value,
            indicatoron=False,
            width=18,
            bg=C["bg3"],
            fg=C["fg"],
            selectcolor=C["accent"],
            activebackground=C["accent"],
            activeforeground=C["bg"],
            relief="flat",
            font=(FONT_MONO, 9, "bold"),
            cursor="hand2"
)
        if command:
            rb.config(command=command)
        return rb
    def _section(self, parent, title, options, var):
        box = panel_frame(parent)
        box.pack(fill="x", pady=5)
        tk.Label(box, text=f"  {title}",
                 font=(FONT_MONO, 9, "bold"),
                 bg=C["panel"], fg=C["accent"]).pack(anchor="w", pady=(8, 4))
        separator(box).pack(fill="x", padx=8)
        inner = tk.Frame(box, bg=C["panel"])
        inner.pack(fill="x", padx=8, pady=4)
        cols = 3 if len(options) >= 6 else 2
        for i, opt in enumerate(options):
            self._radio(inner, opt, var, opt).grid(
                row=i // cols, column=i % cols, sticky="w", padx=6, pady=2)
    def _count_section(self, parent):
        box = panel_frame(parent)
        box.pack(fill="x", pady=5)
        tk.Label(box, text="  QUESTION COUNT",
                 font=(FONT_MONO, 9, "bold"),
                 bg=C["panel"], fg=C["accent"]).pack(anchor="w", pady=(8, 4))
        separator(box).pack(fill="x", padx=8)
        inner = tk.Frame(box, bg=C["panel"])
        inner.pack(fill="x", padx=8, pady=4)
        for i, opt in enumerate(Q_COUNTS):
            self._radio(inner, opt, self.count_var, opt,
                        command=self._toggle_custom).grid(
                row=0, column=i, sticky="w", padx=6, pady=2)
        cf = tk.Frame(box, bg=C["panel"])
        cf.pack(fill="x", padx=8, pady=(2, 4))
        tk.Label(cf, text=f"Custom (1–{MAX_QUESTIONS}):",
                 font=(FONT_MONO, 8), bg=C["panel"], fg=C["fg_dim"]).pack(side="left")
        self.custom_entry = tk.Entry(
            cf, textvariable=self.custom_q,
            font=(FONT_MONO, 9), width=5,
            bg=C["bg2"], fg=C["accent"],
            insertbackground=C["accent"],
            relief="flat", bd=1, state="disabled",
        )
        self.custom_entry.pack(side="left", padx=8)
    def _toggle_custom(self):
        self.custom_entry.config(
            state="normal" if self.count_var.get() == "Custom" else "disabled")
    def _start(self):
        count_val = self.count_var.get()
        if count_val == "Custom":
            try:
                n = int(self.custom_q.get())
                if not 1 <= n <= MAX_QUESTIONS:
                    raise ValueError
                amount = n
            except ValueError:
                messagebox.showerror("Invalid Input",
                                     f"Custom amount must be 1–{MAX_QUESTIONS}.")
                return
        else:
            amount = int(count_val)
        cfg = {
            "player":       self.master.player_name,
            "category":     self.cat_var.get(),
            "category_id":  CATEGORIES[self.cat_var.get()],
            "difficulty":   self.diff_var.get(),
            "q_type":       "boolean" if "True" in self.type_var.get() else "multiple",
            "q_type_label": self.type_var.get(),
            "amount":       amount,
            "mode":         self.mode_var.get(),
            "theme":        self.master.current_theme,
        }
        self.master.show_loading(cfg)
# ─────────────────────────── LOADING ─────────────────────────────
class LoadingScreen(tk.Frame):
    def __init__(self, master, cfg):
        super().__init__(master, bg=C["bg"])
        self.cfg    = cfg
        self._dots  = 0
        self.anim_id = None
        self._build()
        self.after(200, self._animate)
        self.after(400, self._fetch)
    def _build(self):
        ctr = tk.Frame(self, bg=C["bg"])
        ctr.pack(expand=True)
        tk.Label(ctr, text="⚙",
                 font=(FONT_MONO, 48), bg=C["bg"], fg=C["accent"]).pack()
        tk.Label(ctr, text="FETCHING QUESTIONS",
                 font=(FONT_MONO, 12, "bold"), bg=C["bg"], fg=C["fg"]).pack(pady=8)
        self.dot_label = tk.Label(ctr, text="",
                                  font=(FONT_MONO, 12), bg=C["bg"], fg=C["accent"])
        self.dot_label.pack()
        tk.Label(ctr,
                 text=f"{self.cfg['category']}  ·  {self.cfg['difficulty']}  ·  {self.cfg['mode']}",
                 font=(FONT_MONO, 9), bg=C["bg"], fg=C["fg_dim"]).pack(pady=10)
    def _animate(self):
        self._dots = (self._dots + 1) % 4
        self.dot_label.config(text="▓" * self._dots + "░" * (3 - self._dots))
        self.anim_id = self.after(300, self._animate)
    def _fetch(self):
        if self.anim_id:
            self.after_cancel(self.anim_id)
        questions, error = get_questions(self.cfg)
        if questions:
            self.master.show_quiz(questions, self.cfg)
            return
        messagebox.showerror(
            "No Questions Found",
            f"{error}\n\nTry a different category, difficulty, or question count."
        )
        self.master.show_setup()
# ─────────────────────────── QUIZ ────────────────────────────────
class QuizScreen(tk.Frame):
    TIMED_SECONDS = 20
    def __init__(self, master, questions, cfg):
        super().__init__(master, bg=C["bg"])
        self.questions   = questions
        self.cfg         = cfg
        self.idx         = 0
        self.score       = 0
        self.streak      = 0
        self.best_streak = 0
        self.start_time  = time.time()
        self.wrong_list  = []
        self.answered    = False
        self._timer_id   = None
        self._time_left  = self.TIMED_SECONDS
        self._build()
        self._load_question()
    def _build(self):
        self.top_bar = tk.Frame(self, bg=C["bg2"])
        self.top_bar.pack(fill="x")
        self.master.bind("<Key-a>", lambda e: self.safe_invoke(0))
        self.master.bind("<Key-b>", lambda e: self.safe_invoke(1))
        self.master.bind("<Key-c>", lambda e: self.safe_invoke(2))
        self.master.bind("<Key-d>", lambda e: self.safe_invoke(3))
        self.mode_lbl = tk.Label(self.top_bar, text="", font=(FONT_MONO, 9, "bold"), bg=C["bg2"], fg=C["accent"])
        self.mode_lbl.pack(side="left", padx=16, pady=8)
        self.player_lbl = tk.Label(self.top_bar, text="", font=(FONT_MONO, 9), bg=C["bg2"], fg=C["fg_dim"])
        self.player_lbl.pack(side="left", padx=4)
        self.score_lbl = tk.Label(self.top_bar, text="", font=(FONT_MONO, 9), bg=C["bg2"], fg=C["fg"])
        self.score_lbl.pack(side="right", padx=16, pady=8)
        self.streak_lbl = tk.Label(self.top_bar, text="🔥 0", bg=C["bg2"], fg=C["accent"], font=(FONT_MONO, 9, "bold"))
        self.streak_lbl.pack(side="right", padx=10)
        self.prog_canvas = tk.Canvas(self, bg=C["bg3"], height=6, highlightthickness=0)
        self.prog_canvas.pack(fill="x")
        self.timer_bar = tk.Canvas(self, bg=C["bg3"], height=4, highlightthickness=0)
        self.q_panel = panel_frame(self)
        self.q_panel.pack(fill="x", padx=24, pady=(12, 8))
        self.cat_lbl = tk.Label(self.q_panel, text="", font=(FONT_MONO, 8), bg=C["panel"], fg=C["fg_dim"])
        self.cat_lbl.pack(anchor="w", padx=14, pady=(10, 2))

        self.q_lbl = tk.Label(self.q_panel, text="", font=(FONT_MONO, 12, "bold"), bg=C["panel"], fg=C["fg"], wraplength=700, justify="left")
        self.q_lbl.pack(anchor="w", padx=14, pady=(2, 14))

        self.ans_frame = tk.Frame(self, bg=C["bg"])
        self.ans_frame.pack(fill="both", expand=True, padx=24, pady=4)
        self.ans_btns = []

        self.bottom = tk.Frame(self, bg=C["bg"])
        self.bottom.pack(fill="x", padx=24, pady=10)

        self.timer_lbl = tk.Label(self.bottom, text="", font=(FONT_MONO, 20, "bold"), bg=C["bg"], fg=C["accent"])
        
        self.next_btn = styled_button(self.bottom, "NEXT  ▶", self._next_question, "primary", 14)
        self.next_btn.pack(side="right")
        self.next_btn.config(state="disabled")

        styled_button(self.bottom, "✕  QUIT", self._quit_quiz, "ghost", 10).pack(side="left")

    def safe_invoke(self, index):
        if not self.answered and index < len(self.ans_btns):
            self.ans_btns[index].invoke()
    def _tick(self):
        if self.answered: return
        self._time_left -= 1

        self.timer_bar.delete("all")
        w = self.timer_bar.winfo_width()
        pct = self._time_left / self.TIMED_SECONDS
        self.timer_bar.create_rectangle(0, 0, int(w * pct), 4, fill=C["accent"] if pct > 0.3 else C["red"], outline="")
        self.timer_lbl.config(text=str(max(0, self._time_left)))

        if self._time_left <= 0:
            self._answer(None, "TIMEOUT")
        else:
            self._timer_id = self.after(1000, self._tick)

    def _answer(self, btn, val):
        if self.answered: return
        self.answered = True
        if self._timer_id: self.after_cancel(self._timer_id)

        correct_ans = self.questions[self.idx]["correct"]
        is_correct = (val == correct_ans)

        if is_correct:
            self.score += 100 + (self.streak * 10)
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
            if btn: btn.config(bg=C["green_dark"], highlightbackground=C["green"])
        else:
            self.streak = 0
            if btn: btn.config(bg=C["red_dark"], highlightbackground=C["red"])
            self.wrong_list.append({"q": self.questions[self.idx]["question"], "a": correct_ans})
            # Visual feedback for the right answer
            for b in self.ans_btns:
                if b.cget("text").split(".  ")[-1] == correct_ans:
                    b.config(bg=C["green_dark"], highlightbackground=C["green"])

        self.streak_lbl.config(text=f"🔥 {self.streak}")
        self.score_lbl.config(text=f"Q {self.idx+1}/{len(self.questions)}  │  SCORE: {self.score}")
        self.next_btn.config(state="normal")

        if self.cfg["mode"] == "Sudden Death" and not is_correct:
            self.after(1500, self._finish)

    def _next_question(self):
        self.idx += 1
        if self.idx >= len(self.questions):
            self._finish()
        else:
            self._load_question()

    def _load_question(self):
        self.answered = False
        self._time_left = self.TIMED_SECONDS
        for btn in self.ans_btns: btn.destroy()
        self.ans_btns.clear()

        q = self.questions[self.idx]
        self.mode_lbl.config(text=f"◈ {self.cfg['mode'].upper()}")
        self.player_lbl.config(text=f"│  {self.cfg['player']}")
        self.score_lbl.config(text=f"Q {self.idx+1}/{len(self.questions)}  │  SCORE: {self.score}")
        
        self.cat_lbl.config(text=f"  {q['category']}  ·  {q['difficulty'].upper()}")
        self.q_lbl.config(text=q["question"])

        # Progress bar
        self.update_idletasks()
        pw = self.prog_canvas.winfo_width()
        self.prog_canvas.delete("all")
        self.prog_canvas.create_rectangle(0, 0, int(pw * (self.idx/len(self.questions))), 6, fill=C["accent"], outline="")

        cols = 1 if self.cfg["q_type"] == "boolean" else 2
        for i, ans in enumerate(q["answers"]):
            btn = tk.Button(self.ans_frame, text=f"  {chr(65+i)}.  {ans}", font=(FONT_MONO, 10),
                            bg=C["bg3"], fg=C["fg"], relief="flat", anchor="w", pady=12, padx=10,
                            highlightthickness=1, highlightbackground=C["border"])
            btn.config(command=lambda b=btn, a=ans: self._answer(b, a))
            btn.grid(row=i // cols, column=i % cols, sticky="ew", padx=4, pady=4)
            self.ans_btns.append(btn)

        for c in range(cols): self.ans_frame.columnconfigure(c, weight=1)
        self.next_btn.config(state="disabled")

        if self.cfg["mode"] == "Timed":
            self.timer_bar.pack(fill="x")
            self.timer_lbl.pack(side="left")
            self._tick()

    def _finish(self):
        elapsed = int(time.time() - self.start_time)
        results = {
            "score": self.score,
            "streak": self.best_streak,
            "time": elapsed,
            "wrong": self.wrong_list,
            "total": len(self.questions)
        }
        self.master.show_results(results, self.cfg)
    def _quit_quiz(self):
        if messagebox.askyesno("Quit", "Abandon the quiz? Progress will be lost."):
            self.master.show_home()
# ─────────────────────────── RESULTS & LEADERBOARD ──────────────────
class ResultScreen(tk.Frame):
    def __init__(self, master, data, cfg):
        super().__init__(master, bg=C["bg"])
        self.data = data
        add_score({"name": cfg["player"], "score": data["score"], "time": data["time"], "date": str(datetime.date.today())})
        self._build()
    def _build(self):
        ctr = tk.Frame(self, bg=C["bg"])
        ctr.pack(expand=True)
        tk.Label(ctr, text="QUIZ COMPLETE", font=(FONT_MONO, 24, "bold"), bg=C["bg"], fg=C["accent"]).pack(pady=10)
        panel = panel_frame(ctr)
        panel.pack(ipadx=40, ipady=20)
        stats = [("FINAL SCORE", self.data['score']), ("BEST STREAK", self.data['streak']), ("TIME", f"{self.data['time']}s")]
        for lbl, val in stats:
            f = tk.Frame(panel, bg=C["panel"])
            f.pack(fill="x", pady=4)
            tk.Label(f, text=lbl, font=(FONT_MONO, 10), bg=C["panel"], fg=C["fg_dim"]).pack(side="left")
            tk.Label(f, text=str(val), font=(FONT_MONO, 12, "bold"), bg=C["panel"], fg=C["accent"]).pack(side="right")
        btn_f = tk.Frame(ctr, bg=C["bg"])
        btn_f.pack(pady=30)
        styled_button(btn_f, "REPLAY", self.master.show_setup, "primary").pack(side="left", padx=10)
        styled_button(btn_f, "MAIN MENU", self.master.show_home, "ghost").pack(side="left", padx=10)
class LeaderboardScreen(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=C["bg"])
        self._build()
    def _build(self):
        hdr = tk.Frame(self, bg=C["bg2"], height=60)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🏆 GLOBAL RANKINGS", font=(FONT_MONO, 14, "bold"), bg=C["bg2"], fg=C["accent"]).pack(side="left", padx=20, pady=15)
        styled_button(hdr, "CLOSE", self.master.show_home, "ghost", 10).pack(side="right", padx=20)

        container = tk.Frame(self, bg=C["bg"])
        container.pack(expand=True, fill="both", padx=50, pady=20)

        scores = load_leaderboard()
        if not scores:
            tk.Label(container, text="No scores yet. Be the first!", font=(FONT_MONO, 10), bg=C["bg"], fg=C["fg_faint"]).pack(pady=50)
        else:
            for i, entry in enumerate(scores):
                f = tk.Frame(container, bg=C["bg3"] if i%2==0 else C["bg"], pady=8)
                f.pack(fill="x")
                tk.Label(f, text=f"{i+1}.", font=(FONT_MONO, 10, "bold"), bg=f.cget("bg"), fg=C["accent"], width=4).pack(side="left")
                tk.Label(f, text=entry["name"], font=(FONT_MONO, 10), bg=f.cget("bg"), fg=C["fg"]).pack(side="left", padx=10)
                tk.Label(f, text=str(entry["score"]), font=(FONT_MONO, 10, "bold"), bg=f.cget("bg"), fg=C["white"]).pack(side="right", padx=20)

if __name__ == "__main__":
    app = QuizForge()
    app.mainloop()