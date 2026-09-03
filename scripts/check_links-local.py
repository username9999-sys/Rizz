#!/usr/bin/env python3
"""
Local-only link checker.

Validates relative .md links in markdown files. Faster and offline
compared to scripts/check_links.py which hits the network for every
external URL.

Usage:
    python3 scripts/check-links-local.py
    python3 scripts/check-links-local.py --external   # also report external URLs (no HEAD)
"""

import os
import re
import sys
import argparse
from pathlib import Path


def find_markdown_files(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        # skip noise
        dirnames[:] = [
            d for d in dirnames
            if d not in (".git", "node_modules", "__pycache__", ".venv", "venv", "htmlcov")
        ]
        for fn in filenames:
            if fn.endswith(".md"):
                out.append(os.path.join(dirpath, fn))
    return out


# Match markdown links more carefully:
#   [text](url)   — url may contain balanced parens only if escaped
# Also matches image syntax: ![alt](url)
MD_LINK_RE = re.compile(r'!?\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
# Also bare URLs (for external reporting)
BARE_URL_RE = re.compile(r'(?<![\(\[])(https?://[^\s<>"\)\]]+)')


def check_file(md_path, root, report_external=False):
    """Return list of broken-link descriptions for this file."""
    issues = []
    try:
        content = Path(md_path).read_text(encoding="utf-8")
    except Exception as e:
        return [(md_path, "<file>", f"read error: {e}")]

    # Find markdown links
    for match in MD_LINK_RE.finditer(content):
        url = match.group(1)
        # Skip anchors and external schemes
        if url.startswith("#"):
            continue
        if url.startswith(("http://", "https://", "mailto:", "tel:")):
            if report_external:
                # Just note the external URL — we don't ping the network
                pass
            continue
        # Resolve relative to file's directory
        target = os.path.normpath(
            os.path.join(os.path.dirname(md_path), url.split("#")[0])
        )
        if not os.path.exists(target):
            # Suggest closest match for typo correction
            suggestions = suggest(target, root)
            hint = f"  (closest: {suggestions})" if suggestions else ""
            issues.append((md_path, url, f"NOT FOUND: {target}{hint}"))

    # Find bare external URLs (report only)
    if report_external:
        for match in BARE_URL_RE.finditer(content):
            url = match.group(1)
            # strip trailing punctuation that isn't part of the URL
            url = url.rstrip(".,;:!?")

    return issues


def suggest(target, root, max_n=3):
    """Find close matches to target under root."""
    if not os.path.isabs(target):
        return ""
    target_parts = target.split(os.sep)
    target_name = target_parts[-1]
    candidates = []
    for dirpath, _, filenames in os.walk(root):
        dirnames_filtered = [
            d for d in os.listdir(dirpath)
            if os.path.isdir(os.path.join(dirpath, d))
            and d not in (".git", "node_modules", "__pycache__")
        ] if os.path.isdir(dirpath) else []
        for fn in filenames + dirnames_filtered:
            full = os.path.join(dirpath, fn)
            if target_name.lower() in fn.lower():
                rel = os.path.relpath(full, root)
                candidates.append(rel)
                if len(candidates) >= max_n:
                    return ", ".join(candidates)
    return ", ".join(candidates) if candidates else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="project root (default: cwd)")
    ap.add_argument("--external", action="store_true", help="report external URLs too")
    args = ap.parse_args()

    md_files = find_markdown_files(args.root)
    if not md_files:
        print("No markdown files found.")
        return 1

    all_issues = []
    for f in md_files:
        all_issues.extend(check_file(f, args.root, report_external=args.external))

    print(f"Scanned {len(md_files)} markdown files in {args.root}")
    if all_issues:
        print(f"\n{len(all_issues)} broken relative link(s):\n")
        for path, url, msg in all_issues:
            print(f"  {path}")
            print(f"    -> {url}")
            print(f"    {msg}\n")
        return 1

    print("OK: all relative .md links resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
