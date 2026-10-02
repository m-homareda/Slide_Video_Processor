import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog,messagebox,ttk


class SettingsDialog(tk.Toplevel):
    def __init__(self,parent,video_path):
        super().__init__(parent)
        self.title("スライド動画の処理設定"); self.resizable(False,False); self.result=None
        self.transient(parent); self.grab_set()
        self.language_var=tk.StringVar(value="en")
        self.min_speakers_var=tk.IntVar(value=1); self.max_speakers_var=tk.IntVar(value=2)
        self.make_transcript_var=tk.BooleanVar(value=True)
        self.include_timestamps_var=tk.BooleanVar(value=True)
        self.make_pdf_var=tk.BooleanVar(value=True)
        frame=ttk.Frame(self,padding=12); frame.grid(sticky="nsew")
        ttk.Label(frame,text="動画").grid(row=0,column=0,sticky="nw",pady=4)
        ttk.Label(frame,text=str(video_path),wraplength=560).grid(row=0,column=1,columnspan=2,sticky="w",pady=4)
        ttk.Label(frame,text="認識言語").grid(row=1,column=0,sticky="w",pady=4)
        box=ttk.Combobox(frame,textvariable=self.language_var,values=("en","ja"),state="readonly",width=8)
        box.grid(row=1,column=1,sticky="w",pady=4); box.bind("<<ComboboxSelected>>",self._prompt)
        ttk.Label(frame,text="最小話者数").grid(row=2,column=0,sticky="w",pady=4)
        ttk.Spinbox(frame,from_=1,to=20,textvariable=self.min_speakers_var,width=8).grid(row=2,column=1,sticky="w")
        ttk.Label(frame,text="最大話者数").grid(row=3,column=0,sticky="w",pady=4)
        ttk.Spinbox(frame,from_=1,to=20,textvariable=self.max_speakers_var,width=8).grid(row=3,column=1,sticky="w")
        ttk.Label(frame,text="初期プロンプト").grid(row=4,column=0,sticky="nw",pady=4)
        self.prompt_text=tk.Text(frame,width=70,height=7,wrap="word"); self.prompt_text.grid(row=4,column=1,columnspan=2)
        self.prompt_text.insert("1.0","This is a slide-based presentation. Transcribe the spoken content accurately and preserve technical terms.")
        ttk.Checkbutton(frame,text="話者番号付きTXTを作成",variable=self.make_transcript_var).grid(row=5,column=1,columnspan=2,sticky="w",pady=4)
        ttk.Checkbutton(frame,text="TXTにタイムスタンプを表示",variable=self.include_timestamps_var).grid(row=6,column=1,columnspan=2,sticky="w",pady=4)
        ttk.Checkbutton(frame,text="スライドPDFを作成",variable=self.make_pdf_var).grid(row=7,column=1,columnspan=2,sticky="w",pady=4)
        buttons=ttk.Frame(frame); buttons.grid(row=8,column=0,columnspan=3,sticky="e",pady=(12,0))
        ttk.Button(buttons,text="キャンセル",command=self._cancel).pack(side="right",padx=(8,0))
        ttk.Button(buttons,text="処理開始",command=self._accept).pack(side="right")
        self.protocol("WM_DELETE_WINDOW",self._cancel); self.update_idletasks()
        x=max(0,(self.winfo_screenwidth()-self.winfo_width())//2); y=max(0,(self.winfo_screenheight()-self.winfo_height())//2)
        self.geometry(f"+{x}+{y}")
    def _prompt(self,_event=None):
        self.prompt_text.delete("1.0","end")
        self.prompt_text.insert("1.0","これはスライド形式の発表動画です。専門用語を含め、発話内容を正確に文字起こししてください。" if self.language_var.get()=="ja" else "This is a slide-based presentation. Transcribe the spoken content accurately and preserve technical terms.")
    def _accept(self):
        minimum=int(self.min_speakers_var.get()); maximum=int(self.max_speakers_var.get())
        if minimum<1 or maximum<minimum:
            messagebox.showerror("設定エラー","話者数を確認してください。",parent=self); return
        if not self.make_transcript_var.get() and not self.make_pdf_var.get():
            messagebox.showerror("設定エラー","TXTまたはPDFを選択してください。",parent=self); return
        self.result={"language":self.language_var.get(),"min_speakers":minimum,"max_speakers":maximum,
            "custom_vocab":self.prompt_text.get("1.0","end").strip(),"make_transcript":self.make_transcript_var.get(),
            "include_timestamps":self.include_timestamps_var.get(),"make_pdf":self.make_pdf_var.get()}
        self.destroy()
    def _cancel(self): self.result=None; self.destroy()


def find_ffmpeg():
    candidates=[shutil.which("ffmpeg"),str(Path(__file__).resolve().parent/"ffmpeg.exe")]
    for candidate in candidates:
        if candidate and Path(candidate).is_file(): return candidate
    raise FileNotFoundError("ffmpeg.exe が見つかりません。")


def extract_audio(video_path,audio_path):
    subprocess.run([find_ffmpeg(),"-y","-i",str(video_path),"-vn","-ac","1","-ar","16000","-c:a","pcm_s16le",str(audio_path)],check=True)


def main():
    root=tk.Tk(); root.withdraw(); root.attributes("-topmost",True)
    name=filedialog.askopenfilename(parent=root,title="処理するスライド形式のMP4を選択",filetypes=[("MP4動画","*.mp4"),("すべてのファイル","*.*")])
    if not name: root.destroy(); return 0
    video=Path(name).resolve(); root.deiconify(); root.geometry("1x1-32000-32000"); root.update_idletasks()
    dialog=SettingsDialog(root,video); dialog.attributes("-topmost",True); dialog.lift(); dialog.focus_force(); root.wait_window(dialog); root.withdraw()
    settings=dialog.result
    if settings is None: root.destroy(); return 0
    txt=video.with_suffix(".txt")
    raw_json=video.with_name(video.stem+"_transcript_raw.json")
    pdf=video.with_name(video.stem+"_slides.pdf")
    timeline=video.with_name(video.stem+"_slide_timeline.json")

    planned_outputs=[]
    if settings["make_transcript"]:
        planned_outputs.extend([txt,raw_json])
    if settings["make_pdf"]:
        planned_outputs.extend([pdf,timeline])
    existing_outputs=[path for path in planned_outputs if path.exists()]
    if existing_outputs:
        existing_text="\n".join(str(path) for path in existing_outputs)
        choice=messagebox.askyesnocancel(
            "同名ファイルの確認",
            "次の同名ファイルが既に存在します。\n\n"+existing_text+
            "\n\n[はい] 上書き\n[いいえ] 日時付きの別名で保存\n[キャンセル] 処理中止",
            parent=root
        )
        if choice is None:
            root.destroy()
            return 0
        if choice is False:
            stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
            txt=video.with_name(video.stem+f"_{stamp}.txt")
            raw_json=video.with_name(video.stem+f"_{stamp}_transcript_raw.json")
            pdf=video.with_name(video.stem+f"_{stamp}_slides.pdf")
            timeline=video.with_name(video.stem+f"_{stamp}_slide_timeline.json")

    work=Path(tempfile.mkdtemp(prefix=f"{video.stem}_work_",dir=str(video.parent)))
    audio=work/"audio.wav"
    slide_work=work/"slides"
    try:
        print(f"[1/3] 入力MP4: {video}")
        if settings["make_transcript"]:
            from transcribe_worker import transcribe_audio
            print("[2/3] 音声を抽出しています..."); extract_audio(video,audio)
            print("[2/3] 文字起こしと話者分離を実行しています...")
            transcribe_audio(
                audio,txt,settings["language"],settings["custom_vocab"],
                settings["min_speakers"],settings["max_speakers"],
                settings["include_timestamps"],raw_json,video
            )
        if settings["make_pdf"]:
            from slide_pdf import create_slide_pdf
            print("[3/3] スライドを検出してPDFを作成しています...")
            create_slide_pdf(video,pdf,slide_work,timeline)
        results=[]
        if settings["make_transcript"]: results.extend([str(txt),str(raw_json)])
        if settings["make_pdf"]: results.extend([str(pdf),str(timeline)])
        messagebox.showinfo("処理完了","次のファイルを作成しました。\n\n"+"\n".join(results),parent=root)
        return 0
    except Exception as exc:
        print(f"処理に失敗しました: {exc}",file=sys.stderr); messagebox.showerror("処理失敗",f"{type(exc).__name__}: {exc}",parent=root); return 1
    finally:
        shutil.rmtree(work,ignore_errors=True); root.destroy()

if __name__=="__main__": raise SystemExit(main())
