import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image


def _comparison_image(frame,width=320):
    gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    height=max(1,int(gray.shape[0]*width/frame.shape[1]))
    resized=cv2.resize(gray,(width,height),interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(resized,(5,5),0)


def _difference(first,second):
    return float(np.mean(cv2.absdiff(first,second)))/255.0


def _content_crop(frame):
    gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    mask=gray>18
    rows=np.where(mask.any(axis=1))[0]
    cols=np.where(mask.any(axis=0))[0]
    if rows.size==0 or cols.size==0:
        return frame
    top,bottom=int(rows[0]),int(rows[-1])+1
    left,right=int(cols[0]),int(cols[-1])+1
    if bottom-top<frame.shape[0]*0.5 or right-left<frame.shape[1]*0.5:
        return frame
    return frame[top:bottom,left:right]


def _duplicate(candidate,accepted,threshold):
    for existing in accepted:
        comparison=existing
        if comparison.shape!=candidate.shape:
            comparison=cv2.resize(comparison,(candidate.shape[1],candidate.shape[0]),interpolation=cv2.INTER_AREA)
        if _difference(candidate,comparison)<=threshold:
            return True
    return False


def _timestamp(seconds):
    value=max(0,int(float(seconds)))
    hours,remainder=divmod(value,3600)
    minutes,secs=divmod(remainder,60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def create_slide_pdf(video_path,output_pdf,work_dir,timeline_json=None,
                     sample_interval_seconds=0.5,change_threshold=0.055,
                     stable_threshold=0.012,stable_sample_count=3,
                     duplicate_threshold=0.010):
    video_path=Path(video_path); output_pdf=Path(output_pdf); work_dir=Path(work_dir)
    if timeline_json is None:
        timeline_json=output_pdf.with_name(output_pdf.stem+"_timeline.json")
    timeline_json=Path(timeline_json)
    work_dir.mkdir(parents=True,exist_ok=True)
    capture=cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"動画を開けません: {video_path}")
    fps=capture.get(cv2.CAP_PROP_FPS)
    total_frames=int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if not fps or fps<=0:
        capture.release(); raise RuntimeError("動画のFPSを取得できません。")
    frame_step=max(1,int(round(fps*sample_interval_seconds)))
    accepted_frames=[]; accepted_comparisons=[]; accepted_slides=[]
    previous=None; pending=True; stable_count=0; frame_index=0; next_sample=0; last_progress=-1
    try:
        while True:
            if not capture.grab(): break
            if frame_index>=next_sample:
                ok,frame=capture.retrieve()
                if not ok: break
                current=_comparison_image(frame)
                if previous is None:
                    previous=current; stable_count=1
                else:
                    diff=_difference(previous,current)
                    if diff>=change_threshold:
                        pending=True; stable_count=0
                    elif diff<=stable_threshold:
                        stable_count+=1
                    else:
                        stable_count=0
                    if pending and stable_count>=stable_sample_count:
                        cropped=_content_crop(frame)
                        candidate=_comparison_image(cropped)
                        if not _duplicate(candidate,accepted_comparisons,duplicate_threshold):
                            accepted_frames.append(cropped.copy()); accepted_comparisons.append(candidate)
                            slide_number=len(accepted_frames); start=frame_index/fps; seconds=int(start)
                            image_path=work_dir/f"slide_{slide_number:04d}_{seconds:06d}s.png"
                            cv2.imwrite(str(image_path),cropped)
                            accepted_slides.append({"slide_number":slide_number,"pdf_page":slide_number,
                                "start_seconds":start,"start_timestamp":_timestamp(start),
                                "source_frame_index":frame_index,"image_filename":image_path.name})
                            print(f"スライド候補を採用: {image_path.name}",flush=True)
                        pending=False
                    previous=current
                next_sample+=frame_step
            if total_frames>0:
                progress=int((frame_index+1)*100/total_frames)
                if progress>=last_progress+10:
                    last_progress=progress; print(f"スライド検出進捗: {min(progress,100)}%",flush=True)
            frame_index+=1
    finally:
        capture.release()
    if not accepted_frames:
        raise RuntimeError("スライドを1枚も検出できませんでした。")
    pages=[Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)).convert("RGB") for frame in accepted_frames]
    output_pdf.parent.mkdir(parents=True,exist_ok=True)
    pages[0].save(output_pdf,"PDF",save_all=True,append_images=pages[1:],resolution=150.0)
    timeline_json.parent.mkdir(parents=True,exist_ok=True)
    payload={
        "schema_version": 1,
        "source_video": str(video_path),
        "output_pdf": str(output_pdf),
        "timestamp_semantics": "stable_frame_capture_time",
        "processing_settings": {
            "sample_interval_seconds": sample_interval_seconds,
            "change_threshold": change_threshold,
            "stable_threshold": stable_threshold,
            "stable_sample_count": stable_sample_count,
            "duplicate_threshold": duplicate_threshold
        },
        "slides": accepted_slides
    }
    with timeline_json.open("w",encoding="utf-8") as handle:
        json.dump(payload,handle,ensure_ascii=False,indent=2)
    print(f"スライドPDF作成完了: {output_pdf}")
    print(f"スライド時刻JSON: {timeline_json}")
    print(f"採用スライド数: {len(accepted_frames)}")
