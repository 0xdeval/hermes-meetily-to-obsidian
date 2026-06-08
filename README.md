# hermes-meetily-to-obsidian

Process Meetily exports from a Syncthing-synced inbox into structured Obsidian meeting notes.

## Flow

1. Meetily exports a meeting folder on your Mac.
2. Syncthing syncs that folder to the server inbox.
3. Hermes processes the synced export on the server.
4. Hermes writes:
   - `summary.md`
   - `raw.md`
5. The source export is removed from the server inbox after successful processing.

## Supported export shape

### Meetily folder export

A folder containing:
- `metadata.json`
- `transcripts.json`

### Markdown fallback

A single markdown file with frontmatter and a transcript section.

## Server paths used in this setup

- Syncthing inbox: `/root/meetily_exports`
- Obsidian vault: `/root/Obsidian`
- Output: `/root/Obsidian/Meetings/dd-mm-yyyy/<meeting-title>/`

## Processor

Run manually:

```bash
python3 scripts/process_exporter.py \
  --export-dir /root/meetily_exports \
  --vault /root/Obsidian \
  --cleanup-source delete
```

Useful options:
- `--dry-run` — preview what would be processed
- `--cleanup-source move` — move processed exports into `.processed/`
- `--cleanup-source keep` — leave the source export in place

## Notes

- The processor ignores `.stignore`, `.stfolder`, hidden files, and `.processed/`.
- The processor uses a small SQLite DB (`processed.db`) to skip duplicates.
- The included `hermes-meetily-watcher.service` is a sample systemd unit for running it as a service on the server.
