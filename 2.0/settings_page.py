import tkinter as tk
from tkinter import ttk, filedialog

# --- カラー定義（メイン側と一致） ---
BG_PANEL  = "#32302F"   # 設定タブの背景
FG_MAIN   = "#e5e7eb"   # 通常文字色
SEARCH_BG = "#3d3b3a"   # Entry 背景（丸エントリ）


class SettingsPage(tk.Frame):
    """設定タブを SteamAchievementsGUI から分離したクラス"""

    def __init__(
        self,
        master,
        api_key_var: tk.StringVar,
        steam_id_var: tk.StringVar,
        output_path_var: tk.StringVar,
        save_config_callback=None,
        *args,
        **kwargs
    ):
        super().__init__(master, bg=BG_PANEL, *args, **kwargs)

        self.api_key = api_key_var
        self.steam_id = steam_id_var
        self.output_path = output_path_var
        self.save_config_callback = save_config_callback

        self._build_layout()
        self._setup_trace()

    # -------------------------------------------------------------------------
    #  角丸 Entry を生成するヘルパー
    # -------------------------------------------------------------------------
    def _rounded_entry(self, parent, textvariable, width_mode="narrow"):
        """
        width_mode="narrow": 横幅60%くらい
        width_mode="full"  : 横いっぱい
        """
        container = tk.Frame(parent, bg=BG_PANEL)

        if width_mode == "full":
            container.pack(side="left", fill="x", expand=True, padx=(8, 0))
        else:
            container.pack(side="left", padx=(8, 0))

        canvas = tk.Canvas(
            container,
            height=30,
            bg=BG_PANEL,
            highlightthickness=0,
            borderwidth=0,
        )
        if width_mode == "full":
            canvas.pack(fill="x")
        else:
            canvas.pack()

        entry = tk.Entry(
            canvas,
            textvariable=textvariable,
            bg=SEARCH_BG,
            fg="#f9fafb",
            insertbackground="#f9fafb",
            relief="flat",
            borderwidth=0,
            width=40 if width_mode != "full" else None,
        )

        def _redraw(_event=None):
            canvas.delete("all")
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            if w <= 0 or h <= 0:
                return

            # pill形背景
            r = 14
            x0, y0, x1, y1 = 1, 1, w - 1, h - 1

            canvas.create_oval(x0, y0, x0 + 2 * r, y1,
                               fill=SEARCH_BG, outline=SEARCH_BG)
            canvas.create_oval(x1 - 2 * r, y0, x1, y1,
                               fill=SEARCH_BG, outline=SEARCH_BG)
            canvas.create_rectangle(x0 + r, y0, x1 - r, y1,
                                    fill=SEARCH_BG, outline=SEARCH_BG)

            # Entry 配置
            canvas.create_window(
                (w // 2, h // 2),
                window=entry,
                width=w - 16,
                height=h - 10,
            )

        canvas.bind("<Configure>", _redraw)
        return entry

    # -------------------------------------------------------------------------
    #  UI 構築
    # -------------------------------------------------------------------------
    def _build_layout(self):
        # タイトル
        title = tk.Label(
            self,
            text="Steam API 設定",
            bg=BG_PANEL,
            fg="#ffffff",
            font=("NotoSansJP", 14, "bold"),
        )
        title.pack(anchor="w", padx=20, pady=(20, 8))

        desc = tk.Label(
            self,
            text="Steam Web API のキーと SteamID64 を入力し、CSV の保存先（フォルダ＋ファイル名）を指定してください。",
            bg=BG_PANEL,
            fg="#d1d5db",
            wraplength=760,
            justify="left",
        )
        desc.pack(anchor="w", padx=20, pady=(0, 16))

        # メインフォーム
        form = tk.Frame(self, bg=BG_PANEL)
        form.pack(fill="x", padx=20)

        # -------------------------
        #  API Key
        # -------------------------
        row1 = tk.Frame(form, bg=BG_PANEL)
        row1.pack(fill="x", pady=8)

        tk.Label(
            row1,
            text="API Key：",
            bg=BG_PANEL,
            fg=FG_MAIN,
            width=14,
            anchor="e",
        ).pack(side="left")

        self._rounded_entry(row1, self.api_key, width_mode="narrow")

        # -------------------------
        #  SteamID64
        # -------------------------
        row2 = tk.Frame(form, bg=BG_PANEL)
        row2.pack(fill="x", pady=8)

        tk.Label(
            row2,
            text="SteamID64：",
            bg=BG_PANEL,
            fg=FG_MAIN,
            width=14,
            anchor="e",
        ).pack(side="left")

        self._rounded_entry(row2, self.steam_id, width_mode="narrow")

        # -------------------------
        #  出力先 CSV（ラベル＋横長エントリ）
        # -------------------------
        row3 = tk.Frame(form, bg=BG_PANEL)
        row3.pack(fill="x", pady=8)

        tk.Label(
            row3,
            text="出力先CSV：",
            bg=BG_PANEL,
            fg=FG_MAIN,
            width=14,
            anchor="e",
        ).pack(side="left")

        self._rounded_entry(row3, self.output_path, width_mode="full")

        # "参照..." ボタン（行を分けて右端）
        button_row = tk.Frame(form, bg=BG_PANEL)
        button_row.pack(fill="x", pady=(4, 0))

        ttk.Button(
            button_row,
            text="参照...",
            command=self._browse_output_path,
        ).pack(side="right")

        # 下部メモ
        note = tk.Label(
            self,
            text="※ 設定は自動保存されます。",
            bg=BG_PANEL,
            fg="#9ca3af",
            justify="left",
        )
        note.pack(anchor="w", padx=20, pady=(18, 0))

    # -------------------------------------------------------------------------
    #  trace による自動保存
    # -------------------------------------------------------------------------
    def _setup_trace(self):
        def _on_change(*_):
            if self.save_config_callback:
                self.save_config_callback()

        self.api_key.trace_add("write", _on_change)
        self.steam_id.trace_add("write", _on_change)
        self.output_path.trace_add("write", _on_change)

    # -------------------------------------------------------------------------
    #  ファイル選択ダイアログ（参照ボタン）
    # -------------------------------------------------------------------------
    def _browse_output_path(self):
        current = self.output_path.get().strip()
        import os

        initial_dir = os.path.dirname(current) if current else "C:\\"
        initial_file = os.path.basename(current) if current else "steam_achievements_jp.csv"

        path = filedialog.asksaveasfilename(
            title="CSV 出力先を選択",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialdir=initial_dir,
            initialfile=initial_file,
        )

        if path:
            self.output_path.set(path)
            if self.save_config_callback:
                self.save_config_callback()
