#!/usr/bin/env python3
"""Download YouTube videos in 1080p or higher using yt-dlp.

Usage examples:
  python youtube_hd_downloader.py "https://www.youtube.com/watch?v=..."
  python youtube_hd_downloader.py --output "downloads/%(title)s.%(ext)s"
  python youtube_hd_downloader.py --allow-lower-resolution
"""

from __future__ import annotations

import argparse
import shutil
import sys
from typing import Any

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download YouTube videos at 1080p+ (video + audio merged)."
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="YouTube URL. If omitted, you'll be prompted interactively.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="%(title)s.%(ext)s",
        help="Output file template for yt-dlp (default: %%(title)s.%%(ext)s)",
    )
    parser.add_argument(
        "--allow-lower-resolution",
        action="store_true",
        help="Fallback to best available if 1080p+ does not exist.",
    )
    return parser.parse_args()


def is_ffmpeg_installed() -> bool:
    return shutil.which("ffmpeg") is not None


def build_ydl_options(
    output_template: str,
    allow_lower_resolution: bool,
    ffmpeg_available: bool,
) -> dict[str, Any]:
    if ffmpeg_available:
        preferred_hd = (
            "bestvideo[height>=1080][ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo[height>=1080]+bestaudio/best[height>=1080]"
        )
        format_selector = preferred_hd
        if allow_lower_resolution:
            format_selector = f"{preferred_hd}/bestvideo+bestaudio/best"
    else:
        combined_hd = "best[height>=1080][ext=mp4]/best[height>=1080]"
        format_selector = combined_hd
        if allow_lower_resolution:
            format_selector = f"{combined_hd}/best"

    return {
        "format": format_selector,
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
    }


def main() -> int:
    args = parse_args()

    try:
        from yt_dlp import YoutubeDL
    except ImportError:
        print(
            "yt-dlp is not installed. Install it with: pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1
    url = args.url or input("Enter YouTube URL: ").strip()

    if not url:
        print("No URL provided.", file=sys.stderr)
        return 1

    ffmpeg_available = is_ffmpeg_installed()
    if not ffmpeg_available:
        print(
            "Warning: ffmpeg is not installed. Using combined-format fallback when possible.",
            file=sys.stderr,
        )

    ydl_opts = build_ydl_options(
        args.output,
        args.allow_lower_resolution,
        ffmpeg_available,
    )

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as exc:  # noqa: BLE001
        print(
            f"Download failed ({exc.__class__.__name__}): {exc}",
            file=sys.stderr,
        )
        return 1

    print("Download complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
