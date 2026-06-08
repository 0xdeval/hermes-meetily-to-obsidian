---
name: hermes-meetily-to-obsidian
description: "Hermes skill to post-process Meetily / meetily-exporter meeting folders or markdown exports into structured Obsidian notes, deduplicate them, and clean up processed exports."
version: 0.2.0
author: 0xdeval + Mike Krupin
license: MIT
metadata:
  hermes:
    tags: [obsidian, meetily, meetily-exporter, meetings, automation, syncthing]
    related_skills: [hermes-agent-skill-authoring]
---

# hermes-meetily-to-obsidian

This Hermes skill post-processes Meetily exports from a Syncthing-synced export folder and writes structured meeting notes into Obsidian.

It is designed for the common Meetily export shape where each meeting is a directory containing `metadata.json` and `transcripts.json`.
It also supports a markdown-export fallback.

## Overview

The workflow is:

1. Meetily exports a meeting folder on your Mac.
2. Syncthing syncs that folder to the server.
3. Hermes processes the synced export on the server.
4. Hermes writes two notes into Obsidian:
   - `summary.md`
   - `raw.md`
5. The processed export is kept on the server by default so it can be reprocessed later.

Meetings are stored under:

`<VAULT>/Meetings/dd-mm-yyyy/<short-title>/`

## When to Use

- Meetily on macOS exports meeting folders or markdown files.
- The export folder is synced to a server with Syncthing.
- You want Hermes to normalize the meeting into Obsidian.
- You want processed exports cleaned up so the export inbox stays empty.

## Expected Export Shape

### Meetily folder export

A meeting folder should contain at least:

- `metadata.json`
- `transcripts.json`

The processor reads these files, builds a readable transcript, then writes Obsidian notes.

### Markdown export fallback

If the exporter writes a single markdown file instead, the processor will still ingest it.

## Output Layout in Obsidian

For each meeting:

- `summary.md` — Hermes-generated thematic summary without timestamps, grouped by topic, capped at 2000 characters and 280 words
- `raw.md` — full transcript text

Example:

```text
/root/Obsidian/Meetings/02-06-2026/Meeting 2026-06-02 16-29-27/
  summary.md
  raw.md
```

## Cleanup Behavior

Default behavior is to keep the processed export in the exporter folder.

You can also choose:
- `keep` — leave the source export in place
- `move` — move the source into `.processed/`
- `delete` — remove the source export after successful processing

## Common Pitfalls

1. **Pointing the exporter directly at the Obsidian vault.**
   Keep the Syncthing export inbox separate from the vault so you do not create sync loops.

2. **Processing partial files.**
   The processor waits for the export to be old enough and stable before handling it.

3. **Syncthing bookkeeping files being processed.**
   The script ignores `.stignore`, `.stfolder`, `.processed`, and hidden files.

4. **Expecting one source export to create multiple Obsidian notes.**
   This skill creates exactly one meeting folder per export.

5. **Thinking cleanup will delete the Mac copy.**
   If the server is the processing side, cleanup only removes the synced server copy unless you also build a Mac-side delete hook.

## Verification Checklist

- [ ] Syncthing export folder exists on the server
- [ ] Meetily export folders contain `metadata.json` and `transcripts.json`
- [ ] Obsidian receives `summary.md` and `raw.md`
- [ ] The processed server-side export is cleaned up
- [ ] Duplicates are skipped via the processed database

## Files

- `scripts/process_exporter.py` — main processor
- `templates/summary-template.md` — summary template
- `hermes-meetily-watcher.service` — sample systemd unit for the server
- `README.md` — usage notes
