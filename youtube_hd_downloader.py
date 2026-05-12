#!/usr/bin/env python3
"""Download YouTube videos in 1080p or higher using yt-dlp.

Usage examples:
  python youtube_hd_downloader.py "https://www.youtube.com/watch?v=..."
  python youtube_hd_downloader.py --output "downloads/%(title)s.%(ext)s"
  python youtube_hd_downloader.py --allow-lower-resolution
  python youtube_hd_downloader.py --cookies cookies.txt "https://www.youtube.com/watch?v=..."
  python youtube_hd_downloader.py --write-subs --sub-langs en "https://www.youtube.com/watch?v=..."
  python youtube_hd_downloader.py --subtitles-only --write-auto-subs --convert-subs srt "https://www.youtube.com/watch?v=..."
  python youtube_hd_downloader.py --mp3-playlist "https://www.youtube.com/playlist?list=..."

Handles age-restricted, region-locked, and copyright-claimed videos automatically.
If only images are available, the video is completely blocked and cannot be downloaded.
Place cookies.txt in the project root for automatic age-restricted video support.
"""

from __future__ import annotations

import argparse
import os
import re
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
    parser.add_argument(
        "--write-subs",
        action="store_true",
        help="Download manually provided subtitles with the video.",
    )
    parser.add_argument(
        "--write-auto-subs",
        action="store_true",
        help="Download YouTube auto-generated subtitles.",
    )
    parser.add_argument(
        "--subtitles-only",
        action="store_true",
        help="Download subtitles without downloading the video.",
    )
    parser.add_argument(
        "--sub-langs",
        default="en",
        help="Comma-separated subtitle languages to download (default: en, use all for every language).",
    )
    parser.add_argument(
        "--sub-format",
        default="srt/vtt/best",
        help="Subtitle download preference for yt-dlp (default: srt/vtt/best).",
    )
    parser.add_argument(
        "--convert-subs",
        default="srt",
        help="Convert downloaded subtitles to this format (default: srt, use none to disable).",
    )
    parser.add_argument(
        "--mp3-playlist",
        action="store_true",
        help="Download a YouTube playlist as MP3 files into a folder named after the playlist.",
    )
    parser.add_argument(
        "--audio-quality",
        default="0",
        help="MP3 quality for --mp3-playlist (yt-dlp/ffmpeg scale, default: 0 best).",
    )
    return parser.parse_args()


def is_ffmpeg_installed() -> bool:
    return shutil.which("ffmpeg") is not None


def sanitize_folder_name(name: str) -> str:
    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return safe_name or "YouTube Playlist"


def describe_unavailable_entry(entry: Any, index: int) -> str | None:
    if entry is None:
        return f"{index}. Unknown deleted/private video"
    if not isinstance(entry, dict):
        return f"{index}. Unknown unavailable playlist item"

    title = entry.get("title") or entry.get("id") or "Unknown title"
    availability = (entry.get("availability") or "").lower()
    reason = (
        entry.get("reason")
        or entry.get("error")
        or entry.get("availability")
        or "unavailable"
    )
    deleted_titles = {
        "[deleted video]",
        "[private video]",
        "deleted video",
        "private video",
    }
    if title.lower() in deleted_titles or availability in {
        "deleted",
        "private",
        "premium_only",
        "subscriber_only",
        "unavailable",
    }:
        video_id = entry.get("id")
        id_suffix = f" ({video_id})" if video_id else ""
        return f"{index}. {title}{id_suffix} - {reason}"
    return None


def find_unavailable_playlist_entries(playlist_info: dict[str, Any]) -> list[str]:
    unavailable: list[str] = []
    for fallback_index, entry in enumerate(playlist_info.get("entries") or [], start=1):
        index = fallback_index
        if isinstance(entry, dict):
            index = entry.get("playlist_index") or fallback_index
        description = describe_unavailable_entry(entry, index)
        if description:
            unavailable.append(description)
    return unavailable


def print_playlist_report(playlist_info: dict[str, Any], playlist_folder: str) -> None:
    entries = playlist_info.get("entries") or []
    unavailable_entries = find_unavailable_playlist_entries(playlist_info)
    reported_total = playlist_info.get("playlist_count") or playlist_info.get("n_entries")
    parsed_total = len(entries)
    inaccessible_count = len(unavailable_entries)

    if isinstance(reported_total, int) and reported_total > parsed_total:
        inaccessible_count += reported_total - parsed_total

    downloadable_count = max(parsed_total - len(unavailable_entries), 0)

    print("\nPlaylist parse summary:")
    print(f"  Title: {playlist_info.get('title') or 'YouTube Playlist'}")
    print(f"  Output folder: {playlist_folder}")
    if isinstance(reported_total, int):
        print(f"  Reported playlist items: {reported_total}")
    print(f"  Parsed playlist items: {parsed_total}")
    print(f"  Downloadable items detected: {downloadable_count}")
    print(f"  Deleted/private/unavailable items detected: {inaccessible_count}")

    if unavailable_entries:
        print("\nDeleted/private/unavailable playlist items:")
        for item in unavailable_entries:
            print(f"  - {item}")
    else:
        print("\nDeleted/private/unavailable playlist items: none detected in parsed entries.")

    if isinstance(reported_total, int) and reported_total > parsed_total:
        missing_count = reported_total - parsed_total
        print(
            f"  - {missing_count} playlist item(s) were reported by YouTube but not returned in the parsed entries."
        )
    print()


def build_mp3_playlist_options(
    output_template: str,
    audio_quality: str,
    cookies: str | None = None,
) -> dict[str, Any]:
    options: dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "ignoreerrors": True,
        "noplaylist": False,
        "quiet": False,
        "no_warnings": False,
        "windowsfilenames": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": audio_quality,
            }
        ],
    }
    if cookies:
        options["cookiefile"] = cookies
    return options


def download_playlist_as_mp3(
    YoutubeDL: Any,
    url: str,
    audio_quality: str,
    cookies: str | None = None,
) -> None:
    extract_options: dict[str, Any] = {
        "extract_flat": "in_playlist",
        "ignoreerrors": True,
        "quiet": True,
        "no_warnings": False,
        "noplaylist": False,
    }
    if cookies:
        extract_options["cookiefile"] = cookies

    with YoutubeDL(extract_options) as ydl:
        playlist_info = ydl.extract_info(url, download=False)

    if not playlist_info:
        raise RuntimeError("Could not read playlist information.")

    playlist_title = playlist_info.get("title") or "YouTube Playlist"
    playlist_folder = sanitize_folder_name(playlist_title)
    os.makedirs(playlist_folder, exist_ok=True)

    print_playlist_report(playlist_info, playlist_folder)

    output_template = os.path.join(
        playlist_folder,
        "%(playlist_index)03d - %(title)s [%(id)s].%(ext)s",
    )
    download_options = build_mp3_playlist_options(
        output_template,
        audio_quality,
        cookies,
    )
    print(f'Downloading playlist MP3 files into: "{playlist_folder}"')
    with YoutubeDL(download_options) as ydl:
        ydl.download([url])


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


def add_subtitle_options(
    options: dict[str, Any],
    write_subs: bool,
    write_auto_subs: bool,
    subtitles_only: bool,
    sub_langs: str,
    sub_format: str,
    convert_subs: str,
) -> dict[str, Any]:
    if not (write_subs or write_auto_subs or subtitles_only):
        return options

    subtitle_options = options.copy()
    subtitle_options.update(
        {
            "writesubtitles": write_subs or subtitles_only,
            "writeautomaticsub": write_auto_subs,
            "subtitleslangs": [
                lang.strip() for lang in sub_langs.split(",") if lang.strip()
            ],
            "subtitlesformat": sub_format,
        }
    )
    if convert_subs and convert_subs.lower() != "none":
        subtitle_options["postprocessors"] = [
            *subtitle_options.get("postprocessors", []),
            {
                "key": "FFmpegSubtitlesConvertor",
                "format": convert_subs,
                "when": "before_dl",
            },
        ]
    if subtitles_only:
        subtitle_options["skip_download"] = True
    return subtitle_options


def download_subtitles(
    YoutubeDL: Any,
    url: str,
    output_template: str,
    cookies: str | None = None,
    sub_langs: str = "en",
    sub_format: str = "srt/vtt/best",
    convert_subs: str = "srt",
    include_auto_subs: bool = True,
) -> None:
    subtitle_options = add_subtitle_options(
        {
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": False,
            "no_warnings": False,
        },
        write_subs=True,
        write_auto_subs=include_auto_subs,
        subtitles_only=True,
        sub_langs=sub_langs,
        sub_format=sub_format,
        convert_subs=convert_subs,
    )
    if cookies:
        subtitle_options["cookiefile"] = cookies

    with YoutubeDL(subtitle_options) as ydl:
        ydl.download([url])


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
        if (
            (args.write_subs or args.write_auto_subs or args.subtitles_only)
            and args.convert_subs.lower() != "none"
        ):
            print(
                "Warning: converting subtitles to srt requires ffmpeg.",
                file=sys.stderr,
            )
        if args.mp3_playlist:
            print(
                "MP3 playlist download requires ffmpeg to convert audio to mp3.",
                file=sys.stderr,
            )
            return 1

    cookies_file = args.cookies if os.path.exists(args.cookies) else None

    if args.mp3_playlist:
        try:
            download_playlist_as_mp3(
                YoutubeDL,
                url,
                args.audio_quality,
                cookies_file,
            )
        except Exception as exc:  # noqa: BLE001
            print(
                f"MP3 playlist download failed ({exc.__class__.__name__}): {exc}",
                file=sys.stderr,
            )
            return 1
        print("Playlist MP3 download complete.")
        return 0

    def make_ydl_options(
        cookies: str | None = None,
        fallback_mode: bool = False,
    ) -> dict[str, Any]:
        return add_subtitle_options(
            build_ydl_options(
                args.output,
                args.allow_lower_resolution,
                ffmpeg_available,
                cookies,
                fallback_mode=fallback_mode,
            ),
            args.write_subs,
            args.write_auto_subs,
            args.subtitles_only,
            args.sub_langs,
            args.sub_format,
            args.convert_subs,
        )

    ydl_opts = make_ydl_options(cookies_file)

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as exc:  # noqa: BLE001
        error_msg = str(exc)
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
                ydl_opts_with_cookies = make_ydl_options(cookies_file)
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
                            with YoutubeDL(
                                {**ydl_opts_with_cookies, "listformats": True}
                            ) as ydl:
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
                        ydl_opts_fallback = make_ydl_options(
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
                ydl_opts_fallback = make_ydl_options(fallback_mode=True)
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
            ydl_opts_with_cookies = make_ydl_options(cookies_file)
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
