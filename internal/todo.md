# HYPERDESK To-Do

## Now
- [ ] Build host file index + client browser view
- [ ] Add client revoke UI for shared files
- [ ] Implement edit workflow (copy vs in-place)
- [ ] Build wireframe screens into a clickable prototype

## Soon
- [ ] OS integration: context menu "Send to HYPERDESK"
- [ ] Expand pairing to real handshake over control channel

## Done
- [x] Capture concept summary and initial wireframes
- [x] Define permission modes and conflict rules (mirror/copy/approval)
- [x] Decide MVP tech stack (Python + PySide6)
- [x] Draft data model for sessions, devices, and shared items
- [x] Draft implementation strategy
- [x] Place wireframes in internal folder
- [x] Create MVP repo structure and app shell
- [x] Prototype network discovery + pairing
- [x] Define control message schema (JSON events)
- [x] Implement transfer engine PoC (chunk + checksum)
- [x] Wire UI to live session state
- [x] Add real mDNS discovery (zeroconf) behind a feature flag
- [x] Implement websocket control channel using the message schema
- [x] Create local hyperbox folder + request queue model
- [x] Persist sessions and audit logs in SQLite
- [x] Build transfer log UI with live progress
- [x] Wire control channel to session events and UI
- [x] Add request queue UI with approve/deny actions
- [x] Implement file watcher for hyperbox changes
- [x] Add real pairing handshake + session token exchange
- [x] Create transfer settings UI and persist preferences
- [x] Implement hyperbox mapping to a local folder
- [x] Build request queue and transfer log UI
- [x] Add transfer engine with resume and checksum
- [x] Create basic security model (pairing key, session tokens)
- [x] Connect control channel to a real peer client
- [x] Tie request approvals to transfer jobs
- [x] Enforce transfer settings (bandwidth + retry policy)
- [x] Add file watcher rules for auto-sync modes
- [x] Build a dedicated request queue view with filters/history
- [x] Tie approvals to user-selected source files (file picker)
- [x] Implement peer-side transfer reception for real device testing
- [x] Enforce bandwidth policy with UI-visible throttling stats
- [x] Add per-session sync rules and conflict resolution UI
- [x] Add peer-side progress reporting back to host
- [x] Persist sync rule presets per device
- [x] Add request queue search by session/device
- [x] Expose bandwidth throttle stats in transfer log footer
- [x] Implement conflict resolution behavior for mirror mode
- [x] Add transfer integrity validation on peer (checksum ack)
- [x] Persist sync rule presets per device (UI for defaults)
- [x] Add request queue export to CSV
- [x] Add bandwidth utilization history chart
- [x] Build a simple peer UI for non-CLI testing
- [x] Add request queue export scheduling (auto archive)
- [x] Add bandwidth utilization history export
- [x] Implement conflict resolution behavior for mirror mode on receive side
- [x] Add transfer integrity validation on peer for inbound syncs
