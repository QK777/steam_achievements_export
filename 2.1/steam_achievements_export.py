import tkinter as tk
from tkinter import ttk, messagebox
import requests
import csv
import time
import os
import json
import threading

from settings_page import SettingsPage

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
BG_ROOT = "#232120"
BG_PANEL = "#32302F"
BG_ENTRY = "#32302F"
FG_MAIN = "#e5e7eb"
SEARCH_BG = "#3d3b3a"


# -----------------------------
#  API 関連処理
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
#  GUI 部品：丸チェック
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
            borderwidth=0
        )
        self.canvas.grid(row=0, column=0, padx=(0, 6))

        self.label_name = tk.Label(
            self,
            text=name_text,
            anchor="w",
            bg=BG_PANEL,
            fg=FG_MAIN,
            font=("NotoSansJP", 10)
        )
        self.label_name.grid(row=0, column=1, sticky="we")

        self.label_appid = tk.Label(
            self,
            text=f"AppID: {appid_text}",
            anchor="e",
            bg=BG_PANEL,
            fg="#9ca3af",
            font=("NotoSansJP", 9)
        )
        self.label_appid.grid(row=0, column=2, padx=(8, 0))

        self.canvas.bind("<Button-1>", self.toggle)
        self.label_name.bind("<Button-1>", self.toggle)
        self.label_appid.bind("<Button-1>", self.toggle)

        self.draw()

    def draw(self):
        self.canvas.delete("all")
        self.canvas.create_oval(2, 2, 16, 16, outline="#9ca3af", width=2)
        if self.var.get():
            self.canvas.create_oval(5, 5, 13, 13, fill="#f9fafb", outline="")

    def toggle(self, _):
        self.var.set(not self.var.get())
        self.draw()
        if self.command:
            self.command()

    def get(self):
        return self.var.get()

    def set(self, value: bool):
        self.var.set(value)
        self.draw()


# -----------------------------
#  GUI 部品：pill ボタン
# -----------------------------
class PillButton(tk.Canvas):
    def __init__(self, master, text, command=None,
                 width=120, height=30,
                 bg="#3f3e3d", fg="#ffffff",
                 hover="#4b4a49", active="#2f2e2d"):
        super().__init__(
            master,
            width=width,
            height=height,
            bg=BG_PANEL,
            highlightthickness=0,
            bd=0
        )

        self.text = text
        self.command = command

        self.bg_color = bg
        self.fg_color = fg
        self.hover_color = hover
        self.active_color = active
        self.current_color = bg
        self.radius = height // 2

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>", lambda e: self._draw())

        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1 or h <= 1:
            try:
                w = int(self["width"])
                h = int(self["height"])
            except Exception:
                w, h = 120, 30

        r = self.radius
        self.create_oval(0, 0, h, h, fill=self.current_color, outline=self.current_color)
        self.create_oval(w - h, 0, w, h, fill=self.current_color, outline=self.current_color)
        self.create_rectangle(r, 0, w - r, h, fill=self.current_color, outline=self.current_color)
        self.create_text(w // 2, h // 2, text=self.text, fill=self.fg_color, font=("NotoSansJP", 11, "bold"))

    def _on_enter(self, _):
        self.current_color = self.hover_color
        self._draw()

    def _on_leave(self, _):
        self.current_color = self.bg_color
        self._draw()

    def _on_press(self, _):
        self.current_color = self.active_color
        self._draw()

    def _on_release(self, _):
        self.current_color = self.hover_color
        self._draw()
        if self.command:
            self.command()


# -----------------------------
#  メイン GUI
# -----------------------------
class SteamAchievementsGUI:
    def __init__(self, root):
        self.root = root
        root.title(APP_TITLE)
        root.configure(bg=BG_ROOT)
        root.geometry("900x600")

        try:
            root.iconbitmap("steam_achi.ico")
        except Exception:
            pass

        root.option_add("*Font", "NotoSansJP 10")

        self.api_key = tk.StringVar()
        self.steam_id = tk.StringVar()
        self.output_path = tk.StringVar(value=DEFAULT_OUTPUT)

        self.games = []
        self.round_checks = []
        self.search_var = tk.StringVar()

        # ローディング関連
        self.loading_label = None
        self.loading_text_var = tk.StringVar()
        self._loading_after_id = None
        self._loading = False
        self._loading_anim_step = 0

        self._setup_style()
        self._build_layout()
        self.load_config()

        # 起動直後に常に自動取得
        root.after(400, self.on_fetch_games)

    # -------------------------
    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("Crystal.TNotebook", background=BG_ROOT, borderwidth=0)
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
            background=[("selected", "#3b3a39"), ("active", BG_PANEL)],
            foreground=[("selected", "#ffffff"), ("active", "#f9fafb")]
        )

        style.configure(
            "Crystal.Vertical.TScrollbar",
            gripcount=0,
            background=BG_PANEL,
            troughcolor=BG_ROOT,
            relief="flat",
            arrowcolor=BG_ROOT
        )
        style.layout(
            "Crystal.Vertical.TScrollbar",
            [(
                "Vertical.Scrollbar.trough",
                {
                    "children": [
                        ("Vertical.Scrollbar.thumb",
                         {"expand": "1", "sticky": "nswe"})
                    ],
                    "sticky": "ns"
                }
            )]
        )

    # -------------------------
    def _build_layout(self):
        outer = tk.Frame(self.root, bg=BG_ROOT)
        outer.pack(fill="both", expand=True, padx=12, pady=12)

        hud = tk.Frame(outer, bg=BG_PANEL)
        hud.pack(fill="both", expand=True, padx=4, pady=4)

        self.notebook = ttk.Notebook(hud, style="Crystal.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=4, pady=4)

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

    # -------------------------
    #  実績タブ
    # -------------------------
    def _build_achievements_tab(self):
        f = self.achievements_frame

        # 上部ボタン
        top = tk.Frame(f, bg=BG_PANEL)
        top.pack(fill="x", padx=16, pady=(16, 8))

        # Export
        PillButton(
            top,
            text="Export",
            command=self.on_export_achievements,
            width=120,
            height=30
        ).pack(side="left", padx=(0, 10))

        # Select All
        PillButton(
            top,
            text="Select All",
            command=self.select_all_games,
            width=120,
            height=30
        ).pack(side="left", padx=(0, 10))

        # Clear
        PillButton(
            top,
            text="Clear",
            command=self.clear_all_games,
            width=120,
            height=30
        ).pack(side="left")

        # -------------------------
        # ゲーム一覧 + 検索
        # -------------------------
        center = tk.Frame(f, bg=BG_PANEL)
        center.pack(fill="both", expand=True, padx=40, pady=(4, 8))

        games_frame = tk.Frame(center, bg=BG_PANEL)
        games_frame.pack(side="left", fill="both", expand=True, pady=(6,0))

        header = tk.Frame(games_frame, bg=BG_PANEL)
        header.pack(fill="x")
        tk.Label(
            header,
            text="ゲーム一覧",
            bg=BG_PANEL,
            fg=FG_MAIN
        ).pack(side="left")

        # 🔍 検索ウィンドウ
        search_wrap = tk.Frame(header, bg=BG_PANEL)
        search_wrap.pack(side="right", anchor="e", padx=(8,0), pady=(0,12))

        self.search_canvas = tk.Canvas(
            search_wrap,
            height=28,
            bg=BG_PANEL,
            highlightthickness=0,
            bd=0
        )
        self.search_canvas.pack(anchor="w")
        
        def _resize_search_bar(_=None):
            pw = header.winfo_width()
            self.search_canvas.configure(width=int(pw * 0.4))  # ←40% など自由
        header.bind("<Configure>", _resize_search_bar)

        search_wrap.bind("<Configure>", _resize_search_bar)

        self.search_entry = tk.Entry(
            self.search_canvas,
            textvariable=self.search_var,
            bg=SEARCH_BG,
            fg="#9ca3af",
            relief="flat",
            bd=0,
            insertbackground="#ffffff"
        )

        def redraw(_=None):
            self.search_canvas.delete("all")
            w = self.search_canvas.winfo_width()
            h = self.search_canvas.winfo_height()
            if w <= 1 or h <= 1:
                return
            r = 14
            self.search_canvas.create_oval(0, 0, h, h, fill=SEARCH_BG, outline=SEARCH_BG)
            self.search_canvas.create_oval(w - h, 0, w, h, fill=SEARCH_BG, outline=SEARCH_BG)
            self.search_canvas.create_rectangle(r, 0, w - r, h, fill=SEARCH_BG, outline=SEARCH_BG)

             # 虫眼鏡アイコンを描く
            lens_color = "#9ca3af"
            # 円
            self.search_canvas.create_oval(6, 6, 18, 18, outline=lens_color, width=2)
            # 持ち手
            self.search_canvas.create_line(16, 16, 22, 22, fill=lens_color, width=2)

            self.search_canvas.create_window(
                (w // 2) + 10,
                h // 2,
                window=self.search_entry,
                width=w - 40,
                height=h - 8
            )

        self.search_canvas.bind("<Configure>", redraw)

        # Scroll
        canvas = tk.Canvas(games_frame, bg=BG_PANEL, highlightthickness=0, bd=0)
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            games_frame,
            orient="vertical",
            style="Crystal.Vertical.TScrollbar",
            command=canvas.yview
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

        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        # ログ
        log_frame = tk.Frame(f, bg=BG_PANEL)
        log_frame.pack(fill="x", padx=16, pady=(0, 12))

        tk.Label(
            log_frame,
            text="ログ",
            bg=BG_PANEL,
            fg=FG_MAIN
        ).pack(anchor="w")

        log_box = tk.Frame(log_frame, bg=BG_PANEL)
        log_box.pack(fill="x")

        self.log_text = tk.Text(
            log_box,
            height=3,
            bg=BG_ENTRY,
            fg="#e5e7eb",
            relief="flat",
            wrap="word"
        )
        self.log_text.pack(side="left", fill="both", expand=True)

        log_scroll = ttk.Scrollbar(
            log_box,
            orient="vertical",
            style="Crystal.Vertical.TScrollbar",
            command=self.log_text.yview
        )
        log_scroll.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=log_scroll.set)

        self._init_search_placeholder()

        # 検索フィルタ
        self.search_var.trace_add("write", lambda *_: self.filter_games())

    # -------------------------
    def _init_search_placeholder(self):
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

    # -------------------------
    def log(self, msg):
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")

    # -------------------------
    def clear_games_list(self):
        for w in self.games_inner.winfo_children():
            w.destroy()
        self.round_checks.clear()

    # -------------------------
    def select_all_games(self):
        for appid, name, rc in self.round_checks:
            rc.set(True)

    def clear_all_games(self):
        for appid, name, rc in self.round_checks:
            rc.set(False)

    # -------------------------
    def filter_games(self):
        keyword = self.search_var.get().lower()
        if keyword == self._search_placeholder.lower():
            keyword = ""

        for appid, name, rc in self.round_checks:
            match = keyword in name.lower()

            if match and not rc.visible:
                rc.pack(anchor="w", fill="x", pady=2)
                rc.visible = True

            elif not match and rc.visible:
                rc.pack_forget()
                rc.visible = False

    # -------------------------
    def _show_loading(self):
        self.clear_games_list()

        self.loading_text_var.set("Now Loading")
        self.loading_label = tk.Label(
            self.games_inner,
            textvariable=self.loading_text_var,
            bg=BG_PANEL,
            fg="#9ca3af",
            font=("NotoSansJP", 11, "bold")
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

    # -------------------------
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

    # -------------------------
    def on_export_achievements(self):
        api_key = self.api_key.get().strip()
        steam_id = self.steam_id.get().strip()

        if not api_key or not steam_id:
            messagebox.showwarning("注意", "API Key と SteamID を設定タブで入力してください。")
            return

        selected = [(appid, name) for appid, name, rc in self.round_checks if rc.get()]
        if not selected:
            messagebox.showinfo("情報", "書き出すゲームにチェックを入れてください。")
            return

        if len(selected) == 1:
            name = selected[0][1].replace("/", "_").replace("\\", "_")
            auto_name = f"{name}_achievements.csv"
        else:
            auto_name = "SteamGames_achievements.csv"

        base_dir = os.path.dirname(self.output_path.get())
        if not base_dir:
            base_dir = os.path.dirname(DEFAULT_OUTPUT)

        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)

        output_path = os.path.join(base_dir, auto_name)

        rows = []
        self.log_text.delete("1.0", "end")
        self.log("実績取得を開始...")

        for appid, base_name in selected:
            self.log(f"{base_name} (AppID: {appid}) 取得中...")
            try:
                jp, achievements, status = get_schema_and_achievements(api_key, steam_id, appid)
                if achievements is None or status is None:
                    self.log("  ⚠ 情報なし")
                    continue

                game_name = jp or base_name

                for a in achievements:
                    api = a.get("name")
                    display = a.get("displayName", "")
                    desc = a.get("description", "")
                    achieved = "✅" if status.get(api) == 1 else "❌"

                    rows.append({
                        "ゲーム名": game_name,
                        "実績名": display,
                        "説明": desc,
                        "取得状況": achieved
                    })

                time.sleep(0.3)

            except Exception as e:
                self.log(f"  エラー: {e}")

        if not rows:
            messagebox.showinfo("情報", "実績が取得できませんでした。")
            return

        try:
            with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["ゲーム名", "実績名", "説明", "取得状況"]
                )
                writer.writeheader()
                writer.writerows(rows)

            self.log(f"完了 → {output_path}")
            messagebox.showinfo("完了", f"CSV 書き出し完了:\n{output_path}")

        except Exception as e:
            messagebox.showerror("エラー", f"書き出し失敗:\n{e}")
            self.log(f"書き出しエラー: {e}")

    # -------------------------
    def save_config(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({
                    "api_key": self.api_key.get(),
                    "steam_id": self.steam_id.get(),
                    "output_path": self.output_path.get(),
                }, f, indent=2, ensure_ascii=False)
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
#  エントリポイント
# -----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SteamAchievementsGUI(root)
    root.mainloop()
