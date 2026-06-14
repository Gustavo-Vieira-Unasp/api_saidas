# Phase 2: Mobile app

Planned native or cross-platform mobile client reusing the existing FastAPI backend.

## Goals

- Login with RA + UNASP password (same as web)
- Send exit now from saved templates
- View submission history and screenshots
- Push notifications when scheduled submissions fail

## API reuse

All endpoints documented in [API.md](API.md) are mobile-ready. JWT auth via bearer token.

## Out of scope (initial mobile release)

- Batch planning UI (web-only for now)
- Template weekly time editor (simplified mobile form first)

## Timeline

TBD — after Phase 1 web app is deployed and stable with test coverage.
