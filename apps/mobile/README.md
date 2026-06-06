# Mobile shell

Mobile uses the Quasar/Capacitor mode from `apps/web`. Keep module UI shared where possible. Device-only capabilities such as notifications, camera, GPS, and sensors should be isolated in typed Capacitor adapters under `packages/sync-client` and `packages/event-client`.
