# PVE Laptop Battery Shutdown Monitor

## Summary
Implement this as a host-side Proxmox tool, not a container/addon script.

Primary implementation:
- Add `tools/pve/laptop-battery-shutdown.sh` as the upstream-style interactive installer/remover/updater.
- Add `json/laptop-battery-shutdown.json` with `type: "pve"` so it fits the Community Scripts catalog.
- Generate host files at install time:
  - `/usr/local/bin/pve-battery-monitor-check`
  - `/usr/local/bin/pve-battery-monitor-manage`
  - `/usr/local/bin/update_pve_battery_monitor`
  - `/usr/local/bin/uninstall_pve_battery_monitor`
  - `/usr/local/lib/pve-battery-monitor/laptop-battery-shutdown.sh`
  - `/etc/default/pve-battery-monitor`
  - `/etc/systemd/system/pve-battery-monitor.service`
  - `/etc/systemd/system/pve-battery-monitor.timer`
  - `/var/lib/pve-battery-monitor/state`

Why this approach:
- Matches the upstream `tools/pve/*.sh` pattern.
- Uses only tools already present on the target host: `bash`, `systemd`, `logger`, `whiptail`.
- Avoids extra dependencies and avoids hardcoding any machine-specific data.

Alternative approaches to document in the script header or PR description:
- `upower`-based: cleaner battery abstraction, but adds package/runtime dependency.
- `acpi`-based: simple CLI output, but less structured and not necessary here.
- `udev`/event-driven: lower polling overhead, but more brittle and harder to reason about for upstream v1.
- Recommended for v1: pure Bash + `systemd` timer.

## Key Changes
Behavior and flow:
- Installer script presents `Install`, `Update`, `Remove`, and `Status` actions via `whiptail` to match existing `tools/pve` UX.
- `Install` verifies:
  - running on Proxmox VE major version `>= 8`
  - at least one battery exists under `/sys/class/power_supply/BAT*`
  - `systemd` is available
- Script auto-detects runtime devices:
  - battery: first `BAT*`, overrideable via config
- AC availability: aggregate system-scoped external supplies, including USB-C. `AC_DEVICE` selects a preferred reporting label.

Generated config interface:
- `/etc/default/pve-battery-monitor` contains only generic defaults, no host data baked into repo:
  - `BATTERY_DEVICE=""`
  - `AC_DEVICE=""`
  - `LOW_CAPACITY_PERCENT=10`
  - `CHECK_INTERVAL_SECONDS=60`
  - `DRY_RUN=0`
- Documentation guidance should state:
  - `25%` is a safer threshold for older batteries or batteries with unstable low-end reporting
  - `10%` can be acceptable for a new battery in good health with predictable discharge behavior
- Repo does not contain:
  - host IP addresses
  - hostnames
  - battery model/serial
  - any local SSH or node identifiers

Check algorithm:
- Timer runs every 60 seconds.
- Check script reads `/sys/class/power_supply/<battery>/uevent` and AC `online`.
- Each run emits one compact decision line in the service journal, including `eta=...` when available.
- ETA is estimated from `POWER_SUPPLY_POWER_NOW` when available, with fallback to recent discharge slope from the previous battery sample.
- Shutdown path only qualifies when:
  - AC is offline
  - battery capacity is `<= LOW_CAPACITY_PERCENT`
  - current sample is still low on the next check and capacity did not increase
- First qualifying low sample:
  - log warning to journald via `logger`
  - mark state as `armed`
  - do not shut down yet
- Second consecutive qualifying low sample:
  - run `shutdown -h now "Low battery on Proxmox host"`
- Any recovery condition clears the armed state:
  - AC returns
  - capacity rises above threshold
  - capacity increases between checks
  - battery disappears or cannot be read

Systemd units:
- `pve-battery-monitor.service`: simple service running `/usr/local/bin/pve-battery-monitor-check`
- `pve-battery-monitor.timer`: `OnBootSec=60s`, `OnUnitActiveSec=60s`, `AccuracySec=1s`
- `Remove` disables/removes units, helpers, and state files. The configuration is retained.

Public interfaces and defaults:
- User-facing entrypoint: `tools/pve/laptop-battery-shutdown.sh`
- Catalog metadata: `json/laptop-battery-shutdown.json`
- Host admin interface: `/etc/default/pve-battery-monitor`
- Installed management entrypoint: `/usr/local/bin/pve-battery-monitor-manage`
- Test interface: `DRY_RUN=1` prevents actual shutdown and logs the command instead

## Test Plan
Safe validation:
- Install with `DRY_RUN=1` and confirm timer/service enable cleanly.
- Run the check script manually and confirm journald output.
- Verify `Status` shows detected battery, AC source, current capacity, armed state, and timer status.

Behavior scenarios:
- No battery present: installer exits with clear message and does not install units.
- Proxmox version below 8: installer refuses to proceed.
- Battery above threshold: no warning, no armed state.
- Battery below 10% with AC online: no armed state, no shutdown.
- First low offline sample: warning logged, armed state created.
- Second consecutive low offline sample: shutdown command invoked, or logged only in `DRY_RUN=1`.
- Power returns before second sample: armed state cleared.
- Capacity rises before second sample: armed state cleared.
- `BAT0` missing but another `BAT*` exists: autodetect still works.
- Generated repo files contain no node-specific IP, hostname, battery serial, or other local identifiers.
- Runtime tuning note:
  - validate low-end battery behavior on real hardware before trusting a `10%` threshold
  - if the battery gauge collapses near the bottom, raise `LOW_CAPACITY_PERCENT` to `25%` or `30%`

## Assumptions
- v1 relies on normal Proxmox/systemd host shutdown behavior to stop guests cleanly; it does not implement custom `qm shutdown` / `pct shutdown` orchestration.
- `Not charging` while AC is online must not trigger shutdown; AC `online` is authoritative.
- Upstream submission target is a `tools/pve` script plus JSON metadata, not a `ct/` or `tools/addon/` contribution.
- Generic defaults are committed; actual host configuration is created only on the installed machine.
- The repository default can remain `10%`, but operator documentation should clearly recommend validating battery health and raising the live threshold on aging hardware.

## Next Steps
1. Track [DevScripts PR #2630](https://github.com/community-scripts/DevScripts/pull/2630), respond to review feedback, and obtain maintainer review of the host-tool eligibility question.
2. Follow the DevScripts testing and promotion process after acceptance.

## Operational Tips
- Document that laptop recovery after low-battery shutdown is usually controlled in BIOS/UEFI, not by Proxmox.
- Recommend enabling automatic power-on when external power is re-attached. Common firmware names include:
  - `Restore on AC Power Loss`
  - `Power On AC Attach`
  - `AC Power Recovery`
- Recommend enabling scheduled automatic power-on via BIOS/UEFI RTC wake or power-on alarm.
- Scheduled power-on is especially useful when the battery is weak and the laptop may need additional charging time before it can boot successfully after shutdown.
- Documentation should note that exact firmware option names vary by laptop vendor and model.

## Future Features
- Low priority: consider a separate Proxmox battery UI companion page with graphing and ETA, documented in [FUTURE_FEATURE_BATTERY_UI.md](FUTURE_FEATURE_BATTERY_UI.md). Keep this out of the built-in Proxmox Summary page unless Proxmox adds a supported web UI extension model.

## Contribution Preparation
- Author attribution is `Christian Sandberg (chrsandb)`, with an MIT license in `LICENSE`.
- Installation requires a readable AC indicator returning `0` or `1`, with `AC_DEVICE` configuration guidance on failure.
- Generated scripts are staged and syntax-checked before per-file atomic replacement. Downloads and telemetry have time limits.
- New scripts enter through DevScripts, with metadata in `json/` for its PocketBase workflow.
- The installer supports curl/bash launches and downloads updates from `PVE_BATTERY_SCRIPT_URL`, defaulting to this project's published script.
- Confirmation requires samples from the same boot and devices, no more than three check intervals apart.
- Run `python3 -m unittest discover -s tests -v`, ShellCheck, shfmt, Bash syntax checks, and JSON validation before submission.
- Prepare a focused DevScripts PR with published-entrypoint test results and an accurate AI-assistance disclosure. Flag the application eligibility checklist's applicability to this host utility in the PR for maintainer review.
- Follow the current contribution references recorded in `AGENTS.md`, including the JSON template's three-note limit and behavior-focused description.

## Validation Completed
- 2026-11-13, commit `7101292` published to the standalone repository.
- All 18 isolated regression tests passed, along with ShellCheck, shfmt, Bash syntax, JSON validation, and staged sensitive-data checks.
- Tested on Proxmox VE 9.2, amd64, with AC power connected and `DRY_RUN=1`.
- The published curl entrypoint, installed status command, update wrapper, uninstall wrapper, and reinstallation passed.
- The installed source matched the published script, and generated units passed `systemd-analyze verify`.
- The enabled timer automatically triggered another successful check after configuration restoration.
- Existing configuration was preserved through install, update, and removal, then restored after testing. Rollback files and detailed test logs were retained outside the repository.
- Proxmox VE 8 compatibility and a new physical low-battery shutdown test remain unverified for this revision.

## Upstream Submission
- Opened [DevScripts PR #2630](https://github.com/community-scripts/DevScripts/pull/2630) from `chrsandb/DevScripts`, branch `feat/laptop-battery-shutdown`, on 2026-11-13.
- The contribution contains the host script and matching JSON metadata. Its default download URL targets DevScripts for automatic rewriting during promotion.
- All 19 regression tests passed on the revised standalone and contribution scripts. The added regression verifies that curl/bash launches retain the supplied source.
- The fork's install, status, update, removal, reinstallation, configuration preservation, and systemd validation passed on Proxmox VE 9.2 amd64 with `DRY_RUN=1` and AC connected.
- Verified the fork's curl/bash entrypoint without a source-URL override, using a revision query to bypass raw-content caching. The original standalone installation and configuration were restored afterward.
- The PR discloses AI assistance and unverified platforms and shutdown testing. The release-artifact requirement is checked after publishing `v0.1.0`. The stars requirement remains unchecked, with an exception and `keep-open` requested for maintainer assessment under the seven-day stale policy.

## First Release
- Published [v0.1.0](https://github.com/chrsandb/proxmox-laptop-poweroff-lowbattery/releases/tag/v0.1.0) from commit `455f9badb5c34359121aa1406addb8d4a399f782` on 2026-11-13.
- Release assets include a versioned source tarball containing the installer, README, MIT license, metadata, and tests, plus `SHA256SUMS`.
- All 19 tests passed from the extracted archive. The published archive was downloaded and checksum-verified.
- Updated DevScripts PR #2630 and requested an exception to the stars threshold and a maintainer-applied `keep-open` label.

## Codex Review Fixes
- Aggregate external power across system-scoped supplies, including USB-C. Any online adapter prevents shutdown; uncertain readings clear confirmation when all other adapters report offline.
- Treat `AC_DEVICE` as a preferred reporting label and exclude battery and device-scoped peripheral supplies from adapter detection.
- Set `AccuracySec=1s` so short polling intervals remain compatible with the three-interval confirmation freshness window.
- All 26 regression tests passed, including the reported charge-based USB-C case, invalid supply readings, peripheral exclusion, and five-second timer configuration with systemd verification.
- The release-artifact criterion is satisfied by `v0.1.1`, which includes these fixes. A maintainer decision on the stars exception remains pending.

## Patch Release
- Published [v0.1.1](https://github.com/chrsandb/proxmox-laptop-poweroff-lowbattery/releases/tag/v0.1.1) from commit `9f1236d25b776e355886b95a3a78ec2604c95164` with the external-power aggregation and timer-accuracy fixes.
- All 26 tests and static checks passed from the extracted source archive. The uploaded archive was downloaded and verified against `SHA256SUMS`.
- Marked `v0.1.1` as the latest release and updated the upstream PR's release-artifact reference.
