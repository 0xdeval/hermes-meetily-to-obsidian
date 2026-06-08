# Hermes Meetily → Obsidian

Turn Meetily exports into structured Obsidian meeting notes with Hermes.

This repository packages a reusable Hermes skill plus a processor script for taking Meetily meeting exports, generating a compact summary, and writing canonical notes into an Obsidian vault.

## What it does

- asks the right **topology question first**:
  - are Meetily, Obsidian, and Hermes on the same machine?
- supports both:
  - **same-machine** setups
  - **split-machine** setups with Syncthing
- ingests real Meetily-style exports:
  - `metadata.json`
  - `transcripts.json`
- writes one canonical meeting folder in Obsidian containing:
  - `summary.md`
  - `raw.md`
- generates compact summaries capped at:
  - **280 words**
  - **2000 characters**
- avoids duplicates with a small SQLite processed database
- supports `keep`, `move`, or `delete` cleanup modes for processed exports
- includes guidance for readiness checks before calling the setup complete

## Repository contents

- `SKILL.md` — the main Hermes skill document
- `scripts/process_exporter.py` — processor for Meetily exports
- `templates/summary-template.md` — summary template used by the processor
- `references/exporter-format.md` — supported input shapes
- `references/syncthing-setup.md` — split-machine sync setup guide
- `references/testing-guide.md` — verification and troubleshooting checklist
- `hermes-meetily-watcher.service` — example systemd service
- `hermes-meetily-watcher.timer` — example systemd timer

## Supported setup modes

### 1) Same machine

Use this when Meetily, Obsidian, and Hermes all run locally.

Typical flow:
1. Export meetings locally from Meetily.
2. Run the processor against the local export folder.
3. Write meeting notes directly into the local Obsidian vault.

Syncthing is optional in this mode.

### 2) Split machine

Use this when Meetily runs on one machine and Hermes + Obsidian run on another.

Typical flow:
1. Meetily exports to a user-device folder.
2. Syncthing sends the export folder to the processing server.
3. Hermes processes exports on the server.
4. Obsidian notes are written into the server-side vault.

See:
- `references/syncthing-setup.md`
- `references/testing-guide.md`

## Output layout

Meetings are written to:

```text
<VAULT>/Meetings/dd-mm-yyyy/<short-title>/
  summary.md
  raw.md
```

## Quick start

Run manually:

```bash
python3 scripts/process_exporter.py \
  --export-dir /root/meetily_exports \
  --vault /root/Obsidian \
  --cleanup-source keep
```

Useful options:
- `--dry-run` — preview what would be processed
- `--reprocess-all` — rebuild notes from already-seen exports
- `--cleanup-source keep` — keep source exports
- `--cleanup-source move` — move exports into `.processed/`
- `--cleanup-source delete` — remove source exports after success

## Expected input

### Preferred input
A Meetily meeting folder containing:
- `metadata.json`
- `transcripts.json`

### Fallback input
A markdown export with frontmatter plus transcript text.

See `references/exporter-format.md` for details.

## Readiness checklist

Before declaring the workflow ready, verify:

- topology was identified correctly
- Meetily is installed or producing exports
- Hermes is callable on the processing machine
- the Obsidian vault path exists and is writable
- if split-machine: Syncthing is installed and healthy on both sides
- the processor runs successfully
- scheduler/timer/cron is healthy if automation is expected
- there are no unresolved sync or processing errors in logs/status output

## Notes

- This repository is focused on **post-processing and storage**, not live meeting recording.
- The processor ignores Syncthing bookkeeping files such as `.stignore`, `.stfolder`, and `.processed/`.
- The summary is meant to be a real thematic synthesis, not a transcript dump.
- `processed.db` is intentionally ignored by git because it is runtime state.

## License

MIT
