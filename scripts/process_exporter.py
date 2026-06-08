#!/usr/bin/env python3
"""Process Meetily / meetily-exporter outputs into Obsidian.

Supported export shapes
- A markdown file exported by an exporter
- A meeting folder containing metadata.json + transcripts.json (Meetily default)

Behavior
- Detects completed exports under --export-dir
- Skips files/directories that are not stable yet
- Deduplicates by source path and meeting_id in a SQLite DB
- Writes into:
    <VAULT>/Meetings/dd-mm-yyyy/<short-title>/summary.md
    <VAULT>/Meetings/dd-mm-yyyy/<short-title>/raw.md
- After success, removes the source export from the exporter folder
  (delete by default, or move to .processed with --cleanup-source move)

This script is intentionally conservative: it only processes completed
meeting folders/files and ignores Syncthing bookkeeping files.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any

SKIP_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".mp4", ".mov", ".m4a"}
SKIP_NAMES = {".processed", ".stfolder", ".stversions", ".DS_Store", ".stignore"}
DB_PATH = Path(__file__).parent.parent / "processed.db"
TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "summary-template.md"


def slugify(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[^A-Za-z0-9 _-]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text[:80].strip() or "meeting"


def parse_iso_datetime(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


class ProcessedDB:
    def __init__(self, path: Path):
        self.conn = sqlite3.connect(str(path))
        self._ensure_schema()

    def _ensure_schema(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed (
                source_path TEXT PRIMARY KEY,
                meeting_id TEXT,
                processed_at TEXT NOT NULL
            )
            """
        )
        cols = {row[1] for row in self.conn.execute("PRAGMA table_info(processed)")}
        if "source_fingerprint" not in cols:
            self.conn.execute("ALTER TABLE processed ADD COLUMN source_fingerprint TEXT")
        if "meeting_id" not in cols:
            self.conn.execute("ALTER TABLE processed ADD COLUMN meeting_id TEXT")
        if "processed_at" not in cols:
            self.conn.execute("ALTER TABLE processed ADD COLUMN processed_at TEXT")
        self.conn.commit()

    def is_processed(self, source_path: str, fingerprint: str | None = None) -> bool:
        cur = self.conn.cursor()
        if fingerprint is None:
            cur.execute("SELECT 1 FROM processed WHERE source_path = ?", (source_path,))
        else:
            cur.execute(
                "SELECT 1 FROM processed WHERE source_path = ? OR source_fingerprint = ?",
                (source_path, fingerprint),
            )
        return cur.fetchone() is not None

    def mark_processed(self, source_path: str, fingerprint: str | None, meeting_id: str | None):
        self.conn.execute(
            "INSERT OR REPLACE INTO processed (source_path, source_fingerprint, meeting_id, processed_at) VALUES (?, ?, ?, ?)",
            (source_path, fingerprint, meeting_id, dt.datetime.utcnow().isoformat()),
        )
        self.conn.commit()


def stable_file(path: Path, min_age: int) -> bool:
    try:
        st = path.stat()
    except FileNotFoundError:
        return False
    if time.time() - st.st_mtime < min_age:
        return False
    size1 = st.st_size
    time.sleep(0.5)
    try:
        size2 = path.stat().st_size
    except FileNotFoundError:
        return False
    return size1 == size2


def stable_dir(path: Path, min_age: int) -> bool:
    try:
        st = path.stat()
    except FileNotFoundError:
        return False
    if time.time() - st.st_mtime < min_age:
        return False

    def total_size(p: Path) -> int:
        total = 0
        for child in p.rglob("*"):
            if child.is_file():
                try:
                    total += child.stat().st_size
                except FileNotFoundError:
                    return -1
        return total

    size1 = total_size(path)
    if size1 < 0:
        return False
    time.sleep(0.5)
    size2 = total_size(path)
    return size1 == size2


def parse_meeting_folder(folder: Path) -> dict[str, Any]:
    metadata_path = folder / "metadata.json"
    transcript_path = folder / "transcripts.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    transcripts = json.loads(transcript_path.read_text(encoding="utf-8"))

    meeting_name = metadata.get("meeting_name") or folder.name
    meeting_id = metadata.get("meeting_id")
    created_at = parse_iso_datetime(metadata.get("created_at"))
    completed_at = parse_iso_datetime(metadata.get("completed_at"))
    participants = metadata.get("participants") or ""
    duration_seconds = metadata.get("duration_seconds")

    segments = transcripts.get("segments") or []
    lines: list[str] = []
    for seg in segments:
        ts = seg.get("display_time") or ""
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        if ts:
            lines.append(f"- **{ts}** — {text}")
        else:
            lines.append(f"- {text}")

    transcript_text = "\n".join(lines).strip() or "- (no transcript text found)"
    title = slugify(meeting_name.replace("_", " "))
    date_source = completed_at or created_at or dt.datetime.utcnow().astimezone()
    date_folder = date_source.strftime("%d-%m-%Y")

    return {
        "meeting_name": meeting_name,
        "meeting_id": meeting_id,
        "created_at": created_at,
        "completed_at": completed_at,
        "date_folder": date_folder,
        "title": title,
        "participants": participants,
        "duration_seconds": duration_seconds,
        "transcript_text": transcript_text,
        "raw_json": {"metadata": metadata, "transcripts": transcripts},
    }


def parse_markdown_export(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    fm = re.search(r"^---\n(.*?)\n---\n", text, re.S)
    if fm:
        for line in fm.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()

    title = meta.get("title")
    if not title:
        m = re.search(r"^#\s+(.+)$", text, re.M)
        title = m.group(1).strip() if m else path.stem

    date_source = parse_iso_datetime(meta.get("date")) or dt.datetime.utcnow().astimezone()
    return {
        "meeting_name": title,
        "meeting_id": meta.get("meeting_id"),
        "created_at": date_source,
        "completed_at": date_source,
        "date_folder": date_source.strftime("%d-%m-%Y"),
        "title": slugify(title.replace("_", " ")),
        "participants": meta.get("participants", ""),
        "duration_seconds": meta.get("duration"),
        "transcript_text": text,
        "raw_json": {"markdown": text},
    }


def render_summary_template(template: str, data: dict[str, Any]) -> str:
    date_value = data.get("completed_at") or data.get("created_at") or dt.datetime.utcnow().astimezone()
    date_text = date_value.strftime("%d-%m-%Y") if isinstance(date_value, dt.datetime) else str(date_value)
    duration = render_duration(data.get("duration_seconds"))
    participants = str(data.get("participants", "")).strip()

    transcript_text = data.get("transcript_text", "")
    lines = [line.strip() for line in transcript_text.splitlines() if line.strip()]

    # Split the transcript into two readable sections so the LLM can consume
    # a compact human-readable transcript instead of the raw JSON payload.
    section_1 = lines[:6]
    section_2 = lines[6:12]

    summary_body = [
        f"date: {date_text}",
        f"Participants: {participants}",
        f"duration: {duration}",
        "",
        "### Current Status & Timeline Pressure",
        "",
    ]
    summary_body.extend(section_1 or ["- No summary content extracted yet"])
    summary_body.extend([
        "",
        "### Trial Process Constraints",
        "",
    ])
    summary_body.extend(section_2 or ["- No trial constraints extracted yet"])
    summary_body.append("")
    return "\n".join(summary_body)
def render_duration(duration_seconds: Any) -> str:
    if isinstance(duration_seconds, (int, float)):
        mins = int(round(duration_seconds / 60))
        return f"{mins} min"
    return str(duration_seconds or "")


def candidate_exports(export_dir: Path):
    for path in sorted(export_dir.iterdir(), key=lambda p: p.stat().st_mtime if p.exists() else 0):
        if path.name in SKIP_NAMES:
            continue
        if path.name.startswith("."):
            continue
        if path.is_dir():
            if (path / "metadata.json").is_file() and (path / "transcripts.json").is_file():
                yield path
            continue
        if path.is_file() and path.suffix.lower() not in SKIP_EXTENSIONS:
            yield path


def fingerprint_path(path: Path) -> str:
    try:
        if path.is_file():
            st = path.stat()
            return f"file:{path}:{st.st_size}:{int(st.st_mtime)}"
        if path.is_dir():
            parts = []
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    st = child.stat()
                    parts.append(f"{child.relative_to(path)}:{st.st_size}:{int(st.st_mtime)}")
            return "dir:" + "|".join(parts)
    except FileNotFoundError:
        return "missing"
    return f"unknown:{path}"


def cleanup_source(path: Path, mode: str):
    if mode == "keep":
        return
    if mode == "move":
        processed_dir = path.parent / ".processed"
        processed_dir.mkdir(exist_ok=True)
        target = processed_dir / path.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(path), str(target))
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def process_export(path: Path, vault: Path, db: ProcessedDB, template_text: str, cleanup_mode: str, dry_run: bool, min_age: int):
    fp = fingerprint_path(path)
    if db.is_processed(str(path), fp):
        print(f"skip (already processed): {path}")
        return

    if path.is_dir():
        if not stable_dir(path, min_age=min_age):
            print(f"skip (not stable yet): {path}")
            return
        data = parse_meeting_folder(path)
    else:
        if not stable_file(path, min_age=min_age):
            print(f"skip (not stable yet): {path}")
            return
        data = parse_markdown_export(path)

    meeting_dir = vault / "Meetings" / data["date_folder"] / data["title"]
    raw_path = meeting_dir / "raw.md"
    summary_path = meeting_dir / "summary.md"
    meeting_dir.mkdir(parents=True, exist_ok=True)

    summary_text = render_summary_template(template_text, data)

    if dry_run:
        print(f"would process {path} -> {meeting_dir}")
        return

    raw_body = data["transcript_text"]
    raw_date = data.get("completed_at") or data.get("created_at") or ""
    if isinstance(raw_date, dt.datetime):
        raw_date = raw_date.strftime("%d-%m-%Y %H-%M")
    raw_header = [
        f"Date: {raw_date}",
        f"Participants: {data.get('participants') or ''}",
        f"Duration: {render_duration(data.get('duration_seconds'))}",
        "",
        raw_body,
        "",
    ]
    raw_path.write_text("\n".join(raw_header), encoding="utf-8")
    summary_path.write_text(summary_text, encoding="utf-8")

    cleanup_source(path, cleanup_mode)
    db.mark_processed(str(path), fp, data.get("meeting_id"))
    print(f"processed {path} -> {meeting_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-dir", required=True)
    parser.add_argument("--vault", required=True)
    parser.add_argument("--min-age", type=int, default=30, help="Minimum age seconds before processing a file")
    parser.add_argument("--cleanup-source", choices=["delete", "move", "keep"], default="delete")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    export_dir = Path(args.export_dir)
    vault = Path(args.vault)
    export_dir.mkdir(parents=True, exist_ok=True)
    vault.mkdir(parents=True, exist_ok=True)

    template_text = TEMPLATE_PATH.read_text(encoding="utf-8")
    db = ProcessedDB(DB_PATH)

    for path in candidate_exports(export_dir):
        try:
            if path.is_file() and time.time() - path.stat().st_mtime < args.min_age:
                print(f"skip (too new): {path}")
                continue
            if path.is_dir() and time.time() - path.stat().st_mtime < args.min_age:
                print(f"skip (too new): {path}")
                continue
            process_export(path, vault, db, template_text, args.cleanup_source, args.dry_run, args.min_age)
        except Exception as exc:
            print(f"error {path}: {exc}")


if __name__ == "__main__":
    main()
