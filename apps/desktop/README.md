# Personal OS Desktop

Tauri shell around the shared Quasar application.

## Development

```bash
pnpm install
pnpm --dir apps/desktop validate
pnpm --dir apps/desktop dev
```

## Release build

```bash
pnpm --dir apps/desktop build
```

Tauri is the default desktop runtime because it keeps the desktop shell smaller and reduces the attack surface compared with bundling a complete Chromium runtime per app.
