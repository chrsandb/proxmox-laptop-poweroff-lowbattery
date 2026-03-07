# PVE Laptop Battery Shutdown Monitor

## Summary
Implement this as a host-side Proxmox tool, not a container/addon script.

Primary implementation:
- Add `tools/pve/laptop-battery-shutdown.sh` as the upstream-style interactive installer/remover/updater.
- Add `frontend/public/json/laptop-battery-shutdown.json` with `type: "pve"` so it fits the Community Scripts catalog.
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
  - AC source: first power-supply entry with `online`, prefer `AC`, overrideable via config

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
- `pve-battery-monitor.timer`: `OnBootSec=60s`, `OnUnitActiveSec=60s`, `Persistent=true`
- `Remove` disables/removes units, helper, config, and state file.

Public interfaces and defaults:
- User-facing entrypoint: `tools/pve/laptop-battery-shutdown.sh`
- Catalog metadata: `frontend/public/json/laptop-battery-shutdown.json`
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
1. Move these files into an actual `community-scripts/ProxmoxVE` fork, include user-facing documentation (`README.md` or equivalent), and test there with the normal curl entrypoint.
   Documentation should explain:
   - `10%` may be acceptable for a new battery in good health
   - `25%` is safer for weaker batteries like this laptop
   - BIOS/UEFI auto-start on AC restore and scheduled power-on tips

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
- Low priority: consider a separate Proxmox battery UI companion page with graphing and ETA, documented in [FUTURE_FEATURE_BATTERY_UI.md](/root/projects/labtools/proxmox-laptop-poweroff-lowbattery/FUTURE_FEATURE_BATTERY_UI.md). Keep this out of the built-in Proxmox Summary page unless Proxmox adds a supported web UI extension model.
