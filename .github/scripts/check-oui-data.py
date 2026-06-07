#!/usr/bin/env python3
"""Validate ARCMA embedded OUI data files."""

from pathlib import Path
import re
import sys


OUI_RE = re.compile(r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){2}$")
ROOT = Path(__file__).resolve().parents[2]
OUI_DIR = ROOT / "luci-app-arcma" / "root" / "usr" / "share" / "arcma" / "oui"


def main() -> int:
    errors = []

    for path in sorted(OUI_DIR.glob("*.txt")):
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            fields = raw.split("\t")
            if len(fields) != 2 or not fields[0].strip() or not fields[1].strip():
                errors.append(f"{path}:{lineno}: expected 'Vendor<TAB>OUI ...'")
                continue

            vendor = fields[0].strip()
            seen_in_vendor = set()
            for oui in fields[1].split():
                if not OUI_RE.match(oui):
                    errors.append(f"{path}:{lineno}: invalid OUI '{oui}'")
                    continue

                first_octet = int(oui[:2], 16)
                if first_octet & 0x01:
                    errors.append(f"{path}:{lineno}: multicast/group OUI '{oui}'")
                if first_octet & 0x02:
                    errors.append(f"{path}:{lineno}: local-admin OUI '{oui}'")

                key = oui.lower()
                if key in seen_in_vendor:
                    errors.append(f"{path}:{lineno}: duplicate OUI '{oui}' for {vendor}")
                seen_in_vendor.add(key)

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    print(f"Validated OUI data in {OUI_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
