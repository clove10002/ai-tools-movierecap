import os
import subprocess
import uuid
from pathlib import Path

TMP_DIR = "/tmp"

def download_and_convert(torrent_url: str) -> str:
    session_id = str(uuid.uuid4())
    download_dir = f"{TMP_DIR}/{session_id}"
    os.makedirs(download_dir, exist_ok=True)

    print("[INFO] Starting download...")
    print("[INFO] Connecting to peers...")
    print("[INFO] Downloading metadata...")

    # Run aria2c as subprocess
    aria2_cmd = [
        "aria2c", "--dir", download_dir, "--seed-time=0",
        "--bt-save-metadata=true", torrent_url
    ]

    try:
        proc = subprocess.Popen(
            aria2_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in proc.stdout:
            line = line.strip()
            if "Downloading" in line:
                print("[INFO] Downloading... ", line)
            elif "Piece" in line:
                print("[INFO] Piece ", line)
            elif "%" in line:
                print("[INFO] %%% ", line)
        proc.wait()
        print("[INFO] Download complete. Starting conversion...")
    except Exception as e:
        raise RuntimeError(f"Download failed: {str(e)}")

    # Find video file
    video_path = None
    for root, _, files in os.walk(download_dir):
        for file in files:
            if file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
                video_path = os.path.join(root, file)
                break
        if video_path:
            break

    if not video_path:
        raise Exception("No video file found in the torrent.")

    # Convert if not MP4
    if not video_path.endswith(".mp4"):
        output_path = os.path.join(download_dir, "converted.mp4")
        print("[INFO] Converting to MP4...")
        try:
            ffmpeg_cmd = [
                "ffmpeg", "-i", video_path,
                "-c:v", "libx264", "-preset", "fast",
                "-c:a", "aac", "-b:a", "128k",
                "-y", output_path,
                "-progress", "pipe:1", "-nostats"
            ]
            proc = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            last_percent = 0.0
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if line.startswith("out_time_ms="):
                    out_time_ms = int(line.split('=')[1])
                    duration_seconds = get_video_duration(video_path)
                    if duration_seconds > 0:
                        percent = min(out_time_ms / (duration_seconds * 1000000) * 100, 100.0)
                        if percent - last_percent >= 5 or percent == 100:
                            print(f"[INFO] Converting... {percent:.1f}%")
                            last_percent = percent
                elif "progress=end" in line:
                    break

            proc.wait()
            print(f"[INFO] Conversion complete. Saved to {output_path}")
            return output_path

        except Exception as e:
            raise RuntimeError(f"Conversion failed: {str(e)}")

    print(f"[INFO] No conversion needed. Saved to {video_path}")
    return video_path

def get_video_duration(video_path: str) -> float:
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0
