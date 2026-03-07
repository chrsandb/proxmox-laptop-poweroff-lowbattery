# Future Feature: Proxmox Battery UI Companion

## Summary
- Supported answer: no, this cannot currently be added to the built-in Proxmox node Summary page as a normal supported extension/plugin without changing Proxmox core UI code.
- Recommended supported path: build a companion battery status page outside the built-in Summary tab, backed by the existing battery monitor, with graph + estimated shutdown counter there.
- Priority: low.

## Research Notes
- Proxmox has backend plugin systems for some subsystems, but no generic supported web UI plugin API for arbitrary Summary-page widgets.
- Current Proxmox UI extension work is added case-by-case for specific domains rather than through a general drop-in frontend plugin model.
- The target host's installed `pve-manager` layout exposes normal web assets and backend modules, but no generic web UI extension directory or summary-widget registration hook.

## Supported Direction
- Extend the battery monitor backend to persist structured status and bounded history.
- Add a small companion read-only API for battery status and history.
- Add a separate lightweight web page with:
  - battery graph
  - estimated runtime / shutdown horizon
  - current battery and AC state
  - recent battery-monitor events
- Keep Proxmox itself unpatched and do not inject into the built-in Summary page.

## Possible Interfaces
- `GET /battery/status`
- `GET /battery/history`

Returned data should include:
- current battery percent
- AC online/offline
- battery status string
- low-battery armed state
- rolling battery history
- estimated remaining runtime when enough discharge data exists

## UI Behavior
- Show graph windows such as 1h / 6h / 24h.
- Only show ETA when on battery and enough stable samples exist.
- Show `estimating` or `insufficient history` when the estimate is not reliable.
- Show last update timestamp so operators can confirm freshness.

## Operational Constraints
- The battery shutdown logic must remain independent from the UI.
- The monitor must continue working even if the companion UI/API is down.
- No Proxmox package files should be modified.
- Proxmox upgrades should not depend on maintaining local web UI patches.

## Test Ideas
- Verify status endpoint on AC power and on battery power.
- Verify history retention and graph rendering with no, partial, and full data.
- Verify ETA suppression while charging or with insufficient history.
- Verify stale-data indication if sampling stops.
- Verify shutdown monitoring still works when the UI/API service is stopped.

## Assumptions
- “Supported only” means no modification of `pve-manager` JavaScript, templates, or packaged web assets.
- A separate host-side page is acceptable even though it is not embedded inside the built-in Summary tab.
- If true in-tab embedding is required later, that becomes an unsupported browser-extension or Proxmox-core-patch project.
