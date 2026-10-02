# Slide Video Processor

動画・音声ファイルから話者番号付き文字起こしを生成し、スライド形式の動画からはスライドPDFも生成するPythonツールです。

## 対応入力

### 動画
`mp4`, `mkv`, `mov`, `avi`, `webm`, `m4v`, `mpeg`, `mpg`, `wmv`, `ts`

動画入力では、文字起こしとスライドPDFを選択できます。

### 音声
`wav`, `mp3`, `m4a`, `flac`, `aac`, `ogg`, `opus`, `wma`

音声入力では文字起こしのみを実行し、スライドPDFの選択は無効になります。実際に処理できるコーデックは、使用しているFFmpegビルドが対応している必要があります。

## 出力

入力が `presentation.mp4` の場合:

```text
presentation.txt
presentation_transcript_raw.json
presentation_slides.pdf
presentation_slide_timeline.json
```

入力が `meeting.m4a` の場合:

```text
meeting.txt
meeting_transcript_raw.json
```

## 必要環境

- Python 3.10以上を推奨
- FFmpeg
- Hugging Faceアクセストークン
- NVIDIA GPUとCUDA対応環境を推奨

## インストール

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

FFmpegはPATHへ追加するか、Windowsでは `ffmpeg.exe` を `lecture_processor.py` と同じフォルダーへ配置してください。

## Hugging Faceトークン

```powershell
$env:HF_TOKEN = "YOUR_HUGGING_FACE_TOKEN"
```

## 使用方法

```powershell
.\.venv\Scripts\python.exe .\lecture_processor.py
```

1. 動画または音声を選択します。
2. 言語、話者数、初期プロンプトを設定します。
3. 文字起こしと、動画の場合はスライドPDFの作成有無を選択します。
4. 処理開始を選択します。

## 注意事項

- スライドPDFは、画面全体の変化が激しすぎないスライド形式の動画を想定しています。
- カメラ映像、アニメーション、埋込み動画、頻繁なズームや画面共有切替がある場合は誤検出する可能性があります。
- 音声認識には誤りが含まれます。固有名詞、専門用語、数値などは元メディアで確認してください。
- 利用者が正当に取り扱えるメディアだけを処理してください。
- 入力メディアや生成物、認証情報をGitへコミットしないでください。
