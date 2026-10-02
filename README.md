# Slide Video Processor

スライドを中心に進行するMP4動画から、スライドPDFと話者番号付きの文字起こしTXTを生成するPythonツールです。  
講義、説明会、発表、講演、社内共有動画など、画面全体の変化が激しすぎないスライド形式の動画を、検索・確認しやすいローカル資料へ変換します。

## 主な機能

- GUIから処理対象のMP4を選択
- 日本語（`ja`）・英語（`en`）の音声認識
- 初期プロンプトの編集
- 最小・最大話者数の指定
- 話者番号付きTXTの生成
- TXTへのタイムスタンプ表示切替
- WhisperXの認識結果と処理条件をJSONへ保存
- 画面変化後の安定フレームからスライドPDFを生成
- 近似重複スライドの除外
- PDFページと動画内時刻の対応をJSONへ保存
- 同名成果物の上書き、日時付き別名保存、処理中止を選択

## 対象に向く動画

- スライドが数秒以上表示される動画
- スライド切替が明確な発表・講演・説明動画
- 画面の大部分が静止しており、必要なタイミングだけ切り替わる動画

次のような動画では、既定のしきい値で正しく抽出できない場合があります。

- カメラ映像が常時大きく動く動画
- スライド内動画やアニメーションが多い動画
- 頻繁なズーム、パン、画面共有切替がある動画
- 1枚の表示時間が極端に短い動画
- 似たスライドが多く、差分が非常に小さい動画

## 構成ファイル

- **lecture_processor.py**: MP4選択、設定画面、音声抽出、処理の統合
- **slide_pdf.py**: 画面変化検出、安定フレーム採用、重複除外、PDF・時刻JSON生成
- **transcribe_worker.py**: WhisperXによる文字起こし、アラインメント、話者分離、TXT・JSON生成
- **requirements.txt**: Python依存パッケージ
- **.gitignore**: 仮想環境、動画、音声、生成物、認証情報などをGit管理から除外

## 出力ファイル

入力が `presentation.mp4` の場合、選択した処理に応じて同じフォルダーへ次を生成します。

```text
presentation.txt
presentation_transcript_raw.json
presentation_slides.pdf
presentation_slide_timeline.json
```

- **presentation.txt**: 話者番号付き文字起こし。設定により開始・終了時刻を表示
- **presentation_transcript_raw.json**: 発言単位の時刻、話者、本文、認識条件
- **presentation_slides.pdf**: 動画から抽出したスライド
- **presentation_slide_timeline.json**: PDFページと動画内時刻、スライド検出条件

## 必要環境

- Python 3.10以上を推奨
- FFmpeg
- Hugging Faceアクセストークン
- NVIDIA GPUとCUDA対応環境を推奨

文字起こしの既定値は次のとおりです。

```text
model: large-v3
device: cuda
compute_type: float16
batch_size: 4
```

CPU環境やVRAMの少ない環境では、`transcribe_worker.py` の `device`、`compute_type`、`batch_size` の調整が必要です。

## FFmpeg

FFmpegをインストールし、`ffmpeg` コマンドをPATHから実行できるようにしてください。  
Windowsでは、`ffmpeg.exe` を `lecture_processor.py` と同じフォルダーへ配置する方法も利用できます。

## インストール

仮想環境の使用を推奨します。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

WhisperX、PyTorch、CUDA、TorchCodec、FFmpegの対応関係は実行環境によって異なります。依存関係の導入で問題が起きた場合は、それぞれの公式ドキュメントで対応バージョンを確認してください。

## Hugging Faceトークン

話者分離にはHugging Faceアクセストークンを使用します。環境変数 `HF_TOKEN` を設定してください。

現在のPowerShellセッションだけに設定する例:

```powershell
$env:HF_TOKEN = "YOUR_HUGGING_FACE_TOKEN"
```

トークンをソースコード、README、コミット履歴へ保存しないでください。

## 使用方法

```powershell
.\.venv\Scripts\python.exe .\lecture_processor.py
```

1. スライド形式のMP4を選択します。
2. 言語、話者数、初期プロンプトを設定します。
3. 文字起こし、TXTのタイムスタンプ表示、スライドPDFの作成有無を選択します。
4. **処理開始**を選択します。
5. MP4と同じフォルダーに成果物が生成されます。

同名成果物が存在する場合は、上書き、日時付き別名保存、キャンセルを選択できます。

## スライド検出方式

1. 動画を先頭から順次読み込みます。
2. 一定間隔ごとの比較フレームを縮小・グレースケール化・平滑化します。
3. 直前の比較フレームとの平均画素差から大きな画面変化を検出します。
4. 変化後、差が小さい状態が一定回数続いたフレームを採用します。
5. 採用済み画像との近似重複を除外します。
6. 採用画像を時系列順にPDFへ保存します。

既定値:

```text
sample_interval_seconds: 0.5
change_threshold: 0.055
stable_threshold: 0.012
stable_sample_count: 3
duplicate_threshold: 0.01
```

動画に合わせて `slide_pdf.py` の値を調整してください。時刻JSONへ保存される時刻は厳密な切替瞬間ではなく、変化後に安定フレームを採用した時刻です。

## 注意事項

- 利用者が正当に取り扱える動画だけを処理してください。
- 動画、スライド、文字起こしには著作権、機密保持、個人情報、利用規約が適用される場合があります。
- 権利者の許可なく、入力動画や生成物を公開・再配布しないでください。
- 音声認識には誤りが含まれます。固有名詞、専門用語、数値、化学式などは元動画やスライドで確認してください。
- 自動生成物を課題、業務、公開資料などへ使用する場合、最終内容は利用者自身で確認してください。
- 動画、音声、生成物、`.env`、`HF_TOKEN`、個人情報や機密情報をGitへコミットしないでください。

## 使用技術

- Python
- WhisperX
- pyannote.audio（WhisperXの話者分離処理で使用）
- PyTorch
- OpenCV
- NumPy
- Pillow
- tkinter
- FFmpeg
