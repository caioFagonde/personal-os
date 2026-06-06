# Personal OS Mobile

Thin Capacitor shell around the shared Quasar application in `apps/web`.

## Development

```bash
pnpm install
pnpm --dir apps/mobile validate
pnpm --dir apps/mobile cap:add:android
pnpm --dir apps/mobile cap:sync
pnpm --dir apps/mobile android:run
```

The app talks to the API gateway. In production, set `VITE_API_URL` to the Tailscale or LAN URL of the control plane and leave module/sync/command services behind the gateway proxy.
