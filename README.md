# YouTube 1080p+ Downloader

This repository provides a Python script that downloads a YouTube video in **1080p or higher** (video + audio merged into MP4).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Install ffmpeg (required for merging video and audio streams)
# Windows: Download from https://ffmpeg.org/download.html or use Chocolatey: choco install ffmpeg
# macOS: brew install ffmpeg
# Linux: apt install ffmpeg or yum install ffmpeg
```

## Usage

```bash
python youtube_hd_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Optional flags:

- `-o/--output` to control output path and filename template.
- `--allow-lower-resolution` to fall back to best available if 1080p+ is not available.

Example:

```bash
python youtube_hd_downloader.py \
  --output "downloads/%(title)s.%(ext)s" \
  "https://www.youtube.com/watch?v=VIDEO_ID"
```

## Notes

- Respect YouTube's Terms of Service and copyright laws in your region.
- This downloader may require `ffmpeg` to merge separate video and audio streams for 1080p+ downloads.
- Some videos may not provide downloadable 1080p+ streams.

## Notebook Tutorial

If you prefer a step-by-step, beginner-friendly walkthrough, open:

- `youtube_hd_downloader_tutorial.ipynb`

This notebook explains each part of the download flow with comments for junior developers.
