# HYPERDESK Implementation Strategy

## Goals
- Fast, safe, local-network device linking for file sharing.
- Clear permission modes with user-approved push options.
- Low-friction UX that feels like a native file explorer feature.
- Reliable transfers with resume and audit history.

## Non-goals (MVP)
- Internet relay or WAN traversal.
- Multi-tenant cloud accounts or hosted storage.
- Full filesystem virtualization across OSes.

## MVP stack decision
- Language: Python 3.12
- UI: PySide6 (Qt)
- Networking: asyncio + websockets
- Storage: SQLite for sessions/logs
- Packaging: PyInstaller (Windows first)

## System architecture (MVP)
1. UI layer (Qt):
   - Scan, link, permissions, request queue, transfer log, session dashboard.
2. Core service:
   - Session state, policy evaluation, transfer orchestration.
3. Network discovery:
   - mDNS service advertising and discovery on LAN.
4. Link and auth:
   - Pairing code, session tokens, per-session permissions.
5. Hyperbox:
   - Local folder that mirrors shared items and requests.
6. Transfer engine:
   - Chunked, resumable transfers + checksums.
7. File watcher:
   - Track changes, generate requests, queue transfers.

## Data model (initial)
- Device: id, name, ip, capabilities, last_seen
- Session: id, host_device_id, peer_device_id, status, token, created_at
- ShareItem: id, session_id, path, mode, permissions
- PermissionPolicy: id, session_id, mode, approval_required
- TransferJob: id, session_id, path, direction, status, progress
- AuditEvent: id, session_id, event_type, details, timestamp

## Permission modes (behavior)
- Mirror: bidirectional sync; conflict resolution = keep both with suffix.
- Copy: one-way push from host to peer; no reverse changes.
- Approval: peer requests changes; host approves per file or batch.

## Protocol outline
1. Discovery (mDNS): announce service and capabilities.
2. Pairing: host displays code, peer confirms.
3. Handshake: exchange device info and session token.
4. Control channel: JSON control messages over websocket.
5. Data channel: chunked binary transfers with checksum.

## Security baseline
- TLS on local transport where possible.
- Session tokens scoped to a single session.
- Approval mode enforces push gating on host.
- Audit log for requests and transfers.

## Implementation milestones
M0: Spec and UX definitions
M1: Discovery + pairing + session state
M2: Transfer engine + hyperbox sync
M3: UI screens + request queue + log
M4: OS integration + packaging

## Success criteria (MVP)
- Two devices link reliably in under 10 seconds on LAN.
- Transfers resume after interruption.
- Approval mode prevents unapproved writes.
- Hyperbox reflects shared items within 2 seconds of change.

## Next concrete steps
Completed:
1. MVP repository structure and app shell.
2. Simulated discovery + pairing prototype.
3. Transfer engine PoC (chunk + checksum).
4. UI wired to live session state.
5. Added zeroconf mDNS discovery behind `HYPERDESK_USE_MDNS`.
6. Implemented websocket control channel module using the message schema.
7. Created local hyperbox folder and request queue model.
8. Persisted sessions, devices, audit events, and transfers in SQLite.
9. Built transfer log UI with live progress updates.
10. Wired control channel to session events and UI.
11. Added request queue UI with approve/deny actions.
12. Implemented hyperbox file watcher.
13. Added pairing handshake and session tokens.
14. Added transfer settings UI and persistent preferences.
15. Connected control channel to a peer client for end-to-end messaging.
16. Tied request approvals to transfer jobs.
17. Enforced transfer settings (bandwidth + retry policy).
18. Added auto-sync rules for file watcher events.
19. Added request queue dialog with filters and history view.
20. Tied approvals to user-selected source files (file picker).
21. Implemented peer-side file reception via transfer offers.
22. Added UI-visible transfer rate stats.
23. Added per-session sync rules and conflict resolution UI.
24. Added request queue search by session/device.
25. Added transfer log footer stats (active + utilization).
26. Added peer-to-host transfer progress updates.
27. Persisted sync rule presets per device.
28. Implemented mirror-mode conflict handling on transfer.
29. Added request queue CSV export and device preset UI.
30. Added bandwidth history chart dialog.
31. Added checksum ack validation for peer transfers.
32. Added unified host/client UI with pairing offers and confirmations.
33. Added session configuration presets and client connection panel.
34. Added request export scheduling and bandwidth history export.

Next:
1. Build host file index and client browser view.
2. Add client revoke UI for shared files.
3. Implement edit workflow (copy vs in-place).
4. Add basic peer-side file browser and metadata view.
5. Add approval flow for client edits with diff preview.
