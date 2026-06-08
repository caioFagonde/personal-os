You are the automatic QA repair node for Personal OS.

You are running inside an isolated git worktree.

Task:
Fix the concrete test/check failure below. Do not add broad new features. Do not perform unrelated refactors. Make the smallest correct change that satisfies the failing tests and preserves product intent.

Hard security rules:
- Do not read, print, modify, or commit .env, .env.*, secrets/, data/, backups/, logs/, credentials, tokens, OAuth secrets, private keys, or personal data.
- Do not weaken auth/security.
- Do not add arbitrary remote shell.
- Do not run destructive commands.
- Do not commit or push to remote.
- Do not hide test failures by deleting meaningful tests.
- If a test is wrong, update it only with a precise justification and maintain the intended invariant.

Failed command:
```bash
run_checks_raw
```

Failure output:
```text

===== Running checks =====
ss...................................................................... [ 27%]
........................................................................ [ 55%]
........................................................................ [ 83%]
...........................................                              [100%]
257 passed, 2 skipped in 0.98s
./.agents/reports/auto-repair-pre-merge-20260608-072820/report.md:51:The \`build-android-signed.sh\` was restructured to use a standard \`keystore.properties\` file (not inline \`-P\` flags) so it would not trip the \`check-secrets.sh\` \`password=\` regex.
./.agent-worktrees/auto-repair-pre-merge-20260608-072820/.agents/reports/auto-repair-pre-merge-20260608-072820/report.md:51:The \`build-android-signed.sh\` was restructured to use a standard \`keystore.properties\` file (not inline \`-P\` flags) so it would not trip the \`check-secrets.sh\` \`password=\` regex.
Potential secret detected. Move it to .env/local secret store, rotate it, then retry.

> @personal-os/web@0.7.0 build /home/caion/Documentos/github/personal-os-scaffold/personal-os/apps/web
> quasar build


 .d88888b.
d88P" "Y88b
888     888
888     888 888  888  8888b.  .d8888b   8888b.  888d888
888     888 888  888     "88b 88K          "88b 888P"
888 Y8b 888 888  888 .d888888 "Y8888b. .d888888 888
Y88b.Y8b88P Y88b 888 888  888      X88 888  888 888
 "Y888888"   "Y88888 "Y888888  88888P' "Y888888 888
       Y8b


 Build mode............. spa
 Pkg quasar............. v2.19.3
 Pkg @quasar/app-vite... v2.6.2
 Pkg vite............... v5.4.21
 Debugging.............. no
 Publishing............. no

 App • Using quasar.config.ts in "ts" format
 App •  WAIT  • Compiling of SPA UI with Vite in progress...
✗ Build failed in 392ms
Build failed with 1 error:

[plugin vite:vue] /home/caion/Documentos/github/personal-os-scaffold/personal-os/apps/web/src/pages/SettingsPage.vue:63:6
SyntaxError: [vue/compiler-sfc] Identifier 'serviceStatus' has already been declared. (63:6)

/home/caion/Documentos/github/personal-os-scaffold/personal-os/apps/web/src/pages/SettingsPage.vue
102|  ]
103|  
104|  const serviceStatus = ref<Record<string, string>>({})
   |        ^
105|  
106|  function saveLocalSettingsSnapshot() {
    at constructor (/home/caion/Documentos/github/personal-os-scaffold/personal-os/node_modules/.pnpm/@babel+parser@7.29.7/node_modules/@babel/parser/lib/index.js:365:19)
    at TypeScriptParserMixin.raise (/home/caion/Documentos/github/personal-os-scaffold/personal-os/node_modules/.pnpm/@babel+parser@7.29.7/node_modules/@babel/parser/lib/index.js:6616:19)
    at TypeScriptScopeHandler.checkRedeclarationInScope (/home/caion/Documentos/github/personal-os-scaffold/personal-os/node_modules/.pnpm/@babel+parser@7.29.7/node_modules/@babel/parser/lib/index.js:1619:19)
    at TypeScriptScopeHandler.declareName (/home/caion/Documentos/github/personal-os-scaffold/personal-os/node_modules/.pnpm/@babel+parser@7.29.7/node_modules/@babel/parser/lib/index.js:1585:12)
    at TypeScriptScopeHandler.declareName (/home/caion/Documentos/github/personal-os-scaffold/personal-os/node_modules/.pnpm/@babel+parser@7.29.7/node_modules/@babel/parser/lib/index.js:4892:11)
    at TypeScriptParserMixin.declareNameFromIdentifier (/home/caion/Documentos/github/personal-os-scaffold/personal-os/node_modules/.pnpm/@babel+parser@7.29.7/node_modules/@babel/parser/lib/index.js:7584:16)
    at TypeScriptParserMixin.checkIdentifier (/home/caion/Documentos/github/personal-os-scaffold/personal-os/node_modules/.pnpm/@babel+parser@7.29.7/node_modules/@babel/parser/lib/index.js:7580:12)
    at TypeScriptParserMixin.checkLVal (/home/caion/Documentos/github/personal-os-scaffold/personal-os/node_modules/.pnpm/@babel+parser@7.29.7/node_modules/@babel/parser/lib/index.js:7517:12)
    at TypeScriptParserMixin.parseVarId (/home/caion/Documentos/github/personal-os-scaffold/personal-os/node_modules/.pnpm/@babel+parser@7.29.7/node_modules/@babel/parser/lib/index.js:13429:10)
    at TypeScriptParserMixin.parseVarId (/home/caion/Documentos/github/personal-os-scaffold/personal-os/node_modules/.pnpm/@babel+parser@7.29.7/node_modules/@babel/parser/lib/index.js:9769:11)
    at aggregateBindingErrorsIntoJsError (file:///home/caion/Documentos/github/personal-os-scaffold/personal-os/node_modules/.pnpm/rolldown@1.0.3/node_modules/rolldown/dist/shared/error-BuvQYXuZ.mjs:48:18)
    at unwrapBindingResult (file:///home/caion/Documentos/github/personal-os-scaffold/personal-os/node_modules/.pnpm/rolldown@1.0.3/node_modules/rolldown/dist/shared/error-BuvQYXuZ.mjs:18:128)
    at #build (file:///home/caion/Documentos/github/personal-os-scaffold/personal-os/node_modules/.pnpm/rolldown@1.0.3/node_modules/rolldown/dist/shared/rolldown-build-CrPk_lZe.mjs:3246:34)
    at async buildEnvironment (file:///home/caion/Documentos/github/personal-os-scaffold/personal-os/node_modules/.pnpm/vite@8.0.16_@types+node@25.9.2_esbuild@0.27.7_sass-embedded@1.100.0_sass@1.100.0_terser@5.48.0/node_modules/vite/dist/node/chunks/node.js:33253:64)
    at async Object.build (file:///home/caion/Documentos/github/personal-os-scaffold/personal-os/node_modules/.pnpm/vite@8.0.16_@types+node@25.9.2_esbuild@0.27.7_sass-embedded@1.100.0_sass@1.100.0_terser@5.48.0/node_modules/vite/dist/node/chunks/node.js:33675:19)
    at async QuasarModeBuilder.buildWithVite (file:///home/caion/Documentos/github/personal-os-scaffold/personal-os/node_modules/.pnpm/@quasar+app-vite@2.6.2_@quasar+extras@1.18.0_@types+node@25.9.2_pinia@2.3.1_typescript@5.9.3__sjsw6mh42qzxksgbjdjduy2sai/node_modules/@quasar/app-vite/lib/app-tool.js:30:5)
    at async QuasarModeBuilder.build (file:///home/caion/Documentos/github/personal-os-scaffold/personal-os/node_modules/.pnpm/@quasar+app-vite@2.6.2_@quasar+extras@1.18.0_@types+node@25.9.2_pinia@2.3.1_typescript@5.9.3__sjsw6mh42qzxksgbjdjduy2sai/node_modules/@quasar/app-vite/lib/modes/spa/spa-builder.js:7:5) {
  errors: [Getter/Setter]
}

 App • ⚠️   FAIL  App build failed (check the log above)

 ELIFECYCLE  Command failed with exit code 1.
```

Current known failure examples may include:
- missing structured error constant such as optional_service_unavailable
- page missing expected visual class such as glass-card
- Settings page missing validation rules
- Settings page missing localStorage persistence contract
- Settings page missing serviceStatus/checkServices contract

Repair requirements:
1. Inspect only relevant files.
2. Fix the actual root cause.
3. Add or preserve tests.
4. Run the failing command again if possible.
5. Run:
   - scripts/agents/run-pytest.sh tests -q
   - ./scripts/check-secrets.sh
6. Write a report to:
   .agents/reports/auto-repair-pre-merge-20260608-083912/report.md

Report must include:
- root cause
- files changed
- tests run
- results
- remaining risks
