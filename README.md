# README — hermes-meetily-to-obsidian

This Hermes skill processes meetily-exporter (or similar) markdown exports into structured Obsidian meeting notes.

Install
- Clone this repo into your machine or place under ~/.hermes/skills/<category>/hermes-meetily-to-obsidian

Usage
- Run the processor:

  python3 scripts/process_exporter.py --export-dir /path/to/exporter --vault /root/Obsidian --move-processed

- Set up a cron job or Hermes cronjob to run periodically.

Configuration
- edit templates/summary-template.md to change the summary skeleton.

Publishing
- Push this repo to https://github.com/0xdeval/hermes-meetily-to-obsidian.git and then open a PR to hermeshub as you requested.
