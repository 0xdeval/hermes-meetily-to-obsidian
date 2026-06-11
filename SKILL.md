---
name: hermes-meetily-to-obsidian
description: "Use when Meetily exports should be post-processed into structured Obsidian meeting notes with topology-aware setup, deduplication, summary generation, and readiness checks."
version: 0.4.0
author: 0xdeval + Mike Krupin
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [obsidian, meetily, meetily-exporter, meetings, automation, syncthing]
    related_skills: [hermes-agent-skill-authoring, hermes-agent]
---

# hermes-meetily-to-obsidian

This Hermes skill post-processes Meetily exports from a Syncthing-synced export folder and writes structured meeting notes into Obsidian.

It is designed for the common Meetily export shape where each meeting is a directory containing `metadata.json` and `transcripts.json`.
It also supports a markdown-export fallback.

## Overview

Start with one required question:

- Are Meetily, Obsidian, and Hermes running on the same machine?

The workflow then branches:

### Same machine

1. Install or verify Meetily, Obsidian, and Hermes on that machine.
2. Configure a local Meetily export folder.
3. Run the processor against the local Obsidian vault.
4. Skip Syncthing unless the user explicitly wants multi-device vault sync.

### Separate machines

1. Install Meetily on the user machine that produces the meeting exports.
2. Install Syncthing on that user machine.
3. Install or verify Syncthing on the Hermes/Obsidian server.
4. Syncthing syncs the export folder to the server inbox.
5. Hermes processes the synced export on the server.
6. Hermes writes two notes into Obsidian:
   - `summary.md`
   - `raw.md`
7. The processed export is kept on the server by default so it can be reprocessed later.

Meetings are stored under:

`<VAULT>/Meetings/dd-mm-yyyy/<short-title>/`

## When to Use

- Meetily exports meeting folders or markdown files.
- Hermes should normalize the meeting into Obsidian.
- The setup may be same-machine or split-machine.
- If split-machine, the export folder is synced to a server with Syncthing.
- You want the skill to verify service readiness before declaring setup complete.

Do not use for:
- live meeting recording itself
- direct Meetily internal database integration
- workflows that need multiple note formats from a single export at once

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

- `summary.md` — Hermes-generated thematic summary with exact `Overview / Topics / Next steps` structure, semantic topic titles, preserved markdown line breaks, emphasis on material details, and at least 3 bullets per topic when the transcript supports it
- `raw.md` — full merged transcript text plus compact metadata such as semantic title, source meeting name, date, duration, and exporter status

Example:

```text
/root/Obsidian/Meetings/02-06-2026/Meeting 2026-06-02 16-29-27/
  summary.md
  raw.md
```

## Common Pitfalls

1. **Pointing the exporter directly at the Obsidian vault.**
   Keep the Syncthing export inbox separate from the vault so you do not create sync loops.

2. **Processing partial files or incomplete meetings.**
   The processor must wait for the export to be old enough, stable, and marked completed in metadata before handling it.

3. **Using the raw metadata timestamp as the Obsidian meeting title.**
   The final note title should be inferred semantically from the conversation topic, with participant names included when they are clear.

4. **Flattening markdown summaries into a single line.**
   Any post-processing that joins words with spaces will break Obsidian rendering and turn headings/bullets into one block.

5. **Creating thin topic sections with only 1-2 bullets.**
   Prefer fewer, stronger topics; merge weak themes into neighboring sections unless the transcript truly contains only sparse information.

6. **Syncthing bookkeeping files being processed.**
   The script ignores `.stignore`, `.stfolder`, `.processed`, and hidden files.

7. **Expecting one source export to create multiple Obsidian notes.**
   This skill creates exactly one meeting folder per export.

8. **Thinking cleanup will delete the Mac copy.**
   If the server is the processing side, cleanup only removes the synced server copy unless you also build a Mac-side delete hook.

## Verification Checklist

Always finish with a readiness check before telling the user the setup is done.

- [ ] Asked whether Meetily, Obsidian, and Hermes are on the same machine
- [ ] If same-machine: Meetily, Obsidian, and Hermes are installed and usable locally
- [ ] If split-machine: Syncthing is installed on the user device and on the Hermes/Obsidian server
- [ ] If split-machine: Syncthing services/processes are running and the shared folder is healthy
- [ ] Server export folder exists and is writable
- [ ] Obsidian vault exists and receives `summary.md` and `raw.md`
- [ ] Meetily export folders contain `metadata.json` and `transcripts.json`
- [ ] Meeting folders are processed only after metadata shows completion
- [ ] Output title is semantic and topic-based, not just the exporter timestamp name
- [ ] Summary uses exact `Overview / Topics / Next steps` structure with preserved markdown line breaks
- [ ] Topic sections contain 3+ bullets when the transcript provides enough detail
- [ ] Duplicates are skipped or reprocessed correctly via source fingerprint changes
- [ ] Scheduler/service is running without current errors
- [ ] No current sync or processor issues remain in logs/status output

## Cleanup Behavior

Default behavior is to keep the processed export in the exporter folder.

You can also choose:
- `keep` — leave the source export in place
- `move` — move the source into `.processed/`
- `delete` — remove the source export after successful processing

## References

- `references/exporter-format.md` — supported input shapes
- `references/syncthing-setup.md` — split-machine Syncthing setup guide
- `references/testing-guide.md` — final verification and troubleshooting checklist

## Files

- `scripts/process_exporter.py` — main processor
- `templates/summary-template.md` — summary template
- `references/exporter-format.md` — export-shape notes
- `references/syncthing-setup.md` — sync setup guide
- `references/testing-guide.md` — readiness checklist
- `hermes-meetily-watcher.service` — sample systemd unit for the server
- `README.md` — usage notes
