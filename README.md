# HYPERDESK

Prototype desktop app for linking devices on the same network and sharing a
session-scoped "hyperbox" directory with controlled permissions.

## Run (Windows)
1. Create a virtual environment:
   - `python -m venv .venv`
   - `.venv\Scripts\activate`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Start the app:
   - `python -m hyperdesk`
4. Use `Start Pairing` to generate a peer code.
5. Use `Sync Rules` to set mode + conflict policy.
6. Optional: set `HYPERDESK_CONTROL_HOST=0.0.0.0` to accept LAN peers (default).

## Run peer client (simulated)
1. Start the host app and click `Start Pairing` to display a code.
2. In another terminal, run:
   - `python -m hyperdesk.peer --host <HOST_IP> --pair-code 123456`
3. Optionally request a file:
   - `python -m hyperdesk.peer --host <HOST_IP> --pair-code 123456 --request "requests/sample.txt"`
4. Received files are saved to `peer_inbox/` (override with `--inbox`).

## Notes
- Discovery and pairing are simulated by default.
- Set `HYPERDESK_USE_MDNS=1` to enable zeroconf mDNS discovery.
- Control channel module is available via websockets and logs incoming events.
- Transfer engine is a local file copy PoC with checksum support.
- Hyperbox folder is watched for new files (requires `watchdog`).
- Transfer settings are stored in the preferences table and editable in the UI.
- Request queue UI supports approve/decline actions (simulated requests).
- Approving a request starts a transfer job and updates status on completion.
- Sync rules (mode + conflict) can be adjusted per session.
- Use the `Request Queue` dialog for filters/history.
- Transfer log footer shows active count, avg rate, and throttle utilization.
- Device presets let you save default sync rules per peer.
- Request queue can export filtered results to CSV.
- Session and audit metadata are stored in `data/hyperdesk.db`.
- Hyperbox files are stored in `hyperbox/`.

## Structure
```
hyperdesk/
  app.py
  core/
  network/
  transfer/
  ui/
```
