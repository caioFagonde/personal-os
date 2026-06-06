# Phase 12 — Real-device E2E and release certification

Phase 12 turns the project from a broad scaffold into a certifiable daily-driver system. It adds browser E2E, Android emulator/USB-device certification, optional live connector sandbox tests, signed release build scripts, and release/continuity UI surfaces.

## Local certification

```bash
./scripts/certify/full-local.sh
```

This runs Python tests, secret scans, compile checks, Compose config validation when Docker is available, frontend tests when pnpm is available, and Tauri Rust tests when Cargo is available.

## Browser E2E

```bash
pnpm install --frozen-lockfile=false
pnpm exec playwright install --with-deps chromium
pnpm --dir apps/web build
python3 scripts/ci/spa-server.py --root apps/web/dist/spa --port 9000
E2E_BASE_URL=http://127.0.0.1:9000 pnpm exec playwright test
```

## Android emulator certification

GitHub Actions runs emulator certification through `reactivecircus/android-emulator-runner`. Locally, start an emulator first, then run:

```bash
./scripts/certify/android-emulator.sh
```

## Physical Android certification

```bash
./scripts/certify/physical-android.sh
```

The script starts `adb`, waits for an authorized USB device, configures `adb reverse` for API/web ports, builds the APK, and installs it. If Android shows an RSA authorization prompt, accept it on the phone; the script waits until authorization succeeds or times out.

## Live connector sandbox tests

These are intentionally opt-in because they call external services.

```bash
RUN_LIVE_CONNECTOR_TESTS=true ./scripts/certify/live-connectors.sh
```

Use `TWILIO_LIVE_SEND=true` only when you explicitly want to send a real sandbox WhatsApp message.

## Signed Android release

Secrets:

```bash
export ANDROID_KEYSTORE_BASE64=...
export ANDROID_KEY_ALIAS=...
export ANDROID_KEYSTORE_PASSWORD=...
export ANDROID_KEY_PASSWORD=...
./scripts/release/build-android-signed.sh
```

If secrets are absent, the script still builds an unsigned release artifact so the pipeline remains useful on forks.

## Signed Tauri release

```bash
export TAURI_SIGNING_PRIVATE_KEY=...
export TAURI_SIGNING_PRIVATE_KEY_PASSWORD=...
./scripts/release/build-tauri-signed.sh
```

If signing secrets are absent, the script builds an unsigned desktop bundle.

## UI surfaces

- `/certification` — certification matrix and commands.
- `/release-center` — release artifacts, backup export, and remote-backup upload controls.
- `/offline-queue` — mobile/desktop offline mutation queue.
- `/conflicts` — sync conflict inspection and resolution.
- `/connector-worker` — outbox worker status and manual tick controls.

## CI jobs

`phase12-certification-release.yml` runs:

- browser E2E across desktop/mobile viewport projects;
- Android emulator install/launch check;
- optional live connector sandbox tests on manual dispatch;
- restore-drill certification;
- Android/Tauri release artifact build;
- scaffold contract checks.

## Known limits

Some tasks cannot be silent by design. Android USB RSA approval, Tailscale account/device approval, Google/Microsoft OAuth consent, phone notification permissions, and Twilio sandbox recipient joining require a human authorization step. The install/certification scripts detect these states, open or prompt where feasible, and then continue once authorization is complete.
