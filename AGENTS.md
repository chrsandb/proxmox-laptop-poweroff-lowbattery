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
- Submit new scripts to `community-scripts/DevScripts` for testing and review. Maintainers handle promotion to ProxmoxVE.
- Use `tools/pve/laptop-battery-shutdown.sh` and `json/laptop-battery-shutdown.json` for this host utility.
- Recheck the current upstream guidance before preparing a PR.
- Read [ProxmoxVE CONTRIBUTING.md](https://github.com/community-scripts/ProxmoxVE/blob/main/CONTRIBUTING.md), [DevScripts AGENTS.md](https://github.com/community-scripts/DevScripts/blob/main/AGENTS.md), its script-creator agent guidance, and the DevScripts PR template.
- Use `gh repo fork community-scripts/DevScripts`, create a feature branch in a separate checkout, and submit with `gh pr create`.
- Follow current `tools/pve` examples and the applicable host-tool guidance.
- DevScripts metadata belongs in `json/`. Put `config_path` inside the install method and include `repository`, `architectures`, and `platforms`.
- ProxmoxVE website metadata is managed through PocketBase and the website.
- Test the published entrypoint, install, update, status, removal, and battery decision logic before submission.
- Set `PVE_BATTERY_SCRIPT_URL` to the fork's raw script URL during fork testing. This URL is preserved by the installed manager for subsequent updates.
- Fill in the current PR template, including PVE Tool, actual platforms tested, and accurate AI-assistance details.
- The current new-script PR validation enforces the application eligibility checkboxes when New script is selected, including age, stars, and release tarballs. Document this host utility honestly and request maintainer guidance on the applicable criteria.

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
