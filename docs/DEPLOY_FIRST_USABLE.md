# Deploy — First Usable Version (PC + Phone over Tailscale)

This is the step-by-step to stand up Nexus Prime as a daily-driver second brain:
the full stack runs on your **PC**, your **phone** is a thin shell that loads the
live web UI over **Tailscale** (so web updates need no new APK), you can **read
PDFs and other artifacts stored on the PC from your phone**, and everything is
**backed up to Google Drive** with one command.

> Doctrine: never commit `.env`; secrets are generated locally by
> `scripts/generate-env.py`. All the OAuth/rclone auth below stays on your PC.

---

## 0. Prerequisites (PC)

- Docker Engine + Docker Compose v2 (`docker compose version`)
- `git`, `python3`
- Node ≥ 22 + `pnpm` (only needed to build the phone APK)
- [Tailscale](https://tailscale.com/) installed on both PC and phone, same tailnet
- For Google Drive backup: [`rclone`](https://rclone.org/) and the MinIO client
  [`mc`](https://min.io/docs/minio/linux/reference/minio-mc.html)

---

## 1. Bring up the stack on the PC

```bash
git clone <your-repo> nexus && cd nexus
./scripts/bootstrap.sh --full --open
```

This generates `.env`, creates runtime dirs, builds and starts all services,
runs migrations, seeds modules, and runs the health + auth smoke tests. First
run compiles images and can take a while.

**Turn on MinIO-backed artifacts** so files live in object storage (and are
therefore captured by the Drive backup). In `.env` set:

```env
STORAGE_BACKEND=minio
```

Then restart the sync-engine so it picks up the change:

```bash
docker compose --env-file .env up -d sync-engine
```

Verify: `docker compose --env-file .env ps` (all healthy) and open
`http://localhost:9000` (the web UI).

---

## 2. Join the PC to Tailscale and get its URL

```bash
sudo tailscale up          # authenticate in the browser it opens
tailscale status           # note this machine's name, e.g. nexus-pc
```

Your PC is now reachable on the tailnet. Two ways the phone can reach the web UI:

- **MagicDNS + HTTPS (recommended):** enable HTTPS certs in the Tailscale admin,
  then `sudo tailscale serve https / http://127.0.0.1:9000`. Your URL becomes
  `https://nexus-pc.<your-tailnet>.ts.net`.
- **Plain tailnet IP:** use `http://<100.x.y.z>:9000` (the `100.*` address from
  `tailscale status`). Works without certs; the app already allows cleartext to
  tailnet hosts.

Confirm from the phone's browser (with Tailscale connected) that the URL loads
the web UI before building the APK.

---

## 3. Build the phone app as a thin shell

The APK is now a shell that loads the **live** web UI from your PC. Set
`MOBILE_SERVER_URL` to the URL from step 2 and build:

```bash
export PATH="$HOME/.nvm/versions/node/v22.22.3/bin:$PATH"   # Node ≥22
pnpm install
pnpm --dir apps/web build                                    # build the SPA (bundled fallback)
export MOBILE_SERVER_URL="https://nexus-pc.<your-tailnet>.ts.net"   # or http://100.x.y.z:9000
cd apps/mobile
pnpm cap:add:android      # generates the native project (not committed)
# apply share-target + shortcuts fragment from android-share-target.xml (see file header)
pnpm cap:sync             # bakes MOBILE_SERVER_URL into the native config
npx cap open android      # build/run from Android Studio, or:
cd android && ./gradlew assembleDebug   # → app/build/outputs/apk/debug/app-debug.apk
```

Install `app-debug.apk` on your phone (adb, or copy it over). When Tailscale is
on, the app loads the live UI from your PC.

**Why this matters:** because the URL points at your PC, **shipping a web change
requires no new APK** — rebuild the web UI on the PC (`pnpm --dir apps/web build`
and restart `web`, or `docker compose ... up -d --build web`) and the phone picks
it up on next load. You only rebuild the APK for native changes (new plugins,
permissions, or a changed `MOBILE_SERVER_URL`).

> Leave `MOBILE_SERVER_URL` unset to build a fully-bundled offline APK instead.

---

## 4. Pair the phone as a trusted device

If `AUTH_REQUIRED=true` (recommended once you're past first setup), new devices
need a single-use pairing code:

1. On the PC web UI go to **Device Pairing** → *Create pairing code* (shows a QR).
2. On the phone, open the app → **Device Pairing** → *Register this device* and
   enter the code (or scan the QR).

The first device bootstraps without a code. See the pairing UI at `/device-pairing`.

---

## 5. Read PC files (PDFs/artifacts) from the phone

Any file attached to a capture, task, or note is stored in MinIO on the PC and
is now browsable from any paired device:

- Open **Files** in the app (also in the command palette → *Files*, or `/files`).
- Tap **Open** to view a PDF or image inline (streamed through the authenticated
  gateway — the phone never touches MinIO's internal host directly), or **Save**
  to download.

Encrypted attachments are not rendered inline (they're opaque here); download via
the sync client to decrypt.

---

## 6. One-command Google Drive backup (Postgres + MinIO + vault)

One-time setup on the PC (auth stays local — nothing lands in the repo):

```bash
# Let the backup capture MinIO artifacts:
mc alias set nexus http://127.0.0.1:${MINIO_API_PORT:-9010} "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
echo 'MINIO_ALIAS=nexus' >> .env

# Configure a Google Drive rclone remote named 'nexus-drive':
rclone config          # n) new → name it nexus-drive → Google Drive → follow OAuth
```

Then, any time you want a full off-box backup:

```bash
make backup-drive
# or: ./scripts/backup-to-drive.sh nexus-drive
```

This runs `backup-v2.sh` (Postgres `pg_dump -Fc` + MinIO artifacts + optional
Obsidian vault + config, sealed with a manifest) and then rclone-copies the
snapshot to Google Drive, verifying it with `rclone check`. It refuses to upload
an incomplete snapshot (no manifest = no upload).

Optional hardening (see `docs/backup.md` / `BACKUP_RESTORE_SPEC.md`):
`BACKUP_ENCRYPT=true` + `scripts/backup-keygen.sh` for age-encrypted snapshots,
and `make backup-verify SNAP=...` / `scripts/restore-drill.sh` for restore drills.

Schedule it (e.g. nightly) with cron on the PC:

```cron
30 2 * * *  cd /path/to/nexus && make backup-drive >> logs/backup-drive.log 2>&1
```

---

## Verify the whole loop

- PC: `docker compose --env-file .env ps` → services healthy; web UI opens.
- Phone (Tailscale on): app loads the live UI; **Files** lists a test PDF and
  opens it.
- `make backup-drive` completes and the snapshot appears in Drive under
  `NexusBackups/`.

## What's deliberately out of scope for this first version

- **Auto-APK-per-release + in-app updater** — not needed while the shell is thin
  (web changes are instant). Only build a new APK for native changes. The
  building blocks for a signed-APK OTA channel exist (`build_channel`/`app_version`
  on devices, `scripts/release/build-android-signed.sh`) if you later want it.
- **Packaged desktop installer (MSI/deb/AppImage)** — the Tauri shell builds on
  Linux CI today but is unsigned and doesn't manage the Docker stack. Use the
  browser on the PC for now; the desktop shell is optional.
