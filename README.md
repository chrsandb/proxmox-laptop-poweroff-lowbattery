# Proxmox Laptop Battery Shutdown

Host-side battery monitoring for Proxmox VE running on laptop hardware.

## What It Does
- Monitors `/sys/class/power_supply/BAT*/uevent`
- Detects whether AC power is online
- Logs one compact status line per run to the `pve-battery-monitor.service` journal
- Arms shutdown on the first low-battery sample
- Shuts the host down on the next low-battery sample if the battery is still below the configured threshold and not recovering

## Runtime Files
- `tools/pve/laptop-battery-shutdown.sh`
- `/etc/default/pve-battery-monitor`
- `/usr/local/bin/pve-battery-monitor-check`
- `/usr/local/bin/pve-battery-monitor-manage`

## Important Config
Configuration lives in:

```bash
/etc/default/pve-battery-monitor
```

Key values:

```bash
BATTERY_DEVICE=""
AC_DEVICE=""
LOW_CAPACITY_PERCENT=10
CHECK_INTERVAL_SECONDS=60
DRY_RUN=0
```

## Threshold Guidance
- `10%` can be acceptable for a new battery in good health with predictable discharge behavior.
- `25%` is safer for older batteries or batteries with unstable low-end reporting.
- `30%` may be a better choice if the battery gauge collapses rapidly near the bottom.

## Logging
Useful commands:

```bash
journalctl -u pve-battery-monitor.service -o cat
```

```bash
/usr/local/bin/pve-battery-monitor-manage status
```

Example status line:

```text
result=ok action=none battery=BAT0 ac=AC:offline capacity=97% status=Discharging armed=0 eta=01h47m detail=above-threshold
```

## Operational Tips
Recovery after low-battery shutdown is usually controlled by laptop firmware, not Proxmox.

Recommended BIOS/UEFI settings:
- enable automatic power-on when AC power is re-attached
- enable scheduled power-on via RTC wake or power-on alarm

Common firmware option names:
- `Restore on AC Power Loss`
- `Power On AC Attach`
- `AC Power Recovery`

Scheduled power-on is useful when the battery is weak and the laptop may need extra charging time before it can boot reliably.

## Upstream Submission Notes
For a `community-scripts/ProxmoxVE` submission, documentation should include:
- threshold guidance for new vs aging batteries
- note that live threshold may need to be raised on weak batteries
- BIOS/UEFI auto-start recommendations after shutdown
