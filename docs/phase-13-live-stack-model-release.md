# Phase 13 — Live-stack certification, model runtime, and release publishing

Phase 13 is the final architecture-certification layer for the initial Personal OS release. It does not add another domain module; it proves the existing system can run as a real product on a live stack, a physical Android device, and release pipelines.

## Delivered capabilities

- Live-stack Playwright tests against Docker services.
- Physical Android sync certification script with ADB authorization handoff.
- Dedicated model-runtime service for OCR, object detection, audio transcription, and fallback multimodal capture.
- Release-readiness gate.
- GitHub release publishing dry-run/real script.
- UI pages for model runtime, live-stack certification, and initial-version readiness.

## Commands

```bash
make up-model-runtime
make test-phase13
make certify-model-runtime
make certify-live-stack
make certify-physical-sync
make release-readiness
make publish-release
```

## Initial version completion gate

The initial version can be called complete when all of these pass with real infrastructure:

1. `./scripts/bootstrap.sh --full --open --certify` succeeds from a fresh clone.
2. GitHub Actions Phase 13 workflow passes.
3. Live-stack Playwright passes against Docker services.
4. Physical Android can pair, reverse ports, register a device, and create offline/synced data.
5. Connector sandbox tests pass for the configured providers.
6. Restore drill proves continuity after volume destruction.
7. Model runtime certifies fallback providers and any enabled external providers.
8. Signed release artifacts or explicit skip evidence exist.

After this point, further work is product refinement, not foundational architecture.
