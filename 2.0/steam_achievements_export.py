import tkinter as tk
from tkinter import ttk, messagebox
import requests
import csv
import time
import os
import json

from settings_page import SettingsPage  # ← 追加：設定タブを別ファイルから読み込み

# -----------------------------
#  設定ファイル
# -----------------------------
CONFIG_PATH = "config.json"

# -----------------------------
#  基本設定
# -----------------------------
APP_TITLE = "Steam 実績エクスポーター - ChatGPT Style"
DEFAULT_OUTPUT = os.path.join("C:\\", "steam_export", "steam_achievements_jp.csv")
USE_JP_TITLE = True

# カラー
BG_ROOT = "#232120"   # 一番外側
BG_PANEL = "#32302F"  # タブ内・リストなど
BG_ENTRY = "#32302F"  # Entry など
FG_MAIN = "#e5e7eb"   # 文字基本色
SEARCH_BG = "#3d3b3a"  # 検索窓の背景


# -----------------------------
#  API 関連処理
# -----------------------------
def get_owned_games(api_key, steam_id):
    """所有ゲーム一覧を取得"""
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
    games = data.get("response", {}).get("games", [])
    return games


def get_schema_and_achievements(api_key, steam_id, appid):
    """スキーマと実績情報を取得（日本語）"""

    # 実績達成状況
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

    # 日本語スキーマ
    schema_url = (
        "https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/"
        f"?key={api_key}&appid={appid}&l=japanese"
    )
    schema_resp = requests.get(schema_url, timeout=15).json()
    game = schema_resp.get("game", {})
    jp_game_name = game.get("gameName")  # 日本語タイトル（あれば）
    achievements = game.get("availableGameStats", {}).get("achievements", [])

    return jp_game_name, achievements, achievements_status


# -----------------------------
#  GUI 部品：丸チェック（カスタム）
# -----------------------------
class RoundCheck(tk.Frame):
    """丸いチェック UI ＋「ゲーム名」「AppID」表示"""

    def __init__(self, master, name_text, appid_text="", command=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.command = command
        self.var = tk.BooleanVar(value=False)

        self.configure(bg=BG_PANEL)

        # ✔ ゲーム名の列を一番広く使う
        self.columnconfigure(0, weight=0)              # チェック丸
        self.columnconfigure(1, weight=1)              # ゲーム名（広く）
        self.columnconfigure(2, weight=0, minsize=80)  # AppID（右端・最小幅だけ）

        # 丸チェック用キャンバス
        self.canvas = tk.Canvas(
            self,
            width=18,
            height=18,
            highlightthickness=0,
            bg=BG_PANEL,
            borderwidth=0,
        )
        self.canvas.grid(row=0, column=0, padx=(0, 6), pady=1, sticky="w")

        # ゲーム名（左・できるだけ広く）
        self.label_name = tk.Label(
            self,
            text=name_text,
            anchor="w",
            justify="left",
            bg=BG_PANEL,
            fg=FG_MAIN,
            font=("NotoSansJP", 10),
            wraplength=0,   # 折り返ししない → フレームいっぱい表示
        )
        self.label_name.grid(row=0, column=1, sticky="we")

        # AppID（右側）
        self.label_appid = tk.Label(
            self,
            text=f"AppID: {appid_text}" if appid_text else "",
            anchor="e",
            justify="right",
            bg=BG_PANEL,
            fg="#9ca3af",
            font=("NotoSansJP", 9),
        )
        self.label_appid.grid(row=0, column=2, sticky="e", padx=(8, 0))

        # クリックでトグル
        self.canvas.bind("<Button-1>", self.toggle)
        self.label_name.bind("<Button-1>", self.toggle)
        self.label_appid.bind("<Button-1>", self.toggle)

        self.draw()

    def draw(self):
        self.canvas.delete("all")
        # 外側の円
        self.canvas.create_oval(
            2, 2, 16, 16,
            outline="#9ca3af",
            width=2
        )
        if self.var.get():
            # 中の光る部分
            self.canvas.create_oval(
                5, 5, 13, 13,
                fill="#f9fafb",
                outline=""
            )

    def toggle(self, _event=None):
        self.var.set(not self.var.get())
        self.draw()
        if self.command:
            self.command()

    def get(self):
        return self.var.get()

    def set(self, value: bool):
        self.var.set(bool(value))
        self.draw()


# -----------------------------
#  GUI 部品：iOS風トグルスイッチ
# -----------------------------
class IOSToggle(tk.Frame):
    """iOS風トグルスイッチ（アニメ付き）"""

    def __init__(self, master, variable=None, command=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.configure(bg=BG_PANEL)

        self.var = variable or tk.BooleanVar(value=False)
        self.command = command

        self.canvas = tk.Canvas(
            self,
            width=44,
            height=24,
            bg=BG_PANEL,
            highlightthickness=0,
            borderwidth=0,
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_click)

        # アニメーション用
        self.knob_pos = 1.0 if self.var.get() else 0.0  # 0.0=左, 1.0=右
        self._target = self.knob_pos
        self._animating = False

        # 変化を監視してアニメ開始
        self.var.trace_add("write", lambda *a: self._animate_to_var())
        self.draw()

    def draw(self):
        self.canvas.delete("all")

        # トラック色はノブ位置で判定
        on = self.knob_pos >= 0.5
        track_color = "#4ade80" if on else "#4b5563"
        knob_color = "#ffffff"

        # pill形のトラック
        self.canvas.create_oval(2, 2, 22, 22, fill=track_color, outline=track_color)
        self.canvas.create_oval(22, 2, 42, 22, fill=track_color, outline=track_color)
        self.canvas.create_rectangle(12, 2, 32, 22, fill=track_color, outline=track_color)

        # ノブ位置
        x0 = 2 + self.knob_pos * 20
        x1 = x0 + 20
        self.canvas.create_oval(x0, 2, x1, 22, fill=knob_color, outline=knob_color)

    def _animate_to_var(self):
        self._target = 1.0 if self.var.get() else 0.0
        if not self._animating:
            self._animating = True
            self._step_animation()

    def _step_animation(self):
        diff = self._target - self.knob_pos
        if abs(diff) < 0.01:
            self.knob_pos = self._target
            self._animating = False
            self.draw()
            return

        # イージングっぽく少しずつ近づける
        self.knob_pos += diff * 0.25
        self.draw()
        self.after(16, self._step_animation)  # 約60fps

    def _on_click(self, _event=None):
        # ON/OFF 変更 → アニメーションは trace で動く
        self.var.set(not self.var.get())
        if self.command:
            self.command()


# -----------------------------
#  メイン GUI クラス
# -----------------------------
class SteamAchievementsGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        # ChatGPT っぽい黒ベース
        self.root.configure(bg=BG_ROOT)
        self.root.geometry("900x600")

        # アプリのアイコン
        try:
            self.root.iconbitmap("steam_achi.ico")
        except Exception:
            pass

        # デフォルトフォント
        self.root.option_add("*Font", "NotoSansJP 10")

        # 状態
        self.api_key = tk.StringVar()
        self.steam_id = tk.StringVar()
        # 設定画面では「保存先ファイル」だが、実際にはフォルダ部分だけ利用する
        self.output_path = tk.StringVar(value=DEFAULT_OUTPUT)
        # 自動取得の ON/OFF
        self.auto_fetch = tk.BooleanVar(value=True)

        self.games = []          # API から取ってきた raw ゲームリスト
        self.round_checks = []   # (appid, name, RoundCheck)
        self.search_var = tk.StringVar()

        self._setup_style()
        self._build_layout()
        self.load_config()

        # 起動時、自動取得が ON なら所持ゲーム取得
        self.root.after(400, self.maybe_auto_fetch)

    # -------------------------
    #  スタイル設定
    # -------------------------
    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Notebook（タブ）
        style.configure(
            "Crystal.TNotebook",
            background=BG_ROOT,
            borderwidth=0,
        )
        style.configure(
            "Crystal.TNotebook.Tab",
            font=("NotoSansJP", 10, "bold"),
            padding=(18, 8),
            background=BG_PANEL,
            foreground="#e5e7eb",
            borderwidth=0
        )
        style.map(
            "Crystal.TNotebook.Tab",
            background=[
                ("selected", "#3b3a39"),
                ("active", BG_PANEL),
            ],
            foreground=[
                ("selected", "#ffffff"),
                ("active", "#f9fafb"),
            ]
        )

        # ボタン
        style.configure(
            "Crystal.TButton",
            font=("NotoSansJP", 10),
            padding=(20, 6),
            background=BG_PANEL,
            foreground="#f3f4f6",
            borderwidth=0,
            relief="flat"
        )
        style.map(
            "Crystal.TButton",
            background=[
                ("active", "#3b3a39"),
                ("pressed", BG_PANEL),
            ],
            foreground=[
                ("active", "#ffffff"),
                ("pressed", "#ffffff"),
            ]
        )

        # スクロールバー（黒系）: ゲーム一覧・ログ共通
        style.configure(
            "Crystal.Vertical.TScrollbar",
            gripcount=0,
            background=BG_PANEL,
            darkcolor=BG_PANEL,
            lightcolor=BG_PANEL,
            troughcolor=BG_ROOT,
            bordercolor=BG_ROOT,
            arrowcolor=BG_ROOT,   # 矢印色も背景と同化
            relief="flat"
        )
        style.configure(
            "Crystal.Horizontal.TScrollbar",
            gripcount=0,
            background=BG_PANEL,
            darkcolor=BG_PANEL,
            lightcolor=BG_PANEL,
            troughcolor=BG_ROOT,
            bordercolor=BG_ROOT,
            arrowcolor=BG_ROOT,
            relief="flat"
        )

        # △矢印を消すために layout を上書き（thumb のみ）
        style.layout(
            "Crystal.Vertical.TScrollbar",
            [
                ("Vertical.Scrollbar.trough", {
                    "children": [
                        ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})
                    ],
                    "sticky": "ns"
                })
            ]
        )
        style.layout(
            "Crystal.Horizontal.TScrollbar",
            [
                ("Horizontal.Scrollbar.trough", {
                    "children": [
                        ("Horizontal.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})
                    ],
                    "sticky": "we"
                })
            ]
        )

    # -------------------------
    #  レイアウト構築
    # -------------------------
    def _build_layout(self):
        # 外側フレーム
        outer = tk.Frame(self.root, bg=BG_ROOT)
        outer.pack(fill="both", expand=True, padx=12, pady=12)

        # 中央パネル
        hud = tk.Frame(
            outer,
            bg=BG_PANEL,
            bd=0,
            highlightthickness=0,
        )
        hud.pack(fill="both", expand=True, padx=4, pady=4)

        # Notebook（タブ）
        self.notebook = ttk.Notebook(hud, style="Crystal.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=4, pady=4)

        # タブフレーム
        self.achievements_frame = tk.Frame(self.notebook, bg=BG_PANEL)
        self.settings_frame = tk.Frame(self.notebook, bg=BG_PANEL)

        # タブ追加（順番：実績 → 設定）
        self.notebook.add(self.achievements_frame, text="実績")
        self.notebook.add(self.settings_frame, text="設定")

        # 実績タブは従来どおりこのクラス内で構築
        self._build_achievements_tab()

        # 設定タブは別クラスに委譲
        self.settings_page = SettingsPage(
            master=self.settings_frame,
            api_key_var=self.api_key,
            steam_id_var=self.steam_id,
            output_path_var=self.output_path,
            save_config_callback=self.save_config,
        )
        self.settings_page.pack(fill="both", expand=True)

    # -------------------------
    #  実績タブ
    # -------------------------
    def _build_achievements_tab(self):
        f = self.achievements_frame

        # 上部ボタン行
        top_bar = tk.Frame(f, bg=BG_PANEL)
        top_bar.pack(fill="x", padx=16, pady=(16, 8))

        # 所持ゲーム取得ボタンは廃止 → 書き出しボタンのみ
        ttk.Button(
            top_bar,
            text="選択したゲームの実績を書き出し",
            style="Crystal.TButton",
            command=self.on_export_achievements
        ).pack(side="left")

        # 自動取得トグル（書き出しボタンの右）
        auto_frame = tk.Frame(top_bar, bg=BG_PANEL)
        auto_frame.pack(side="left", padx=(20, 0))

        tk.Label(
            auto_frame,
            text="自動取得",
            bg=BG_PANEL,
            fg=FG_MAIN
        ).pack(side="left", padx=(0, 8))

        IOSToggle(
            auto_frame,
            variable=self.auto_fetch,
            command=self.on_auto_fetch_toggle
        ).pack(side="left")

        # 中央：ゲーム一覧
        center = tk.Frame(f, bg=BG_PANEL)
        center.pack(fill="both", expand=True, padx=16, pady=(4, 8))

        games_frame = tk.Frame(center, bg=BG_PANEL)
        games_frame.pack(side="left", fill="both", expand=True)

        # ヘッダー行：左「ゲーム一覧」＋ 右「検索窓」
        header_frame = tk.Frame(games_frame, bg=BG_PANEL)
        header_frame.pack(fill="x", pady=(0, 4))

        games_label = tk.Label(
            header_frame,
            text="ゲーム一覧",
            bg=BG_PANEL,
            fg=FG_MAIN,
            anchor="w"
        )
        games_label.pack(side="left")

        # 🔍 検索バー（プレースホルダー「ゲーム検索」）
        search_container = tk.Frame(header_frame, bg=BG_PANEL)
        search_container.pack(side="left", padx=(8, 0), fill="x", expand=True)

        # 丸みのある検索ボックスを Canvas で描画
        self.search_canvas = tk.Canvas(
            search_container,
            height=28,
            bg=BG_PANEL,
            highlightthickness=0,
            borderwidth=0
        )
        self.search_canvas.pack(fill="x")

        self.search_entry = tk.Entry(
            self.search_canvas,
            textvariable=self.search_var,
            bg=SEARCH_BG,
            fg="#9ca3af",            # 初期はプレースホルダー色
            insertbackground="#f9fafb",
            relief="flat",
            borderwidth=0,
        )

        # Canvas 上に丸い背景＋ Entry を配置
        def _redraw_search(_event=None):
            self.search_canvas.delete("all")
            w = self.search_canvas.winfo_width()
            h = self.search_canvas.winfo_height()
            if w <= 0 or h <= 0:
                return
            r = 14  # 角の丸み
            x0, y0, x1, y1 = 1, 1, w - 1, h - 1

            # pill 形（左丸＋右丸＋中央四角）
            self.search_canvas.create_oval(
                x0, y0, x0 + 2 * r, y1,
                fill=SEARCH_BG, outline=SEARCH_BG
            )
            self.search_canvas.create_oval(
                x1 - 2 * r, y0, x1, y1,
                fill=SEARCH_BG, outline=SEARCH_BG
            )
            self.search_canvas.create_rectangle(
                x0 + r, y0, x1 - r, y1,
                fill=SEARCH_BG, outline=SEARCH_BG
            )

            # Entry 本体
            self.search_canvas.create_window(
                (w // 2, h // 2),
                window=self.search_entry,
                width=w - 16,
                height=h - 8
            )

        self.search_canvas.bind("<Configure>", _redraw_search)

        # スクロール領域
        games_canvas = tk.Canvas(
            games_frame,
            bg=BG_PANEL,
            highlightthickness=0,
            borderwidth=0
        )
        games_canvas.pack(side="left", fill="both", expand=True)

        y_scroll = ttk.Scrollbar(
            games_frame,
            orient="vertical",
            style="Crystal.Vertical.TScrollbar",
            command=games_canvas.yview
        )
        y_scroll.pack(side="right", fill="y")
        games_canvas.configure(yscrollcommand=y_scroll.set)

        self.games_inner = tk.Frame(games_canvas, bg=BG_PANEL)
        inner_window = games_canvas.create_window(
            (0, 0),
            window=self.games_inner,
            anchor="nw"
        )

        # Canvas / inner のサイズに合わせてスクロール領域を更新
        def _on_inner_configure(_event=None):
            games_canvas.configure(scrollregion=games_canvas.bbox("all"))
            # Frame の幅を Canvas に合わせる（これでゲーム名エリアが最大化される）
            canvas_width = games_canvas.winfo_width()
            if canvas_width > 0:
                games_canvas.itemconfig(inner_window, width=canvas_width)

        self.games_inner.bind("<Configure>", _on_inner_configure)
        games_canvas.bind("<Configure>", _on_inner_configure)

        # マウスホイール
        def _on_mousewheel(event):
            games_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        games_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # 下部：ログ（3行）
        log_frame = tk.Frame(f, bg=BG_PANEL)
        log_frame.pack(fill="x", padx=16, pady=(0, 12))

        tk.Label(
            log_frame,
            text="ログ",
            bg=BG_PANEL,
            fg=FG_MAIN,
            anchor="w"
        ).pack(anchor="w")

        log_container = tk.Frame(log_frame, bg=BG_PANEL)
        log_container.pack(fill="x")

        self.log_text = tk.Text(
            log_container,
            height=3,  # 3行
            bg=BG_ENTRY,
            fg="#e5e7eb",
            insertbackground="#f9fafb",
            relief="flat",
            wrap="word"
        )
        self.log_text.pack(side="left", fill="both", expand=True)

        log_scroll = ttk.Scrollbar(
            log_container,
            orient="vertical",
            style="Crystal.Vertical.TScrollbar",  # ゲーム一覧と同じスタイル
            command=self.log_text.yview
        )
        log_scroll.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=log_scroll.set)

        # 🔹 入力のたびにフィルタ更新
        self.search_var.trace_add("write", lambda *a: self.filter_games())

        # 🔹 検索プレースホルダー初期化
        self._init_search_placeholder()

    # -------------------------
    #  検索プレースホルダー
    # -------------------------
    def _init_search_placeholder(self):
        self._search_placeholder = "ゲーム検索"

        # 初期表示
        if not self.search_var.get():
            self.search_var.set(self._search_placeholder)
            self.search_entry.configure(fg="#9ca3af")

        def on_focus_in(_event):
            if self.search_var.get() == self._search_placeholder:
                self.search_var.set("")
                self.search_entry.configure(fg="#f9fafb")

        def on_focus_out(_event):
            if not self.search_var.get():
                self.search_var.set(self._search_placeholder)
                self.search_entry.configure(fg="#9ca3af")

        self.search_entry.bind("<FocusIn>", on_focus_in)
        self.search_entry.bind("<FocusOut>", on_focus_out)

    # -------------------------
    #  イベントハンドラ系
    # -------------------------
    def log(self, msg):
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.root.update_idletasks()

    def clear_games_list(self):
        for w in self.games_inner.winfo_children():
            w.destroy()
        self.round_checks.clear()

    def maybe_auto_fetch(self):
        """起動時に自動取得ONなら実行"""
        if self.auto_fetch.get():
            self.on_fetch_games()

    def on_auto_fetch_toggle(self):
        """トグル操作時"""
        self.save_config()
        if self.auto_fetch.get():
            # アニメーションがある程度進んでから取得を始める
            self.root.after(350, self.on_fetch_games)

    def filter_games(self):
        """ゲーム名フィルタ"""
        keyword = self.search_var.get()
        if keyword == getattr(self, "_search_placeholder", None):
            keyword = ""
        keyword = keyword.lower()

        for appid, name, rc in self.round_checks:
            if keyword in name.lower():
                rc.pack(anchor="w", fill="x", pady=2)
            else:
                rc.pack_forget()

    def on_fetch_games(self):
        self.clear_games_list()
        self.log_text.delete("1.0", "end")

        api_key = self.api_key.get().strip()
        steam_id = self.steam_id.get().strip()

        try:
            self.log("所有ゲームを取得中...")
            games = get_owned_games(api_key, steam_id)

            # アルファベット順（ゲーム名）でソート
            games = sorted(games, key=lambda g: g.get("name", "").lower())

            self.games = games
            self.log(f"取得したゲーム数: {len(games)}")

            for g in games:
                appid = g.get("appid")
                name = g.get("name", f"AppID {appid}")

                rc = RoundCheck(
                    self.games_inner,
                    name_text=name,
                    appid_text=str(appid)
                )
                rc.pack(anchor="w", fill="x", pady=2)
                self.round_checks.append((appid, name, rc))

            # 取得後、現在のキーワードでフィルタを適用
            self.filter_games()

        except Exception as e:
            messagebox.showerror("エラー", f"所有ゲームの取得に失敗しました:\n{e}")
            self.log(f"エラー: {e}")

    def on_export_achievements(self):
        api_key = self.api_key.get().strip()
        steam_id = self.steam_id.get().strip()

        if not api_key or not steam_id:
            messagebox.showwarning("注意", "API Key と SteamID を設定タブで入力してください。")
            return

        # 選択ゲームを抽出
        selected = []
        for appid, name, rc in self.round_checks:
            if rc.get():
                selected.append((appid, name))

        if not selected:
            messagebox.showinfo("情報", "書き出すゲームにチェックを入れてください。")
            return

        # ファイル名自動決定
        if len(selected) == 1:
            single_name = selected[0][1].replace("/", "_").replace("\\", "_")
            auto_name = f"{single_name}_achievements.csv"
        else:
            auto_name = "SteamGames_achievements.csv"

        # 設定タブの output_path からフォルダだけ利用
        base_dir = os.path.dirname(self.output_path.get())
        if not base_dir:
            base_dir = os.path.dirname(DEFAULT_OUTPUT)
        if not os.path.isdir(base_dir):
            os.makedirs(base_dir, exist_ok=True)

        output_path = os.path.join(base_dir, auto_name)

        rows = []

        self.log_text.delete("1.0", "end")
        self.log("実績の取得と書き出しを開始します...")

        for appid, base_name in selected:
            self.log(f"ゲーム {base_name} (AppID: {appid}) の実績取得中...")
            self.root.update_idletasks()
            try:
                jp_title, achievements, status = get_schema_and_achievements(
                    api_key, steam_id, appid
                )
                if achievements is None or status is None:
                    self.log("  ⚠ 実績情報が取得できませんでした。")
                    continue

                # 日本語タイトル優先
                game_name = jp_title or base_name

                for a in achievements:
                    api_name = a.get("name")
                    display_name = a.get("displayName", "")
                    description = a.get("description", "")
                    achieved = "✅" if status.get(api_name) == 1 else "❌"

                    rows.append({
                        "ゲーム名": game_name,
                        "実績名": display_name,
                        "説明": description,
                        "取得状況": achieved
                    })

                time.sleep(0.3)  # API 負荷軽減

            except Exception as e:
                self.log(f"  エラー: {e}")

        if not rows:
            messagebox.showinfo("情報", "有効な実績情報が取得できませんでした。")
            self.log("有効な結果がありませんでした。")
            return

        # CSV 出力
        try:
            with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["ゲーム名", "実績名", "説明", "取得状況"]
                )
                writer.writeheader()
                writer.writerows(rows)

            self.log(f"完了: {output_path} に書き出しました。")
            messagebox.showinfo("完了", f"CSV 出力が完了しました。\n\n{output_path}")

        except Exception as e:
            messagebox.showerror("エラー", f"CSV 出力に失敗しました:\n{e}")
            self.log(f"CSV 出力エラー: {e}")

    # -------------------------
    #  設定保存／読込
    # -------------------------
    def save_config(self):
        config = {
            "api_key": self.api_key.get(),
            "steam_id": self.steam_id.get(),
            "output_path": self.output_path.get(),
            "auto_fetch": self.auto_fetch.get(),
        }
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            # 保存失敗しても致命的ではないので黙っておく
            pass

    def load_config(self):
        if not os.path.exists(CONFIG_PATH):
            return
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
            self.api_key.set(config.get("api_key", ""))
            self.steam_id.set(config.get("steam_id", ""))
            self.output_path.set(config.get("output_path", DEFAULT_OUTPUT))
            self.auto_fetch.set(config.get("auto_fetch", True))
        except Exception:
            pass


# -----------------------------
#  エントリポイント
# -----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SteamAchievementsGUI(root)
    root.mainloop()
