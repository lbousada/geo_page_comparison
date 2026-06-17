#!/usr/bin/env python3
"""List local Screaming Frog crawls.

This script uses the Screaming Frog SEO Spider CLI for DB-mode crawls and also
looks for saved .seospider crawl files so real file sizes can be shown when
Screaming Frog stores the crawl as a file.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_WINDOWS_CLI_PATHS = (
    Path(r"C:\Program Files\Screaming Frog SEO Spider\ScreamingFrogSEOSpiderCli.exe"),
    Path(r"C:\Program Files (x86)\Screaming Frog SEO Spider\ScreamingFrogSEOSpiderCli.exe"),
)

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CrawlRow:
    name: str
    size: str
    source: str


def find_cli(explicit_path: str | None) -> Path:
    if explicit_path:
        path = Path(explicit_path).expanduser()
        if path.exists():
            return path
        raise FileNotFoundError(f"Screaming Frog CLI was not found at: {path}")

    from_path = shutil.which("ScreamingFrogSEOSpiderCli")
    if from_path:
        return Path(from_path)

    for path in DEFAULT_WINDOWS_CLI_PATHS:
        if path.exists():
            return path

    raise FileNotFoundError(
        "Could not find ScreamingFrogSEOSpiderCli. Pass --cli-path with the full path."
    )


def run_list_crawls(cli_path: Path) -> str:
    result = subprocess.run(
        [str(cli_path), "--headless", "--list-crawls"],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Screaming Frog CLI returned a non-zero exit code.\n\n"
            f"Exit code: {result.returncode}\n"
            f"Output:\n{result.stdout}"
        )
    return result.stdout


def parse_db_crawls(cli_output: str) -> list[CrawlRow]:
    crawls: list[CrawlRow] = []

    for line in cli_output.splitlines():
        if "║" not in line or "│" not in line:
            continue

        table_part = line.split("INFO  -", 1)[-1].strip()
        cells = [cell.strip() for cell in table_part.strip("║").split("│")]
        if len(cells) < 2:
            continue

        database_id, name = cells[0], cells[1]
        if not UUID_RE.match(database_id):
            continue

        crawls.append(
            CrawlRow(
                name=name or database_id,
                size="not exposed by SF CLI for DB-mode crawls",
                source="DB crawl",
            )
        )

    return crawls


def format_bytes(size: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def find_saved_crawl_files(search_paths: list[Path]) -> list[CrawlRow]:
    rows: list[CrawlRow] = []
    seen: set[Path] = set()

    for search_path in search_paths:
        if not search_path.exists():
            continue

        for root, _, filenames in os.walk(search_path, onerror=lambda _: None):
            for filename in filenames:
                if not filename.lower().endswith(".seospider"):
                    continue

                crawl_file = Path(root) / filename
                try:
                    resolved = crawl_file.resolve()
                except OSError:
                    continue
                if resolved in seen:
                    continue
                seen.add(resolved)

                try:
                    size = format_bytes(crawl_file.stat().st_size)
                except OSError:
                    size = "unavailable"

                rows.append(CrawlRow(name=crawl_file.name, size=size, source="saved file"))

    return sorted(rows, key=lambda row: row.name.lower())


def print_table(rows: list[CrawlRow]) -> None:
    if not rows:
        print("No Screaming Frog crawls found.")
        return

    headers = ("Crawl file/name", "File size", "Source")
    widths = [
        max(len(headers[0]), *(len(row.name) for row in rows)),
        max(len(headers[1]), *(len(row.size) for row in rows)),
        max(len(headers[2]), *(len(row.source) for row in rows)),
    ]

    print(f"{headers[0]:<{widths[0]}}  {headers[1]:<{widths[1]}}  {headers[2]}")
    print(f"{'-' * widths[0]}  {'-' * widths[1]}  {'-' * widths[2]}")

    for row in rows:
        print(f"{row.name:<{widths[0]}}  {row.size:<{widths[1]}}  {row.source}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List local Screaming Frog crawls.")
    parser.add_argument(
        "--cli-path",
        help="Full path to ScreamingFrogSEOSpiderCli.exe. Auto-detected on Windows.",
    )
    parser.add_argument(
        "--search-path",
        action="append",
        default=[],
        help=(
            "Folder to scan for .seospider files. Can be passed more than once. "
            "Defaults to your user profile."
        ),
    )
    parser.add_argument(
        "--skip-db-crawls",
        action="store_true",
        help="Only scan for saved .seospider files; do not call the Screaming Frog CLI.",
    )
    parser.add_argument(
        "--skip-file-scan",
        action="store_true",
        help="Only list DB-mode crawls from the Screaming Frog CLI.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows: list[CrawlRow] = []

    if not args.skip_db_crawls:
        try:
            cli_path = find_cli(args.cli_path)
            rows.extend(parse_db_crawls(run_list_crawls(cli_path)))
        except Exception as exc:
            print(f"Warning: could not list DB-mode crawls: {exc}", file=sys.stderr)

    if not args.skip_file_scan:
        if args.search_path:
            search_paths = [Path(path).expanduser() for path in args.search_path]
        else:
            search_paths = [Path(os.environ.get("USERPROFILE", str(Path.home())))]
        rows.extend(find_saved_crawl_files(search_paths))

    print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
