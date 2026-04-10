# API Quick Reference

## Core Endpoints
- `GET /session` returns whether a session is active.
- `GET /sessions` returns recent session records.
- `GET /session/start/<label>` creates a new session using the supplied label.
- `GET /session/stop/` stops the current session.
- `POST /send/<dest>` sends a dashboard message payload.

## Recommended Validation Flow
- Query `GET /session` first.
- If the system is idle, use `GET /session/start/<label>`.
- Post a message to `POST /send/misc` so operators see the action.
- Confirm records appear in `GET /sessions`.

## Notes
- The Info page includes an API Explorer so this reference and live checks stay together.
- When `VITE_USE_MOCK_API=true`, requests use the built-in mock handlers.
