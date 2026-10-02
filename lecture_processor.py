import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".mpeg", ".mpg", ".wmv", ".ts"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".aac", ".ogg", ".opus", ".wma"}


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, media_path, is_video):
        super().__init__(parent)
        self.title("メディア処理設定")
        self.resizable(False, False)
        self.result = None
        self.transient(parent)
        self.grab_set()

        self.language_var = tk.StringVar(value="en")
        self.min_speakers_var = tk.IntVar(value=1)
        self.max_speakers_var = tk.IntVar(value=2)
        self.make_transcript_var = tk.BooleanVar(value=True)
        self.include_timestamps_var = tk.BooleanVar(value=True)
        self.make_pdf_var = tk.BooleanVar(value=is_video)

        frame = ttk.Frame(self, padding=12)
        frame.grid(sticky="nsew")
        ttk.Label(frame, text="入力").grid(row=0, column=0, sticky="nw", pady=4)
        ttk.Label(frame, text=str(media_path), wraplength=560).grid(row=0, column=1, columnspan=2, sticky="w", pady=4)
        ttk.Label(frame, text="認識言語").grid(row=1, column=0, sticky="w", pady=4)
        language_box = ttk.Combobox(frame, textvariable=self.language_var, values=("en", "ja"), state="readonly", width=8)
        language_box.grid(row=1, column=1, sticky="w", pady=4)
        language_box.bind("<<ComboboxSelected>>", self._set_prompt)
        ttk.Label(frame, text="最小話者数").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Spinbox(frame, from_=1, to=20, textvariable=self.min_speakers_var, width=8).grid(row=2, column=1, sticky="w")
        ttk.Label(frame, text="最大話者数").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Spinbox(frame, from_=1, to=20, textvariable=self.max_speakers_var, width=8).grid(row=3, column=1, sticky="w")
        ttk.Label(frame, text="初期プロンプト").grid(row=4, column=0, sticky="nw", pady=4)
        self.prompt_text = tk.Text(frame, width=70, height=7, wrap="word")
        self.prompt_text.grid(row=4, column=1, columnspan=2)
        self.prompt_text.insert("1.0", "This is a recorded presentation. Transcribe the spoken content accurately and preserve technical terms.")
        ttk.Checkbutton(frame, text="話者番号付きTXTを作成", variable=self.make_transcript_var).grid(row=5, column=1, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(frame, text="TXTにタイムスタンプを表示", variable=self.include_timestamps_var).grid(row=6, column=1, columnspan=2, sticky="w", pady=4)
        pdf_check = ttk.Checkbutton(frame, text="スライドPDFを作成", variable=self.make_pdf_var)
        pdf_check.grid(row=7, column=1, columnspan=2, sticky="w", pady=4)
        if not is_video:
            pdf_check.state(["disabled"])
            ttk.Label(frame, text="音声入力ではスライドPDFを作成しません。", foreground="#666666").grid(row=8, column=1, columnspan=2, sticky="w")
        buttons = ttk.Frame(frame)
        buttons.grid(row=9, column=0, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="キャンセル", command=self._cancel).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="処理開始", command=self._accept).pack(side="right")
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.update_idletasks()
        x = max(0, (self.winfo_screenwidth() - self.winfo_width()) // 2)
        y = max(0, (self.winfo_screenheight() - self.winfo_height()) // 2)
        self.geometry(f"+{x}+{y}")

    def _set_prompt(self, _event=None):
        self.prompt_text.delete("1.0", "end")
        prompt = "これは録音された発表です。専門用語を含め、発話内容を正確に文字起こししてください。" if self.language_var.get() == "ja" else "This is a recorded presentation. Transcribe the spoken content accurately and preserve technical terms."
        self.prompt_text.insert("1.0", prompt)

    def _accept(self):
        minimum = int(self.min_speakers_var.get())
        maximum = int(self.max_speakers_var.get())
        if minimum < 1 or maximum < minimum:
            messagebox.showerror("設定エラー", "話者数を確認してください。", parent=self)
            return
        if not self.make_transcript_var.get() and not self.make_pdf_var.get():
            messagebox.showerror("設定エラー", "TXTまたはPDFを選択してください。", parent=self)
            return
        self.result = {
            "language": self.language_var.get(),
            "min_speakers": minimum,
            "max_speakers": maximum,
            "custom_vocab": self.prompt_text.get("1.0", "end").strip(),
            "make_transcript": self.make_transcript_var.get(),
            "include_timestamps": self.include_timestamps_var.get(),
            "make_pdf": self.make_pdf_var.get(),
        }
        self.destroy()

    def _cancel(self):
        self.destroy()


def find_ffmpeg():
    candidates = [shutil.which("ffmpeg"), str(Path(__file__).resolve().parent / "ffmpeg.exe")]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise FileNotFoundError("ffmpeg が見つかりません。PATHへ追加するか、スクリプトと同じフォルダーへ配置してください。")


def extract_audio(media_path, audio_path):
    command = [
        find_ffmpeg(), "-y", "-i", str(media_path), "-vn", "-ac", "1",
        "-ar", "16000", "-c:a", "pcm_s16le", str(audio_path),
    ]
    completed = subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        details = completed.stderr.strip()
        if len(details) > 4000:
            details = details[-4000:]
        raise RuntimeError(
            "FFmpegによる音声変換に失敗しました。"
            f"\n終了コード: {completed.returncode}"
            f"\n入力: {media_path}"
            f"\n出力: {audio_path}"
            f"\n\nFFmpeg出力:\n{details}"
        )


def choose_outputs(media, settings):
    txt = media.with_suffix(".txt")
    raw_json = media.with_name(media.stem + "_transcript_raw.json")
    pdf = media.with_name(media.stem + "_slides.pdf")
    timeline = media.with_name(media.stem + "_slide_timeline.json")
    planned = []
    if settings["make_transcript"]:
        planned.extend([txt, raw_json])
    if settings["make_pdf"]:
        planned.extend([pdf, timeline])
    existing = [path for path in planned if path.exists()]
    if existing:
        choice = messagebox.askyesnocancel("同名ファイルの確認", "次の同名ファイルが既に存在します。\n\n" + "\n".join(str(path) for path in existing) + "\n\n[はい] 上書き\n[いいえ] 日時付きの別名で保存\n[キャンセル] 処理中止")
        if choice is None:
            return None
        if choice is False:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            txt = media.with_name(media.stem + f"_{stamp}.txt")
            raw_json = media.with_name(media.stem + f"_{stamp}_transcript_raw.json")
            pdf = media.with_name(media.stem + f"_{stamp}_slides.pdf")
            timeline = media.with_name(media.stem + f"_{stamp}_slide_timeline.json")
    return txt, raw_json, pdf, timeline


def main():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    media_name = filedialog.askopenfilename(
        parent=root,
        title="処理する動画または音声を選択",
        filetypes=[
            ("対応メディア", "*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.mpeg *.mpg *.wmv *.ts *.wav *.mp3 *.m4a *.flac *.aac *.ogg *.opus *.wma"),
            ("動画", "*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.mpeg *.mpg *.wmv *.ts"),
            ("音声", "*.wav *.mp3 *.m4a *.flac *.aac *.ogg *.opus *.wma"),
            ("すべてのファイル", "*.*"),
        ],
    )
    if not media_name:
        root.destroy()
        return 0
    media = Path(media_name).resolve()
    extension = media.suffix.lower()
    if extension not in VIDEO_EXTENSIONS | AUDIO_EXTENSIONS:
        messagebox.showerror("未対応形式", f"未対応の拡張子です: {extension}", parent=root)
        root.destroy()
        return 1
    is_video = extension in VIDEO_EXTENSIONS
    root.deiconify()
    root.geometry("1x1-32000-32000")
    root.update_idletasks()
    dialog = SettingsDialog(root, media, is_video)
    dialog.attributes("-topmost", True)
    dialog.lift()
    dialog.focus_force()
    root.wait_window(dialog)
    root.withdraw()
    if dialog.result is None:
        root.destroy()
        return 0
    settings = dialog.result
    outputs = choose_outputs(media, settings)
    if outputs is None:
        root.destroy()
        return 0
    txt, raw_json, pdf, timeline = outputs
    # Keep temporary paths short. Long media names and deep folders can exceed
    # Windows/FFmpeg path limits when the work directory repeats the media name.
    work = Path(tempfile.mkdtemp(prefix="svp_"))
    audio = work / "audio.wav"
    slide_work = work / "slides"
    try:
        print(f"[1/3] 入力メディア: {media}")
        if settings["make_transcript"]:
            from transcribe_worker import transcribe_audio
            print("[2/3] 音声を変換しています...")
            extract_audio(media, audio)
            print("[2/3] 文字起こしと話者分離を実行しています...")
            transcribe_audio(audio, txt, settings["language"], settings["custom_vocab"], settings["min_speakers"], settings["max_speakers"], settings["include_timestamps"], raw_json, media)
        if settings["make_pdf"]:
            from slide_pdf import create_slide_pdf
            print("[3/3] スライドを検出してPDFを作成しています...")
            create_slide_pdf(media, pdf, slide_work, timeline)
        results = []
        if settings["make_transcript"]:
            results.extend([str(txt), str(raw_json)])
        if settings["make_pdf"]:
            results.extend([str(pdf), str(timeline)])
        messagebox.showinfo("処理完了", "次のファイルを作成しました。\n\n" + "\n".join(results), parent=root)
        return 0
    except Exception as exc:
        print(f"処理に失敗しました: {exc}", file=sys.stderr)
        messagebox.showerror("処理失敗", f"{type(exc).__name__}: {exc}", parent=root)
        return 1
    finally:
        shutil.rmtree(work, ignore_errors=True)
        root.destroy()


if __name__ == "__main__":
    raise SystemExit(main())
