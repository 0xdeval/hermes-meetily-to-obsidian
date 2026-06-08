---
name: hermes-meetily-to-obsidian
description: "Hermes skill to post-process Meetily/meetily-exporter markdown exports into structured Obsidian meeting notes (summary + raw transcript), deduplicate, and move processed exports into the Meetings folder."
version: 0.1.0
author: 0xdeval + Mike Krupin
license: MIT
tags: [obsidian, meetily, meetily-exporter, exporter, meetings, automation]
---

# hermes-meetily-to-obsidian

This Hermes skill watches a directory used by the meetily-exporter (or other local exporter), post-processes each meeting export, generates a short summary (filling a template), writes two markdown files into the Obsidian vault under Meetings/dd-mm--yyyy/<meeting-title>/, and removes the original exporter file to avoid duplicates.

Features
- Deduplication by exporter filename and meeting ID
- Generates `summary.md` and `raw_transcript.md` per meeting
- Uses a simple template for the summary (templates/summary-template.md)
- Moves processed exports into a `.processed` subfolder (or deletes them) per your preference

Usage
- Place exported meeting markdown files into the exporter folder (configurable)
- Run `scripts/process_exporter.py --export-dir /path/to/exporter --vault /root/Obsidian` or install as a cron job

Files
- SKILL.md (this file)
- scripts/process_exporter.py — main processing script
- templates/summary-template.md — summary template for notes
- README.md — install & usage notes

Design decisions
- Meetings are stored under: <VAULT>/Meetings/dd-mm--yyyy/<short-title>/
- Each meeting folder contains:
  - summary.md — generated summary that matches the template
  - raw_transcript.md — full raw transcript

Publishing
- This repo is intended to be published in your GitHub (you provided https://github.com/0xdeval/hermes-meetily-to-obsidian.git)
- After confirming the repo push, I can open a PR to hermeshub as you requested (requires push permissions or a fork/PR flow).
