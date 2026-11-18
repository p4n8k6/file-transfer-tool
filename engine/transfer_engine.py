import os
import shutil
import threading

# ----------------------------------------------------
# バックグラウンド処理（スレッド）
# ----------------------------------------------------
class FileTransferEngine:
    """
    ファイル・ディレクトリのコピーおよび移動処理を実行するクラス。

    GUIから受け取った設定に基づき、バックグラウンドスレッドで
    ファイル転送処理を実行する。
    """
    def __init__(self, src_paths, dst_dir, mode, log_callback, finish_callback):
        """
        転送対象、転送先、処理モード、ログ・完了コールバックを設定する。

        Args:
            src_paths : コピー対象アイテムリスト
            dst_dir (str): コピー先
            mode (str): ラジオボタンで指定されたコピー・移動モード
            log_callback : ログ記録のコールバック関数
            finish_callback : 完了時のコールバック関数
        """
        self.src_paths = src_paths
        self.dst_dir = dst_dir
        self.mode = mode
        self.log = log_callback
        self.finish = finish_callback

    def start(self):
        """バックグラウンドスレッドで転送処理を開始する。"""
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        """転送対象を順次確認し、ファイルまたはディレクトリの転送処理を実行する。"""
        self.log("=== 処理を開始します ===")
        
        for src in self.src_paths:
            if not os.path.exists(src):
                self.log(f"スキップ（存在しません）: {src}")
                continue

            if os.path.isfile(src):
                self.process_file(src, self.dst_dir)
            elif os.path.isdir(src):
                folder_name = os.path.basename(src.rstrip('/\\'))
                target_folder = os.path.join(self.dst_dir, folder_name)
                self.process_directory(src, target_folder)

        self.log("=== 処理が完了しました！ ===")
        self.finish()

    def should_copy(self, src_path, dst_path):
        """
        コピー元とコピー先の更新日時を比較し、コピー要否を判定する。

        コピー先が存在しない場合、またはコピー元の更新日時が
        コピー先より新しい場合にTrueを返す。

        Args:
            src_paths : コピー対象アイテムリスト
            dst_dir (str): コピー先
        """
        if not os.path.exists(dst_path):
            return True
        return os.path.getmtime(src_path) > os.path.getmtime(dst_path)

    def process_file(self, src_path, dst_dir):
        """
        単一ファイルのコピー・移動

        Args:
            src_paths : コピー対象アイテムリスト
            dst_dir (str): コピー先
        """
        file_name = os.path.basename(src_path)
        dst_path = os.path.join(dst_dir, file_name)
        if self.mode == 'move':
            self.log(f"[移動] {file_name}")
            try:
                # 1. 移動を実行する前に「移動元」のタイムスタンプを退避しておく
                src_mtime = os.path.getmtime(src_path)
                src_atime = os.path.getatime(src_path)

                # 2. 上書き先に既存があれば消して移動
                if os.path.exists(dst_path):
                    if os.path.isdir(dst_path):
                        shutil.rmtree(dst_path)
                    else:
                        os.remove(dst_path)
                
                shutil.move(src_path, dst_path)

                # 3. タイムスタンプ復元を上書きし、移動元の日時に強制固定する
                os.utime(dst_path, (src_atime, src_mtime))

            except Exception as e:
                self.log(f"エラー ({file_name}): {e}")

        elif self.mode == 'newer':
            if self.should_copy(src_path, dst_path):
                self.log(f"[コピー中] {file_name}")
                try:
                    shutil.copy2(src_path, dst_path)
                except Exception as e:
                    self.log(f"エラー ({file_name}): {e}")
            else:
                self.log(f"[スキップ (更新なし)] {file_name}")

    def process_directory(self, src_dir, dst_dir):
        """
        ディレクトリのコピー・移動

        Args:
            src_paths : コピー対象アイテムリスト
            dst_dir (str): コピー先
        """
        for root, dirs, files in os.walk(src_dir):
            rel_path = os.path.relpath(root, src_dir)
            target_root = os.path.join(dst_dir, rel_path)
            os.makedirs(target_root, exist_ok=True)

            for file in files:
                s_file = os.path.join(root, file)
                d_file = os.path.join(target_root, file)

                if self.mode == 'move':
                    self.log(f"[移動] {os.path.join(rel_path, file)}")
                    try:
                        if os.path.exists(d_file):
                            os.remove(d_file)
                        shutil.move(s_file, d_file)
                    except Exception as e:
                        self.log(f"エラー ({file}): {e}")
                
                elif self.mode == 'newer':
                    if self.should_copy(s_file, d_file):
                        self.log(f"[コピー中] {os.path.join(rel_path, file)}")
                        try:
                            shutil.copy2(s_file, d_file)
                        except Exception as e:
                            self.log(f"エラー ({file}): {e}")
                    else:
                        self.log(f"[スキップ] {os.path.join(rel_path, file)}")
        
        if self.mode == 'move':
            try:
                shutil.rmtree(src_dir)
            except Exception as e:
                self.log(f"フォルダ削除エラー: {e}")
