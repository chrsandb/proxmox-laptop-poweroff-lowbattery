# AGENTS.md

## Purpose
This repository contains a host-side Proxmox VE battery shutdown tool intended for eventual publication and upstream submission. Treat the repository as publishable by default.

## Repository Rules
- Keep committed content generic and reusable.
- Do not commit host-specific operational data.
- Do not commit secrets, credentials, internal IPs, hostnames, SSH details, local battery identifiers, or live deployment state.
- Do not commit files generated on a specific Proxmox host unless they are intentionally generic templates.

## GitHub Workflow
- For future GitHub interactions, use `gh`, not direct browser-only workflows.
- Use `gh auth status` to verify authentication before GitHub operations.
- Use `gh repo create`, `gh repo fork`, `gh pr create`, `gh issue create`, and `gh release` commands as needed.
- Prefer non-interactive `gh` commands where possible.

## Upstream Submission Workflow
- The intended upstream target is `community-scripts/ProxmoxVE`.
- Submit this project as a `tools/pve` contribution, not as a `ct/` container script or a Proxmox UI/plugin change.
- The expected upstream file pair is:
  - `tools/pve/laptop-battery-shutdown.sh`
  - `frontend/public/json/laptop-battery-shutdown.json`
- Before preparing an upstream PR, check the current upstream guidance:
  - `docs/contribution/README.md`
  - `docs/tools/README.md`
  - one or more current `tools/pve/*.sh` examples
  - one or more current `frontend/public/json/*.json` entries with `\"type\": \"pve\"`
- Prefer this workflow for upstream contribution:
  - `gh repo fork community-scripts/ProxmoxVE`
  - clone the fork locally
  - run `bash docs/contribution/setup-fork.sh --full`
  - create a feature branch
  - copy in the tool script and matching JSON metadata
  - test from the fork, including the raw GitHub delivery path if relevant
  - open the PR with `gh pr create`
- Keep the contribution aligned with existing `tools/pve` conventions:
  - `#!/usr/bin/env bash`
  - host-side Proxmox tool behavior
  - minimal, catalog-friendly JSON metadata
  - no assumptions that this belongs in `/ct`, `/install`, or Proxmox web UI code
- Treat `documentation` and `website` fields in JSON as review-sensitive. Upstream may prefer links that fit their ecosystem better than a standalone repo homepage.

## Sensitive Data Policy
Never commit any of the following:
- internal IP addresses
- hostnames
- SSH targets such as `root@...`
- battery model names, serial numbers, or raw hardware inventory tied to one machine
- live thresholds chosen only for one local host
- runtime logs, shell history, screenshots, or temporary investigation notes
- generated files from `/etc`, `/var`, `/usr/local`, or other live host paths

If a fact is useful but environment-specific, move it to a local-only ignored file instead of tracked documentation.

## Local-Only Files
Use ignored files for local operational notes:
- `LOCAL_*.md`
- `*.local`
- `.env`
- `.env.*`

Keep local deployment notes, host tuning, and test observations there.

## Documentation Rules
- Tracked docs must describe defaults, guidance, and safe recommendations generically.
- If documentation mentions tuning, phrase it as guidance:
  - example: `25% may be safer for older batteries`
  - avoid: `this host uses 25%`
- Avoid documenting live environment state in tracked files.

## Pre-Commit Review Checklist
Before committing:
- search for internal IPs:
  - `rg -n "10\\.|192\\.168\\.|172\\.(1[6-9]|2[0-9]|3[0-1])\\." .`
- search for hostnames and SSH targets:
  - `rg -n "root@|@pam|pve[0-9]|hostname|known_hosts" .`
- search for hardware identifiers:
  - `rg -n "SERIAL_NUMBER|MODEL_NAME|MANUFACTURER|POWER_SUPPLY_" .`
- review staged files only:
  - `git diff --cached --stat`
  - `git diff --cached`

If a staged change contains environment-only data, unstage it and move it to an ignored local file.

## Implementation Guidance
- Keep the repository default config conservative but generic.
- Put host-specific runtime changes in `/etc/default/pve-battery-monitor` on the target machine, not in tracked repo files.
- Prefer additive documentation and generic examples over recorded local history.

## Git Hygiene
- Initialize and use git in this workspace.
- Track source files, documentation, and metadata only.
- Ignore local notes, ad hoc exports, logs, secrets, and editor-specific files.
- Do not commit unless the working tree has been reviewed for local-only data.
