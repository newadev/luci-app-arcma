#!/usr/bin/env python3
"""Resolve OpenWrt Stable, Old Stable and Snapshot build matrix."""

import argparse
import json
import re
import sys
import urllib.request


DOWNLOADS_URL = "https://downloads.openwrt.org/"
TARGET = "x86/64"


def extract_version(html, section):
    match = re.search(
        rf"{re.escape(section)}.*?OpenWrt\s+([0-9]+\.[0-9]+\.[0-9]+)",
        html,
        re.DOTALL,
    )
    if not match:
        raise RuntimeError(f"Unable to resolve {section} from {DOWNLOADS_URL}")
    return match.group(1)


def package_ext(version):
    major = int(version.split(".", 1)[0])
    return "apk" if major >= 25 else "ipk"


def install_command(ext):
    if ext == "apk":
        return "apk add --allow-untrusted *.apk"
    return "opkg install *.ipk"


def release_track(track, label, version):
    ext = package_ext(version)
    slug = label.lower().replace(" ", "-")
    return {
        "track": track,
        "openwrt_version": version,
        "openwrt_label": f"OpenWrt {label} {version}",
        "sdk_url": f"https://downloads.openwrt.org/releases/{version}/targets/{TARGET}",
        "package_ext": ext,
        "install_command": install_command(ext),
        "artifact_name": f"arcma-openwrt-{slug}-{version}-{ext}",
    }


def resolve_matrix(html):
    stable = extract_version(html, "Stable Release")
    old_stable = extract_version(html, "Old Stable Release")

    return {
        "include": [
            release_track("stable", "Stable", stable),
            release_track("old-stable", "Old Stable", old_stable),
            {
                "track": "snapshots",
                "openwrt_version": "snapshots",
                "openwrt_label": "OpenWrt Development Snapshots",
                "sdk_url": f"https://downloads.openwrt.org/snapshots/targets/{TARGET}",
                "package_ext": "apk",
                "install_command": "apk add --allow-untrusted *.apk",
                "artifact_name": "arcma-openwrt-development-snapshots-apk",
            },
        ]
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--github-output", action="store_true")
    parser.add_argument("--html-file")
    args = parser.parse_args()

    if args.html_file:
        with open(args.html_file, encoding="utf-8") as handle:
            html = handle.read()
    else:
        html = urllib.request.urlopen(DOWNLOADS_URL, timeout=30).read().decode("utf-8", "replace")

    matrix = json.dumps(resolve_matrix(html), separators=(",", ":"))
    if args.github_output:
        print(f"matrix={matrix}")
    else:
        print(matrix)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"resolve-openwrt-matrix: {exc}", file=sys.stderr)
        raise SystemExit(1)
