import gc
import json
import os
from pathlib import Path

import whisperx
from whisperx.diarize import DiarizationPipeline, assign_word_speakers


def _release_cuda_memory():
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def _timestamp(seconds):
    value = max(0, int(float(seconds)))
    hours, remainder = divmod(value, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def transcribe_audio(audio_file, output_file, language, custom_vocab, min_speakers, max_speakers, include_timestamps=True, raw_json_file=None, source_media=None, device="cuda", batch_size=4, compute_type="float16"):
    audio_file = Path(audio_file)
    output_file = Path(output_file)
    raw_json_file = Path(raw_json_file) if raw_json_file else output_file.with_name(output_file.stem + "_transcript_raw.json")
    source_media = str(Path(source_media).resolve()) if source_media else None
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("環境変数 HF_TOKEN が設定されていません。")
    model = whisperx.load_model("large-v3", device=device, compute_type=compute_type, language=language, asr_options={"initial_prompt": custom_vocab})
    audio = whisperx.load_audio(str(audio_file))
    result = model.transcribe(audio, batch_size=batch_size, language=language)
    del model
    _release_cuda_memory()
    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
    del model_a
    _release_cuda_memory()
    diarize_model = DiarizationPipeline(token=token, device=device)
    diarize_segments = diarize_model(audio, min_speakers=min_speakers, max_speakers=max_speakers)
    result = assign_word_speakers(diarize_segments, result)
    del diarize_model
    _release_cuda_memory()
    speaker_map = {}
    speaker_counter = 1
    raw_segments = []
    with output_file.open("w", encoding="utf-8-sig") as handle:
        for segment in result["segments"]:
            raw_speaker = segment.get("speaker", "UNKNOWN")
            if raw_speaker not in speaker_map:
                speaker_map[raw_speaker] = "【不明な話者】" if raw_speaker == "UNKNOWN" else f"【話者{speaker_counter}】"
                if raw_speaker != "UNKNOWN":
                    speaker_counter += 1
            label = speaker_map[raw_speaker]
            text = segment["text"].strip()
            start = float(segment.get("start", 0.0))
            end = float(segment.get("end", start))
            raw_segments.append({"speaker_id": raw_speaker, "speaker_label": label, "start_seconds": start, "end_seconds": end, "start_timestamp": _timestamp(start), "end_timestamp": _timestamp(end), "text": text})
            line = f"[{_timestamp(start)} - {_timestamp(end)}] {label}\n{text}\n\n" if include_timestamps else f"{label}\n{text}\n\n"
            print(line, end="")
            handle.write(line)
    payload = {
        "schema_version": 2,
        "source_media": source_media,
        "language": result.get("language", language),
        "processing_settings": {"model": "large-v3", "device": device, "compute_type": compute_type, "batch_size": batch_size, "min_speakers": min_speakers, "max_speakers": max_speakers, "initial_prompt": custom_vocab, "txt_timestamps_enabled": include_timestamps},
        "segments": raw_segments,
    }
    with raw_json_file.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
