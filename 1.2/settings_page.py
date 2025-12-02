import tkinter as tk
from tkinter import ttk, filedialog

# ここはメインと同じ色をそのままコピー
BG_PANEL = "#32302F"
SEARCH_BG = "#3d3b3a"
FG_MAIN = "#e5e7eb"


def make_rounded_entry(parent, textvariable):
    """検索窓と同じ、丸いエントリーを描画するヘルパー"""
    container = tk.Frame(parent, bg=BG_PANEL)
    container.pack(side="left", fill="x", expand=True, padx=(8, 0))

    canvas = tk.Canvas(
        container,
        height=30,
        bg=BG_PANEL,
        highlightthickness=0,
        borderwidth=0
    )
    canvas.pack(fill="x")

    entry = tk.Entry(
        canvas,
        textvariable=textvariable,
        bg=SEARCH_BG,
        fg="#f9fafb",
        insertbackground="#f9fafb",
        relief="flat",
        borderwidth=0,
    )

    def _redraw(_event=None, c=canvas, e=entry):
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w <= 0 or h <= 0:
            return
        r = 14
        x0, y0, x1, y1 = 1, 1, w - 1, h - 1

        # pill 形（左丸＋右丸＋中央四角）
        c.create_oval(
            x0, y0, x0 + 2 * r, y1,
            fill=SEARCH_BG, outline=SEARCH_BG
        )
        c.create_oval(
            x1 - 2 * r, y0, x1, y1,
            fill=SEARCH_BG, outline=SEARCH_BG
        )
        c.create_rectangle(
            x0 + r, y0, x1 - r, y1,
            fill=SEARCH_BG, outline=SEARCH_BG
        )

        # Entry 本体
        c.create_window(
            (w // 2, h // 2),
            window=e,
            width=w - 16,
            height=h - 10
        )

    canvas.bind("<Configure>", _redraw)
    return entry


class SettingsPage(tk.Frame):
    """設定タブ専用の Frame"""

    def __init__(self, master, api_key_var, steam_id_var, output_path_var, save_config_callback):
        super().__init__(master, bg=BG_PANEL)
        self.api_key = api_key_var
        self.steam_id = steam_id_var
        self.output_path = output_path_var
        self.save_config = save_config_callback
        self._build_ui()

    def _build_ui(self):
        # 上部説明
        title = tk.Label(
            self,
            text="Steam API 設定",
            bg=BG_PANEL,
            fg="#ffffff",
            font=("NotoSansJP", 14, "bold")
        )
        title.pack(anchor="w", padx=20, pady=(20, 8))

        desc = tk.Label(
            self,
            text="Steam Web API のキーと SteamID64 を入力し、CSV の保存先（ファイル名は自動）を指定してください。",
            bg=BG_PANEL,
            fg="#d1d5db",
            wraplength=760,
            justify="left"
        )
        desc.pack(anchor="w", padx=20, pady=(0, 16))

        form = tk.Frame(self, bg=BG_PANEL)
        form.pack(fill="x", padx=20)

        # --- API Key 行 ---
        row1 = tk.Frame(form, bg=BG_PANEL)
        row1.pack(fill="x", pady=8)

        tk.Label(
            row1,
            text="API Key：",
            bg=BG_PANEL,
            fg=FG_MAIN,
            width=14,
            anchor="e"
        ).pack(side="left")

        make_rounded_entry(row1, self.api_key)

        # --- SteamID64 行 ---
        row2 = tk.Frame(form, bg=BG_PANEL)
        row2.pack(fill="x", pady=8)

        tk.Label(
            row2,
            text="SteamID64：",
            bg=BG_PANEL,
            fg=FG_MAIN,
            width=14,
            anchor="e"
        ).pack(side="left")

        make_rounded_entry(row2, self.steam_id)

        # --- 出力先 CSV 行（右に 参照ボタン） ---
        row3 = tk.Frame(form, bg=BG_PANEL)
        row3.pack(fill="x", pady=8)

        tk.Label(
            row3,
            text="出力先 CSV：",
            bg=BG_PANEL,
            fg=FG_MAIN,
            width=14,
            anchor="e"
        ).pack(side="left")

        make_rounded_entry(row3, self.output_path)

        ttk.Button(
            row3,
            text="参照...",
            style="Crystal.TButton",
            command=self._browse_output_path
        ).pack(side="left", padx=(8, 0))

        # 下部メモ
        note = tk.Label(
            self,
            text="※ 設定は自動保存されます。",
            bg=BG_PANEL,
            fg="#9ca3af",
            wraplength=760,
            justify="left"
        )
        note.pack(anchor="w", padx=20, pady=(18, 0))

        # 設定は自動保存
        self.api_key.trace_add("write", lambda *a: self.save_config())
        self.steam_id.trace_add("write", lambda *a: self.save_config())
        self.output_path.trace_add("write", lambda *a: self.save_config())

    def _browse_output_path(self):
        initial_dir = os.path.dirname(self.output_path.get()) if self.output_path.get() else "C:\\"
        path = filedialog.asksaveasfilename(
            title="CSV 出力先を選択",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialdir=initial_dir,
            initialfile=os.path.basename(self.output_path.get()) if self.output_path.get() else ""
        )
        if path:
            self.output_path.set(path)
