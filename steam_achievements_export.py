import tkinter as tk
from tkinter import ttk, messagebox
import requests
import csv
import time
import os
import json
import threading
import re   # ★ 禁止文字除去に必要
from settings_page import SettingsPage

import sys, os


def resource_path(relative_path):
    """PyInstaller で exe 化した後でもリソースファイルにアクセスできるようにする"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# -----------------------------
# 設定
# -----------------------------
CONFIG_PATH = "config.json"

APP_TITLE = "Steam 実績エクスポーター"
DEFAULT_OUTPUT = os.path.join("C:\\", "steam_export", "steam_achievements_jp.csv")
USE_JP_TITLE = True

# カラー
BG_ROOT = "#232120"
BG_PANEL = "#32302F"
BG_ENTRY = "#32302F"
FG_MAIN = "#e5e7eb"
SEARCH_BG = "#3d3b3a"

# 進捗ゲージ用カラー（黒ベースのグレー系）
GAUGE_TRACK_COLOR = "#3a3a3a"   # ゲージ背景（トラック / 灰色）
GAUGE_BAR_COLOR   = "#ffffff"   # ゲージ本体（バー / 白）


# =========================================================
# ★★ ファイル名を完全安全化する関数
# =========================================================
def safe_filename(name: str) -> str:
    # Windows で使えない文字を全部 "_" に
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    # 末尾のピリオドと空白を削除
    name = name.rstrip(". ")
    # 非表示 / 制御文字を削除
    name = "".join(ch for ch in name if ch.isprintable())
    return name if name else "game"


# -----------------------------
# API
# -----------------------------
def get_owned_games(api_key, steam_id):
    if not api_key or not steam_id:
        raise ValueError("API Key と SteamID64 を設定タブで入力してください。")

    url = (
        "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
        f"?key={api_key}&steamid={steam_id}"
        "&include_appinfo=1&include_played_free_games=1"
    )
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", {}).get("games", [])


def get_schema_and_achievements(api_key, steam_id, appid):
    # 実績の取得状況
    stats_url = (
        "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/"
        f"?key={api_key}&steamid={steam_id}&appid={appid}"
    )
    stats_resp = requests.get(stats_url, timeout=15).json()
    if "playerstats" not in stats_resp or "achievements" not in stats_resp["playerstats"]:
        return None, None, None

    achievements_status = {
        a["apiname"]: a["achieved"]
        for a in stats_resp["playerstats"]["achievements"]
    }

    # 実績のマスタ（日本語名）
    schema_url = (
        "https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/"
        f"?key={api_key}&appid={appid}&l=japanese"
    )
    schema_resp = requests.get(schema_url, timeout=15).json()

    game = schema_resp.get("game", {})
    jp_game_name = game.get("gameName")
    achievements = game.get("availableGameStats", {}).get("achievements", [])

    return jp_game_name, achievements, achievements_status


# -----------------------------
# GUI：丸チェック
# -----------------------------
class RoundCheck(tk.Frame):
    def __init__(self, master, name_text, appid_text="", command=None):
        super().__init__(master, bg=BG_PANEL)

        self.command = command
        self.var = tk.BooleanVar(value=False)
        self.visible = True

        self.columnconfigure(1, weight=1)

        self.canvas = tk.Canvas(
            self,
            width=18,
            height=18,
            bg=BG_PANEL,
            highlightthickness=0,
            borderwidth=0,
        )
        self.canvas.grid(row=0, column=0, padx=(0, 6))

        self.label_name = tk.Label(
            self,
            text=name_text,
            anchor="w",
            bg=BG_PANEL,
            fg=FG_MAIN,
            font=("NotoSansJP", 10),
        )
        self.label_name.grid(row=0, column=1, sticky="we")

        self.label_appid = tk.Label(
            self,
            text=f"AppID: {appid_text}",
            anchor="e",
            bg=BG_PANEL,
            fg="#9ca3af",
            font=("NotoSansJP", 9),
        )
        self.label_appid.grid(row=0, column=2, padx=(8, 20))

        self.canvas.bind("<Button-1>", self.toggle)
        self.label_name.bind("<Button-1>", self.toggle)
        self.label_appid.bind("<Button-1>", self.toggle)

        self._draw()

    def _draw(self):
        self.canvas.delete("all")
        self.canvas.create_oval(2, 2, 16, 16, outline="#9ca3af", width=2)
        if self.var.get():
            self.canvas.create_oval(5, 5, 13, 13, fill="#f9fafb", outline="")

    def toggle(self, _):
        self.var.set(not self.var.get())
        self._draw()
        if self.command:
            self.command()

    def get(self):
        return self.var.get()

    def set(self, value: bool):
        self.var.set(value)
        self._draw()


# -----------------------------
# GUI：Pill ボタン
# -----------------------------
class PillButton(tk.Canvas):
    def __init__(
        self,
        master,
        text,
        command=None,
        width=120,
        height=30,
        bg="#3f3e3d",
        fg="#ffffff",
        hover="#4b4a49",
        active="#2f2e2d",
    ):

        super().__init__(
            master,
            width=width,
            height=height,
            bg=BG_PANEL,
            highlightthickness=0,
            bd=0,
        )

        self.text = text
        self.command = command
        self.bg_color = bg
        self.fg_color = fg
        self.hover_color = hover
        self.active_color = active
        self.current_color = bg
        self.radius = height // 2
        self.enabled = True

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>", lambda e: self._draw())
        self._draw()

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        if enabled:
            self.fg_color = "#ffffff"
            self.current_color = self.bg_color
        else:
            self.fg_color = "#9ca3af"
            self.current_color = "#2b2a29"
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()

        r = self.radius
        # 左の丸
        self.create_oval(0, 0, h, h, fill=self.current_color, outline=self.current_color)
        # 右の丸
        self.create_oval(w - h, 0, w, h, fill=self.current_color, outline=self.current_color)
        # 中央の長方形
        self.create_rectangle(
            r,
            0,
            w - r,
            h,
            fill=self.current_color,
            outline=self.current_color,
        )

        self.create_text(
            w // 2,
            h // 2,
            text=self.text,
            fill=self.fg_color,
            font=("NotoSansJP", 11, "bold"),
        )

    def _on_enter(self, _):
        if not self.enabled:
            return
        self.current_color = self.hover_color
        self._draw()

    def _on_leave(self, _):
        if not self.enabled:
            return
        self.current_color = self.bg_color
        self._draw()

    def _on_press(self, _):
        if not self.enabled:
            return
        self.current_color = self.active_color
        self._draw()

    def _on_release(self, _):
        if not self.enabled:
            return
        self.current_color = self.hover_color
        self._draw()
        if self.command:
            self.command()


# -----------------------------
# 丸端ゲージ（Canvas ベース）
# -----------------------------
class RoundedProgressBar(tk.Canvas):
    def __init__(
        self,
        master,
        variable: tk.DoubleVar,
        track_color=GAUGE_TRACK_COLOR,
        bar_color=GAUGE_BAR_COLOR,
        height=8,
        *args,
        **kwargs,
    ):
        super().__init__(
            master,
            height=height,
            bg=BG_PANEL,
            highlightthickness=0,
            bd=0,
            *args,
            **kwargs,
        )
        self.variable = variable
        self.track_color = track_color
        self.bar_color = bar_color

        # フェード用 after id
        self._fade_after = None

        # 値／サイズが変わったら再描画
        self.variable.trace_add("write", lambda *_: self._draw())
        self.bind("<Configure>", lambda e: self._draw())

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()

        if w <= 2 or h <= 2:
            return

        # トラック（背景）
        self._draw_capsule(0, 0, w, h, self.track_color)

        # 値に応じてバー
        try:
            value = float(self.variable.get())
        except Exception:
            value = 0.0

        value = max(0.0, min(100.0, value))
        if value <= 0:
            return

        fill_len = w * (value / 100.0)
        if fill_len <= 0:
            return

        self._draw_capsule(0, 0, fill_len, h, self.bar_color)

    def _draw_capsule(self, x0, y0, x1, y1, color):
        """左右が丸いカプセル状のバーを描画"""
        w = x1 - x0
        h = y1 - y0
        r = h / 2
        if w <= 0 or h <= 0:
            return

        if w <= h:
            # 幅が高さより小さいときは単純な丸
            self.create_oval(x0, y0, x0 + w, y0 + h, fill=color, outline=color)
            return

        # 左丸
        self.create_oval(
            x0,
            y0,
            x0 + h,
            y0 + h,
            fill=color,
            outline=color,
        )
        # 右丸
        self.create_oval(
            x1 - h,
            y0,
            x1,
            y0 + h,
            fill=color,
            outline=color,
        )
        # 中央の四角
        self.create_rectangle(
            x0 + r,
            y0,
            x1 - r,
            y0 + h,
            fill=color,
            outline=color,
        )

    def animate_to_zero(self, duration=300):
        """ゲージをふわっと減衰させながら 0 に戻すアニメーション"""
        # すでにフェード中なら完全停止
        if self._fade_after is not None:
            try:
                self.after_cancel(self._fade_after)
            except Exception:
                pass
            self._fade_after = None

        start_value = float(self.variable.get())
        if start_value <= 0:
            self.variable.set(0.0)
            self._draw()
            return

        steps = 20
        step_time = max(1, duration // steps)

        def step(i):
            t = i / steps
            eased = (1 - t) ** 2  # ふわっと落ちるイージング
            new_value = start_value * eased
            self.variable.set(new_value)
            self._draw()
            if i < steps:
                self._fade_after = self.after(step_time, lambda: step(i + 1))
            else:
                self._fade_after = None
                self.variable.set(0.0)
                self._draw()

        step(0)


# -----------------------------
# メイン GUI
# -----------------------------
class SteamAchievementsGUI:
    def __init__(self, root):
        self.root = root
        root.title(APP_TITLE)
        root.configure(bg=BG_ROOT)
        root.geometry("1100x720")

        # アイコンパス（exe 内にも対応）
        icon_path = resource_path("steam_achi_multi.ico")
        try:
            root.iconbitmap(icon_path)
        except Exception as e:
            print("icon load error:", e)

        root.option_add("*Font", "NotoSansJP 10")

        self.api_key = tk.StringVar()
        self.steam_id = tk.StringVar()
        self.output_path = tk.StringVar(value=DEFAULT_OUTPUT)

        self.games = []
        self.round_checks = []
        self.search_var = tk.StringVar()

        self.loading_label = None
        self.loading_text_var = tk.StringVar()
        self._loading_after_id = None
        self._loading = False
        self._loading_anim_step = 0

        # Export 状態
        self._exporting = False
        self._cancel_export = False

        # 進捗ゲージ用
        self.progress_var = tk.DoubleVar(value=0.0)
        self._progress_anim_after = None
        self._progress_current = 0.0

        self._setup_style()
        self._build_layout()
        self.load_config()

        root.after(400, self.on_fetch_games)

    # -------------------------
    # スタイル
    # -------------------------
    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Crystal.TNotebook",
            background=BG_ROOT,
            borderwidth=0,
            highlightthickness=0,
            padding=0,
            bordercolor=BG_ROOT,
        )
        style.configure(
            "Crystal.TNotebook.Tab",
            font=("NotoSansJP", 10, "bold"),
            padding=(18, 8),
            background=BG_PANEL,
            foreground="#e5e7eb",
            borderwidth=0,
        )
        style.map(
            "Crystal.TNotebook.Tab",
            background=[("selected", "#3b3a39"), ("active", BG_PANEL)],
            foreground=[("selected", "#ffffff"), ("active", "#f9fafb")],
        )

        # スクロールバー（太さは OS デフォルトのまま）
        style.configure(
            "Crystal.Vertical.TScrollbar",
            gripcount=0,
            background="#6b7280",
            troughcolor=BG_PANEL,
            bordercolor=BG_PANEL,
            arrowcolor=BG_PANEL,
            relief="flat",
        )
        style.map(
            "Crystal.Vertical.TScrollbar",
            background=[("!active", "#6b7280"), ("active", "#9ca3af")],
        )

    # -----------------------------
    # UI レイアウト
    # -----------------------------
    def _build_layout(self):
        outer = tk.Frame(
            self.root,
            bg=BG_ROOT,
            highlightthickness=0,
            bd=0,
            highlightbackground=BG_ROOT,
        )
        outer.pack(fill="both", expand=True, padx=12, pady=12)

        hud = tk.Frame(
            outer,
            bg=BG_PANEL,
            highlightthickness=0,
            bd=0,
            highlightbackground=BG_PANEL,
        )
        hud.pack(fill="both", expand=True, padx=4, pady=4)

        self.notebook = ttk.Notebook(hud, style="Crystal.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=0, pady=0)

        self.achievements_frame = tk.Frame(self.notebook, bg=BG_PANEL)
        self.settings_frame = tk.Frame(self.notebook, bg=BG_PANEL)

        self.notebook.add(self.achievements_frame, text="実績")
        self.notebook.add(self.settings_frame, text="設定")

        self._build_achievements_tab()

        self.settings_page = SettingsPage(
            self.settings_frame,
            api_key_var=self.api_key,
            steam_id_var=self.steam_id,
            output_path_var=self.output_path,
            save_config_callback=self.save_config,
        )
        self.settings_page.pack(fill="both", expand=True)

    # -----------------------------
    # 実績タブ
    # -----------------------------
    def _build_achievements_tab(self):
        f = self.achievements_frame

        top = tk.Frame(f, bg=BG_PANEL)
        top.pack(fill="x", padx=16, pady=(16, 8))

        # ボタン群
        self.export_button = PillButton(top, "CSVで出力", self.on_export_achievements)
        self.export_button.pack(side="left", padx=(0, 10))

        PillButton(top, "すべて選択", self.select_all_games).pack(
            side="left", padx=(0, 10)
        )
        PillButton(top, "選択解除", self.clear_all_games).pack(side="left")

        PillButton(top, "リスト更新", self.on_fetch_games).pack(side="right")

        center = tk.Frame(f, bg=BG_PANEL)
        center.pack(fill="both", expand=True, padx=16, pady=(4, 8))

        games_frame = tk.Frame(center, bg=BG_PANEL)
        games_frame.pack(side="left", fill="both", expand=True)

        header = tk.Frame(games_frame, bg=BG_PANEL)
        header.pack(fill="x", pady=(0, 10))

        search_wrap = tk.Frame(header, bg=BG_PANEL)
        search_wrap.pack(side="left")

        self.search_canvas = tk.Canvas(
            search_wrap,
            height=28,
            bg=BG_PANEL,
            highlightthickness=0,
            bd=0,
        )
        self.search_canvas.pack()

        def _resize_search_bar(_=None):
            pw = header.winfo_width()
            self.search_canvas.configure(width=int(pw * 0.4))

        header.bind("<Configure>", _resize_search_bar)
        search_wrap.bind("<Configure>", _resize_search_bar)

        self.search_entry = tk.Entry(
            self.search_canvas,
            textvariable=self.search_var,
            bg=SEARCH_BG,
            fg="#9ca3af",
            relief="flat",
            bd=0,
            insertbackground="#ffffff",
            font=("NotoSansJP", 10),
        )

        def redraw(_=None):
            self.search_canvas.delete("all")
            w = self.search_canvas.winfo_width()
            h = self.search_canvas.winfo_height()
            if w <= 1 or h <= 1:
                return
            r = 14

            self.search_canvas.create_oval(
                0, 0, h, h, fill=SEARCH_BG, outline=SEARCH_BG
            )
            self.search_canvas.create_oval(
                w - h, 0, w, h, fill=SEARCH_BG, outline=SEARCH_BG
            )
            self.search_canvas.create_rectangle(
                r, 0, w - r, h, fill=SEARCH_BG, outline=SEARCH_BG
            )

            lens_color = "#9ca3af"
            self.search_canvas.create_oval(
                6, 6, 18, 18, outline=lens_color, width=2
            )
            self.search_canvas.create_line(
                16, 16, 22, 22, fill=lens_color, width=2
            )

            self.search_canvas.create_window(
                (w // 2) + 10,
                h // 2,
                window=self.search_entry,
                width=w - 40,
                height=h - 8,
            )

        self.search_canvas.bind("<Configure>", redraw)

        canvas = tk.Canvas(
            games_frame,
            bg=BG_PANEL,
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            games_frame,
            orient="vertical",
            style="Crystal.Vertical.TScrollbar",
            command=canvas.yview,
        )
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)
        self.games_canvas = canvas

        self.games_inner = tk.Frame(canvas, bg=BG_PANEL)
        win = canvas.create_window(0, 0, window=self.games_inner, anchor="nw")

        def _cfg(_=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win, width=canvas.winfo_width())

        self.games_inner.bind("<Configure>", _cfg)
        canvas.bind("<Configure>", _cfg)
        canvas.bind_all(
            "<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"),
        )

        # --- 下部：ログ + 進捗 ---
        log_frame = tk.Frame(f, bg=BG_PANEL)
        log_frame.pack(fill="x", padx=16, pady=(0, 12))

        tk.Frame(log_frame, bg="#4b4b4b", height=1).pack(fill="x", pady=(8, 8))

        log_box = tk.Frame(log_frame, bg=BG_PANEL)
        log_box.pack(fill="x")

        self.log_text = tk.Text(
            log_box,
            height=4,
            bg=BG_ENTRY,
            fg="#e5e7eb",
            relief="flat",
            wrap="word",
            font=("NotoSansJP", 10),
        )
        self.log_text.pack(side="left", fill="both", expand=True)

        log_scroll = ttk.Scrollbar(
            log_box,
            orient="vertical",
            style="Crystal.Vertical.TScrollbar",
            command=self.log_text.yview,
        )
        log_scroll.pack(side="right", fill="y")

        # 進捗ゲージ + 中止ボタン（右側）
        progress_box = tk.Frame(log_frame, bg=BG_PANEL)
        progress_box.pack(fill="x", pady=(8, 0))

        tk.Label(
            progress_box,
            text="進捗",
            bg=BG_PANEL,
            fg=FG_MAIN,
            font=("NotoSansJP", 9),
        ).pack(side="left", padx=(0, 8))

        # ★ 丸端ゲージ（Canvas ベース）
        self.progress_bar = RoundedProgressBar(
            progress_box,
            variable=self.progress_var,
            track_color=GAUGE_TRACK_COLOR,
            bar_color=GAUGE_BAR_COLOR,
            height=8,
        )
        self.progress_bar.pack(
            side="left",
            padx=(0, 8),
            fill="none",
            expand=False,
        )

        # ゲージの幅を常に 70% に
        def _resize_progress_bar(_=None):
            total_w = progress_box.winfo_width()
            if total_w > 0:
                self.progress_bar.configure(width=int(total_w * 0.70))

        progress_box.bind("<Configure>", _resize_progress_bar)

        # 中止ボタン（ゲージ右）
        self.cancel_button = PillButton(
            progress_box,
            "中止",
            self.on_cancel_export,
            bg="#4b5563",
            width=80,
            height=24,
        )
        self.cancel_button.pack(side="left", padx=(8, 0))
        self.cancel_button.set_enabled(False)

        self._init_search_placeholder()
        self.search_var.trace_add("write", lambda *_: self.filter_games())

    # -----------------------------
    # 検索プレースホルダー
    # -----------------------------
    def _init_search_placeholder(self):
        """検索バーのプレースホルダー設定（ゲーム検索）"""
        self._search_placeholder = "ゲーム検索"

        if not self.search_var.get():
            self.search_var.set(self._search_placeholder)
            self.search_entry.configure(fg="#9ca3af")

        def focus_in(_):
            if self.search_var.get() == self._search_placeholder:
                self.search_var.set("")
                self.search_entry.configure(fg="#ffffff")

        def focus_out(_):
            if not self.search_var.get():
                self.search_var.set(self._search_placeholder)
                self.search_entry.configure(fg="#9ca3af")

        self.search_entry.bind("<FocusIn>", focus_in)
        self.search_entry.bind("<FocusOut>", focus_out)

    # -----------------------------
    # Log & filter
    # -----------------------------
    def log(self, msg):
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")

    def _log_from_thread(self, msg: str):
        """別スレッドから安全にログを追加"""
        self.root.after(0, lambda m=msg: self.log(m))

    def clear_games_list(self):
        for w in self.games_inner.winfo_children():
            w.destroy()
        self.round_checks.clear()

    def select_all_games(self):
        for appid, name, rc in self.round_checks:
            rc.set(True)

    def clear_all_games(self):
        for appid, name, rc in self.round_checks:
            rc.set(False)

    def filter_games(self):
        keyword = self.search_var.get().lower().strip()

        if keyword == "" or keyword == "ゲーム検索":
            keyword = None

        for appid, name, rc in self.round_checks:
            if keyword is None:
                if not rc.visible:
                    rc.pack(anchor="w", fill="x", pady=2)
                    rc.visible = True
                continue

            match = keyword in name.lower()

            if match and not rc.visible:
                rc.pack(anchor="w", fill="x", pady=2)
                rc.visible = True
            elif not match and rc.visible:
                rc.pack_forget()
                rc.visible = False

    # -----------------------------
    # Loading
    # -----------------------------
    def _show_loading(self):
        self.clear_games_list()

        self.loading_text_var.set("Now Loading")
        self.loading_label = tk.Label(
            self.games_inner,
            textvariable=self.loading_text_var,
            bg=BG_PANEL,
            fg="#9ca3af",
            font=("NotoSansJP", 11, "bold"),
        )
        self.loading_label.pack(expand=True, pady=40)

        self._loading_anim_step = 0
        self._animate_loading()

    def _animate_loading(self):
        dots = "." * (self._loading_anim_step % 4)
        self.loading_text_var.set("Now Loading" + dots)
        self._loading_anim_step += 1
        self._loading_after_id = self.root.after(400, self._animate_loading)

    def _hide_loading(self):
        if self._loading_after_id is not None:
            try:
                self.root.after_cancel(self._loading_after_id)
            except Exception:
                pass
        self._loading_after_id = None

        if self.loading_label is not None:
            self.loading_label.destroy()
            self.loading_label = None

    # -----------------------------
    # Fetch games
    # -----------------------------
    def on_fetch_games(self):
        if self._loading:
            return

        api_key = self.api_key.get().strip()
        steam_id = self.steam_id.get().strip()

        self.log_text.delete("1.0", "end")
        self.log("所有ゲームを取得中...")
        self._show_loading()
        self._loading = True

        def worker():
            try:
                games = get_owned_games(api_key, steam_id)
                games = sorted(games, key=lambda g: g.get("name", "").lower())
                error = None
            except Exception as e:
                games = []
                error = e

            self.root.after(0, lambda: self._on_fetch_games_done(games, error))

        threading.Thread(target=worker, daemon=True).start()

    def _on_fetch_games_done(self, games, error):
        self._hide_loading()
        self._loading = False

        if error is not None:
            messagebox.showerror("エラー", f"所有ゲームの取得に失敗しました:\n{error}")
            self.log(f"エラー: {error}")
            return

        self.games = games
        self.log(f"取得したゲーム数: {len(games)}")

        for g in games:
            appid = g.get("appid")
            name = g.get("name", f"AppID {appid}")

            rc = RoundCheck(self.games_inner, name_text=name, appid_text=str(appid))
            rc.pack(anchor="w", fill="x", pady=2)
            self.round_checks.append((appid, name, rc))

        self.filter_games()

    # -----------------------------
    # 進捗ゲージ制御
    # -----------------------------
    def _stop_progress_anim(self):
        """root.after を使った進捗アニメーションを完全停止"""
        if self._progress_anim_after is not None:
            try:
                self.root.after_cancel(self._progress_anim_after)
            except Exception:
                pass
            self._progress_anim_after = None

    def _reset_progress(self):
        # 上昇アニメーションを完全停止
        self._stop_progress_anim()

        self._progress_current = 0.0
        self.progress_var.set(0.0)

    def _start_progress_anim(self, target: float):
        # すでにアニメーション中なら完全停止
        self._stop_progress_anim()

        start = self._progress_current
        diff = target - start

        # ゆっくり「すーっ」と伸びるアニメーション
        duration = 900  # ms

        def ease_in_out_cubic(t):
            if t < 0.5:
                return 4 * t * t * t
            else:
                return 1 - ((-2 * t + 2) ** 3) / 2

        start_time = time.time()

        def step():
            elapsed = (time.time() - start_time) * 1000.0
            t = min(elapsed / duration, 1.0)
            eased = ease_in_out_cubic(t)

            new_val = start + diff * eased
            self._progress_current = new_val
            self.progress_var.set(new_val)

            if t >= 1.0:
                self._progress_anim_after = None
            else:
                self._progress_anim_after = self.root.after(16, step)

        step()

    def _set_progress(self, current: int, total: int):
        if total <= 0:
            target = 0.0
        else:
            target = (current / total) * 100.0
        self.root.after(0, lambda t=target: self._start_progress_anim(t))

    # -----------------------------
    # Export 関連
    # -----------------------------
    def on_cancel_export(self):
        if not self._exporting:
            return
        self._cancel_export = True
        self._log_from_thread("中止要求を受け付けました。しばらくお待ちください。")

    def on_export_achievements(self):
        # 連打防止
        if self._exporting:
            return

        api_key = self.api_key.get().strip()
        steam_id = self.steam_id.get().strip()

        if not api_key or not steam_id:
            messagebox.showwarning(
                "注意", "API Key と SteamID を設定タブで入力してください。"
            )
            return

        selected = [(appid, name) for appid, name, rc in self.round_checks if rc.get()]
        if not selected:
            messagebox.showinfo("情報", "書き出すゲームにチェックを入れてください。")
            return

        # 単品出力 → 完全安全なファイル名を使用
        if len(selected) == 1:
            raw_name = selected[0][1]
            name = safe_filename(raw_name)
            auto_name = f"{name}_achievements.csv"
        else:
            auto_name = "SteamGames_achievements.csv"

        base_dir = os.path.dirname(self.output_path.get())
        if not base_dir:
            base_dir = os.path.dirname(DEFAULT_OUTPUT)

        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)

        output_path = os.path.join(base_dir, auto_name)

        # 状態初期化
        self.log_text.delete("1.0", "end")
        self.log("実績取得を開始...")
        self._reset_progress()
        self._cancel_export = False
        self._exporting = True
        self.export_button.set_enabled(False)
        self.cancel_button.set_enabled(True)

        # 非同期で実績取得＆CSV書き出し（逐次書き込み）
        thread = threading.Thread(
            target=self._export_worker,
            args=(api_key, steam_id, selected, output_path),
            daemon=True,
        )
        thread.start()

    def _export_worker(self, api_key, steam_id, selected, output_path):
        total = len(selected)
        canceled = False
        had_rows = False

        # CSV を開いて、1 行ずつ書き込む
        try:
            f = open(output_path, "w", newline="", encoding="utf-8-sig")
        except Exception as e:
            self._log_from_thread(f"書き出しエラー: {e}")
            self.root.after(
                0,
                lambda: self._export_done(output_path, e, wrote=False, canceled=False),
            )
            return

        writer = csv.DictWriter(
            f,
            fieldnames=["ゲーム名", "実績名", "説明", "取得状況"],
        )
        writer.writeheader()

        try:
            for idx, (appid, base_name) in enumerate(selected, start=1):
                if self._cancel_export:
                    canceled = True
                    break

                self._log_from_thread(f"{base_name} (AppID: {appid}) 取得中...")
                try:
                    jp, achievements, status = get_schema_and_achievements(
                        api_key, steam_id, appid
                    )
                    if achievements is None or status is None:
                        self._log_from_thread("  ⚠ 情報なし")
                        self._set_progress(idx, total)
                        continue

                    game_name = jp or base_name

                    for a in achievements:
                        api = a.get("name")
                        display = a.get("displayName", "")
                        desc = a.get("description", "")
                        achieved = "✅" if status.get(api) == 1 else "❌"

                        writer.writerow(
                            {
                                "ゲーム名": game_name,
                                "実績名": display,
                                "説明": desc,
                                "取得状況": achieved,
                            }
                        )
                        had_rows = True

                except Exception as e:
                    self._log_from_thread(f"  エラー: {e}")

                # 進捗更新（すーっとアニメーション）
                self._set_progress(idx, total)

        finally:
            f.close()

        # 結果ゼロ
        if not had_rows:
            self.root.after(
                0,
                lambda: self._export_done(
                    output_path, None, wrote=False, canceled=canceled
                ),
            )
            return

        # 正常完了 or 中止（部分的に出力）
        self.root.after(
            0,
            lambda: self._export_done(
                output_path, None, wrote=True, canceled=canceled
            ),
        )

    def _export_done(self, output_path, error, wrote: bool, canceled: bool):
        """Export 完了時（メインスレッド側で実行）"""
        self._exporting = False
        self.export_button.set_enabled(True)
        self.cancel_button.set_enabled(False)

        # ★ 解決ポイント：
        #  1) 上昇アニメーションを完全停止
        #  2) その時点の値からゲージをふわっと 0 に戻す
        self._stop_progress_anim()
        self._progress_current = float(self.progress_var.get())
        self.progress_bar.animate_to_zero()

        if error is not None:
            messagebox.showerror("エラー", f"書き出し失敗:\n{error}")
            return

        if canceled:
            if wrote:
                messagebox.showinfo(
                    "中止",
                    f"処理を中止しましたが、一部は書き出されています。\n→ {output_path}",
                )
                self.log(f"中止（部分的に出力）→ {output_path}")
            else:
                messagebox.showinfo("中止", "処理を中止しました。CSV は出力されていません。")
                self.log("中止されました。")
            return

        if not wrote:
            messagebox.showinfo("情報", "実績が取得できませんでした。")
            return

        self.log(f"完了 → {output_path}")
        messagebox.showinfo("完了", "CSV 書き出しが完了しました。")

    # -----------------------------
    # Config Save / Load
    # -----------------------------
    def save_config(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "api_key": self.api_key.get(),
                        "steam_id": self.steam_id.get(),
                        "output_path": self.output_path.get(),
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception:
            pass

    def load_config(self):
        if not os.path.exists(CONFIG_PATH):
            return
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                self.api_key.set(cfg.get("api_key", ""))
                self.steam_id.set(cfg.get("steam_id", ""))
                self.output_path.set(cfg.get("output_path", DEFAULT_OUTPUT))
        except Exception:
            pass


# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SteamAchievementsGUI(root)
    root.mainloop()
