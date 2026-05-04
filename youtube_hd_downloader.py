#!/usr/bin/env python3
"""Download YouTube videos in 1080p or higher using yt-dlp.

Usage examples:
  python youtube_hd_downloader.py "https://www.youtube.com/watch?v=..."
  python youtube_hd_downloader.py --output "downloads/%(title)s.%(ext)s"
  python youtube_hd_downloader.py --allow-lower-resolution
"""

from __future__ import annotations

import argparse
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


def build_ydl_options(output_template: str, allow_lower_resolution: bool) -> dict[str, Any]:
    # Prefer MP4 video formats at 1080p+ plus best audio, then merge.
    preferred_hd = (
        "bestvideo[height>=1080][ext=mp4]+bestaudio[ext=m4a]/"
        "bestvideo[height>=1080]+bestaudio/best[height>=1080]"
    )
    format_selector = preferred_hd if not allow_lower_resolution else f"{preferred_hd}/best"

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

    ydl_opts = build_ydl_options(args.output, args.allow_lower_resolution)

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as exc:  # noqa: BLE001
        print(f"Download failed: {exc}", file=sys.stderr)
        return 1

    print("Download complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
