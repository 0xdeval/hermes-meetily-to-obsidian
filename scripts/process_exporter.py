#!/usr/bin/env python3
"""
Process exported meetily markdown files into Obsidian meetings folder.

- For each markdown file in the exporter folder:
  - Parse metadata: title, date, participants, meeting_id if present
  - Extract raw transcript and notes
  - Generate a short title (e.g. 'Interview with Constructor')
  - Render the summary template using the transcript + notes
  - Create folder: <VAULT>/Meetings/dd-mm--yyyy/<short-title>/
  - Write summary.md and raw_transcript.md
  - Move or delete original exporter file to avoid duplicates

"""

import argparse
import datetime
import os
import re
import shutil
import sys
from pathlib import Path

SKIP_EXTENSIONS = {'.png', '.jpg', '.webp', '.svg'}


def slugify(s: str) -> str:
    s = s.strip()
    s = re.sub(r"[^A-Za-z0-9 _-]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s[:80]


def parse_export_markdown(path: Path) -> dict:
    text = path.read_text(encoding='utf-8')
    # naive extraction
    meta = {}
    # try frontmatter
    fm = re.search(r"^---\n(.*?)\n---\n", text, re.S)
    if fm:
        for line in fm.group(1).splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                meta[k.strip()] = v.strip()
    # fallback title
    m = re.search(r"^#\s+(.+)$", text, re.M)
    if m and 'title' not in meta:
        meta['title'] = m.group(1).strip()
    # find transcript section
    trans = ''
    m = re.search(r"(?s)##+\s*Transcript\s*(?:\n|:)(.*?)(?:\n## |\Z)", text)
    if m:
        trans = m.group(1).strip()
    else:
        # try to take everything after 'Transcript' word
        m2 = re.search(r"(?s)Transcript[:\n](.*)$", text)
        if m2:
            trans = m2.group(1).strip()
    meta['transcript'] = trans
    meta['raw'] = text
    return meta


def render_summary_template(template: str, meta: dict) -> str:
    tpl = template
    replacements = {
        '{{title}}': meta.get('title', 'Meeting'),
        '{{date}}': meta.get('date', datetime.datetime.utcnow().strftime('%d-%m--%Y')),
        '{{participants}}': meta.get('participants', ''),
        '{{duration}}': meta.get('duration', ''),
        '{{tldr}}': '',
        '{{key_points}}': '',
        '{{action_items}}': '',
        '{{notes}}': meta.get('transcript', '')[:4000],
    }
    for k, v in replacements.items():
        tpl = tpl.replace(k, v)
    return tpl


def process_file(path: Path, vault: Path, template_text: str, move_processed=True):
    meta = parse_export_markdown(path)
    title = meta.get('title') or path.stem
    short_title = slugify(title)
    # date
    date = meta.get('date')
    if date:
        try:
            # try parse common formats
            dd = datetime.datetime.fromisoformat(date)
            date_folder = dd.strftime('%d-%m--%Y')
        except Exception:
            date_folder = datetime.datetime.utcnow().strftime('%d-%m--%Y')
    else:
        date_folder = datetime.datetime.utcnow().strftime('%d-%m--%Y')

    meeting_dir = vault / 'Meetings' / date_folder / short_title
    meeting_dir.mkdir(parents=True, exist_ok=True)

    # write raw transcript
    raw_path = meeting_dir / 'raw_transcript.md'
    raw_path.write_text(meta.get('raw', ''), encoding='utf-8')

    # render summary (placeholder: we will call Hermes LLM or local summarizer)
    summary_text = render_summary_template(template_text, meta)
    summary_path = meeting_dir / 'summary.md'
    summary_path.write_text(summary_text, encoding='utf-8')

    # move or delete original
    if move_processed:
        processed_dir = path.parent / '.processed'
        processed_dir.mkdir(exist_ok=True)
        shutil.move(str(path), str(processed_dir / path.name))
    else:
        path.unlink()

    return str(meeting_dir)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--export-dir', required=True)
    p.add_argument('--vault', required=True)
    p.add_argument('--move-processed', action='store_true')
    args = p.parse_args()

    export_dir = Path(args.export_dir)
    vault = Path(args.vault)

    template_path = Path(__file__).parent.parent / 'templates' / 'summary-template.md'
    template_text = template_path.read_text(encoding='utf-8')

    for f in export_dir.iterdir():
        if f.is_file() and f.suffix.lower() not in SKIP_EXTENSIONS:
            try:
                meeting_dir = process_file(f, vault, template_text, move_processed=args.move_processed)
                print('processed', f, '->', meeting_dir)
            except Exception as e:
                print('error', f, e)


if __name__ == '__main__':
    main()
