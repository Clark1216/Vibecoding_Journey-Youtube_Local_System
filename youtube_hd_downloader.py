#!/usr/bin/env python3
"""Download YouTube videos in 1080p or higher using yt-dlp.

Usage examples:
  python youtube_hd_downloader.py "https://www.youtube.com/watch?v=..."
  python youtube_hd_downloader.py --output "downloads/%(title)s.%(ext)s"
  python youtube_hd_downloader.py --allow-lower-resolution
  python youtube_hd_downloader.py --cookies cookies.txt "https://www.youtube.com/watch?v=..."

Handles age-restricted, region-locked, and copyright-claimed videos automatically.
If only images are available, the video is completely blocked and cannot be downloaded.
Place cookies.txt in the project root for automatic age-restricted video support.
"""

from __future__ import annotations

import argparse
import os
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
    parser.add_argument(
        "--cookies",
        default="cookies.txt",
        help="Path to cookies file for age-restricted or login-required videos (default: cookies.txt in root).",
    )
    return parser.parse_args()


def is_ffmpeg_installed() -> bool:
    return shutil.which("ffmpeg") is not None


def build_ydl_options(
    output_template: str,
    allow_lower_resolution: bool,
    ffmpeg_available: bool,
    cookies: str | None = None,
    fallback_mode: bool = False,
) -> dict[str, Any]:
    if fallback_mode:
        # For copyright-blocked videos, try various format combinations
        format_selector = (
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo+bestaudio/"
            "best[ext=mp4]/"
            "best"
        )
    else:
        if ffmpeg_available:
            # Include more fallbacks for copyright claims
            preferred_hd = (
                "bestvideo[height>=1080][ext=mp4]+bestaudio[ext=m4a]/"
                "bestvideo[height>=1080]+bestaudio/"
                "best[height>=1080][ext=mp4]/"
                "best[height>=1080]"
            )
            format_selector = preferred_hd
            if allow_lower_resolution:
                format_selector = f"{preferred_hd}/bestvideo+bestaudio/best"
        else:
            combined_hd = "best[height>=1080][ext=mp4]/best[height>=1080]"
            format_selector = combined_hd
            if allow_lower_resolution:
                format_selector = f"{combined_hd}/best"

    options = {
        "format": format_selector,
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
    }
    if cookies:
        options["cookiefile"] = cookies
    return options


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
        args.cookies if os.path.exists(args.cookies) else None,
    )

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as exc:  # noqa: BLE001
        error_msg = str(exc)
        cookies_file = args.cookies if os.path.exists(args.cookies) else None
        if "Requested format is not available" in error_msg:
            print(
                "Listing available formats:",
                file=sys.stderr,
            )
            try:
                with YoutubeDL({**ydl_opts, "listformats": True}) as ydl:
                    ydl.download([url])
            except Exception:
                pass  # Ignore errors from listing
            print(
                "If only images are listed above, the video is completely unavailable for download.",
                file=sys.stderr,
            )
            if cookies_file:
                print(
                    f"Retrying with cookies ({cookies_file})...",
                    file=sys.stderr,
                )
                ydl_opts_with_cookies = build_ydl_options(
                    args.output,
                    args.allow_lower_resolution,
                    ffmpeg_available,
                    cookies_file,
                )
                try:
                    with YoutubeDL(ydl_opts_with_cookies) as ydl:
                        ydl.download([url])
                except Exception as retry_exc:
                    retry_error_msg = str(retry_exc)
                    if "Requested format is not available" in retry_error_msg:
                        print(
                            "Format restrictions detected (possibly copyright claims). Listing available formats with cookies:",
                            file=sys.stderr,
                        )
                        try:
                            with YoutubeDL({**ydl_opts_with_cookies, "listformats": True}) as ydl:
                                ydl.download([url])
                        except Exception:
                            pass
                        print(
                            "If only images are listed above, the video is completely unavailable for download.",
                            file=sys.stderr,
                        )
                        print(
                            "Retrying with copyright-friendly format selection...",
                            file=sys.stderr,
                        )
                        ydl_opts_fallback = build_ydl_options(
                            args.output,
                            args.allow_lower_resolution,
                            ffmpeg_available,
                            cookies_file,
                            fallback_mode=True,
                        )
                        try:
                            with YoutubeDL(ydl_opts_fallback) as ydl:
                                ydl.download([url])
                        except Exception as fallback_exc:
                            print(
                                f"Download failed even with fallback ({fallback_exc.__class__.__name__}): {fallback_exc}",
                                file=sys.stderr,
                            )
                            return 1
                    else:
                        print(
                            f"Download failed even with cookies ({retry_exc.__class__.__name__}): {retry_exc}",
                            file=sys.stderr,
                        )
                        return 1
            else:
                print(
                    "Retrying with copyright-friendly format selection...",
                    file=sys.stderr,
                )
                ydl_opts_fallback = build_ydl_options(
                    args.output,
                    args.allow_lower_resolution,
                    ffmpeg_available,
                    None,
                    fallback_mode=True,
                )
                try:
                    with YoutubeDL(ydl_opts_fallback) as ydl:
                        ydl.download([url])
                except Exception as fallback_exc:
                    print(
                        f"Download failed even with fallback ({fallback_exc.__class__.__name__}): {fallback_exc}",
                        file=sys.stderr,
                    )
                    return 1
        elif (
            "This video is not available" in error_msg
            and cookies_file
        ):
            print(
                f"Video appears age-restricted. Retrying with cookies ({cookies_file})...",
                file=sys.stderr,
            )
            ydl_opts_with_cookies = build_ydl_options(
                args.output,
                args.allow_lower_resolution,
                ffmpeg_available,
                cookies_file,
            )
            try:
                with YoutubeDL(ydl_opts_with_cookies) as ydl:
                    ydl.download([url])
            except Exception as retry_exc:
                print(
                    f"Download failed even with cookies ({retry_exc.__class__.__name__}): {retry_exc}",
                    file=sys.stderr,
                )
                return 1
        else:
            print(
                f"Download failed ({exc.__class__.__name__}): {exc}",
                file=sys.stderr,
            )
            return 1

    print("Download complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
