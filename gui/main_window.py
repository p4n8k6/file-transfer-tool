import os
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD

from engine.transfer_engine import FileTransferEngine

# ----------------------------------------------------
#  メインGUI（TkinterDnD版）
# ----------------------------------------------------
class FileTransferUI(TkinterDnD.Tk):
    """
    ドラッグ&ドロップ対応のファイル転送ツールにおけるGUIを管理するクラス。

    コピー元・コピー先の指定、転送モードの選択、
    処理実行およびログ表示を担当する。
    
    """
    def __init__(self):
        """
        初期化処理
        """
        super().__init__()
        self.title("非対称バックアップ")
        self.geometry("260x450")
        self.dst_path_str = ""

        self.initUI()

    def initUI(self):
        """
        画面配置の初期化
        """
        main_frame = ttk.Frame(self, padding=8)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ① 対象アイテム（リスト枠）
        lbl_src = ttk.Label(main_frame, text="① 対象アイテム:", font=("", 9, "bold"))
        lbl_src.pack(anchor=tk.W)

        src_frame = ttk.Frame(main_frame)
        src_frame.pack(fill=tk.X, pady=(2, 2))

        # リストとスクロールバー用フレーム
        src_list_frame = ttk.Frame(src_frame)
        src_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # リスト本体と縦スクロールバーの領域
        src_body = ttk.Frame(src_list_frame)
        src_body.pack(fill=tk.BOTH, expand=True)

        self.src_list = tk.Listbox(
            src_body,
            height=3,
            selectmode=tk.EXTENDED,
            bg="#fafafa",
            relief="solid",
            bd=1,
            xscrollcommand=lambda *args: src_hscroll.set(*args)
        )
        self.src_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 縦スクロールバー
        src_vscroll = ttk.Scrollbar(
            src_body,
            orient=tk.VERTICAL,
            command=self.src_list.yview
        )
        src_vscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 横スクロールバー
        src_hscroll = ttk.Scrollbar(
            src_list_frame,
            orient=tk.HORIZONTAL,
            command=self.src_list.xview
        )
        src_hscroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.src_list.config(yscrollcommand=src_vscroll.set)

        # ドラッグ＆ドロップ設定
        self.src_list.drop_target_register(DND_FILES)
        self.src_list.dnd_bind('<<Drop>>', self.drop_on_src_list)

        # ファイル・フォルダ追加ボタン
        src_button_frame = ttk.Frame(main_frame)
        src_button_frame.pack(fill=tk.X, pady=(2, 4))

        btn_src_file = ttk.Button(
            src_button_frame,
            text="ファイルを追加",
            command=self.select_source_file
        )
        btn_src_file.pack(fill=tk.X, pady=(0, 2))

        btn_src_dir = ttk.Button(
            src_button_frame,
            text="フォルダを追加",
            command=self.select_source_directory
        )
        btn_src_dir.pack(fill=tk.X)

        # クリアボタン
        btn_clear = ttk.Button(main_frame, text="リストをクリア", command=self.clear_list)
        btn_clear.pack(fill=tk.X, pady=(0, 6))

        # ② コピー先（ドロップ枠）
        lbl_dst = ttk.Label(main_frame, text="② コピー先:", font=("", 9, "bold"))
        lbl_dst.pack(anchor=tk.W)

        dst_frame = ttk.Frame(main_frame)
        dst_frame.pack(fill=tk.X, pady=(2, 6))
        
        # 参照ボタン（先に幅を確保）
        btn_browse = ttk.Button(
            dst_frame, text="参照...", width=6,
            command=self.select_destination
        )
        btn_browse.pack(side=tk.RIGHT)

        # Entryとスクロールバー用フレーム
        dst_input_frame = ttk.Frame(dst_frame)
        dst_input_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        
        self.dst_box = tk.Entry(
            dst_input_frame,
            bg="#fafafa",
            readonlybackground="#fafafa",
            relief="solid",
            bd=1,
            font=("", 9)
        )

        self.dst_box.insert(0, "【コピー先フォルダ】ここにドロップ")
        self.dst_box.config(state="readonly")
        self.dst_box.pack(fill=tk.X, expand=True)
        
        self.dst_scroll = ttk.Scrollbar(
            dst_input_frame,
            orient=tk.HORIZONTAL,
            command=self.dst_box.xview
        )
        self.dst_scroll.pack(fill=tk.X)
        
        self.dst_box.config(xscrollcommand=self.dst_scroll.set)
        
        # ドラッグ＆ドロップ設定
        self.dst_box.drop_target_register(DND_FILES)
        self.dst_box.dnd_bind('<<Drop>>', self.drop_on_dst_box)

        # モード選択ラジオボタン
        self.mode_var = tk.StringVar(value="newer")
        mode_frame = ttk.Frame(main_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 6))

        radio_newer = ttk.Radiobutton(mode_frame, text="差分（最新日付）", value="newer", variable=self.mode_var)
        radio_move = ttk.Radiobutton(mode_frame, text="移動（上書き）", value="move", variable=self.mode_var)
        radio_newer.pack(side=tk.LEFT, padx=(0, 10))
        radio_move.pack(side=tk.LEFT)

        # 実行ボタン
        self.btn_start = tk.Button(
            main_frame, text="処理開始", bg="#2196F3", fg="white", 
            font=("", 10, "bold"), command=self.start_process, relief="flat"
        )
        self.btn_start.pack(fill=tk.X, pady=(0, 6))

        # ログエリア
        self.log_area = scrolledtext.ScrolledText(main_frame, height=5, font=("", 8))
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def add_source_paths(self, paths):
        """
        ディレクトリやファイルを対象アイテムリスト(self.src_list)に追加する
        args:
            paths: ディレクトリかファイルのパスのリスト
        """
        for path in paths:
            self.src_list.insert(tk.END, path)

    def parse_drop_paths(self, event_data):
        """
        ドラッグ＆ドロップイベントから受け取ったパス文字列を解析する。

        Args:
            event_data (str): event.dataから取得したドロップ対象のパス文字列。

        Returns:
            list[str]: 絶対パスに変換したファイル・ディレクトリのパス一覧。
        """
        import re
        paths = re.findall(r'\{(?:\\[\}]|[^}])+\}|[^\s{}]+', event_data)
        cleaned = [p.strip('{}') for p in paths]
        return [os.path.abspath(p) for p in cleaned if p]

    def select_source_file(self):
        """コピー元のファイル選択ダイアログを表示する。
        """
        path = filedialog.askopenfilename(
            title="コピー元ファイルを選択",
            initialdir=os.path.expanduser("~")
        )

        if path:
            self.add_source_paths([path])


    def select_source_directory(self):
        """コピー元のフォルダ選択ダイアログを表示する。
        """
        path = filedialog.askdirectory(
            title="コピー元フォルダを選択",
            initialdir=os.path.expanduser("~")
        )

        if path:
            self.add_source_paths([path])

    def drop_on_src_list(self, event):
        """
        コピー元リストへのドラッグ&ドロップイベント処理

        Args:
            event : ドラッグ&ドロップイベント
        """
        paths = self.parse_drop_paths(event.data)
        self.add_source_paths(paths)

    def drop_on_dst_box(self, event):
        """
        コピー先欄へのドラッグ＆ドロップイベント
        ドロップされたパスを解析し、ファイルの場合は
        親ディレクトリをコピー先として設定する。

        Args:
            event : ドラッグ&ドロップイベント
        """
        paths = self.parse_drop_paths(event.data)
        if paths:
            path = paths[0]
            if os.path.isfile(path):
                path = os.path.dirname(path)
            if os.path.isdir(path):
                self.dst_path_str = path
                self.dst_box.config(state="normal")
                self.dst_box.delete(0, tk.END)
                self.dst_box.insert(0, f"コピー先: {path}")
                self.dst_box.config(state="readonly", readonlybackground="#e8f5e9", fg="#2e7d32")

    def select_destination(self):
        """
        コピー先ディレクトリ選択ダイアログを表示する。
        選択されたディレクトリのパスを保持し、
        コピー先欄の表示を更新する。
        """        
        path = filedialog.askdirectory(
            title="コピー先フォルダを選択",
            initialdir=os.path.expanduser("~")
        )

        if path:
            self.dst_path_str = path
            self.dst_box.config(state="normal")
            self.dst_box.delete(0, tk.END)
            self.dst_box.insert(0, f"コピー先: {path}")
            self.dst_box.config(
                state="readonly",
                readonlybackground="#e8f5e9",
                fg="#2e7d32"
            )

    def clear_list(self):
        """
        対象アイテムリスト(self.src_list)の中身の削除
        """
        self.src_list.delete(0, tk.END)

    def append_log(self, text):
        """
        コピー・移動中のログのテキスト追加

        Args:
            text (str): ログのテキスト
        """
        self.log_area.insert(tk.END, text + "\n")
        self.log_area.see(tk.END)

    def start_process(self):
        """
        移動・コピーを行う関数
        実行ボタン押下時に開始される
        """
        src_paths = list(self.src_list.get(0, tk.END))
        dst_dir = self.dst_path_str

        if not src_paths:
            self.append_log("エラー: コピー対象が選択されていません。")
            return
        if not dst_dir or not os.path.exists(dst_dir):
            self.append_log("エラー: 有効なコピー先フォルダを指定してください。")
            return

        self.btn_start.config(state=tk.DISABLED)
        self.log_area.delete("1.0", tk.END)

        engine = FileTransferEngine(
            src_paths, dst_dir, self.mode_var.get(),
            log_callback=lambda msg: self.after(0, self.append_log, msg),
            finish_callback=lambda: self.after(0, self.on_finished)
        )
        engine.start()

    def on_finished(self):
        """
        コピー・移動終了後の処理
        """
        self.btn_start.config(state=tk.NORMAL)
        if self.mode_var.get() == 'move':
            self.clear_list()
