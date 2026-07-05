import { configure } from 'quasar/wrappers'

export default configure(() => ({
  boot: ['localdb'],
  // nexus-crt.scss is the GREEN GLASS theme layer (docs/DESIGN_LANGUAGE.md R2).
  // It must load after app.scss so it overrides the shared classes without
  // touching them (phase-14 contract strings in app.scss stay intact).
  css: ['app.scss', 'nexus-dark.scss', 'big-picture.scss', 'nexus-crt.scss'],
  extras: ['mdi-v7'],
  framework: {
    iconSet: 'mdi-v7',
    plugins: ['Notify', 'Dialog', 'Dark'],
    config: {
      // GREEN GLASS brand mapping: green=truth, amber=needs-a-human, red=broken.
      brand: {
        primary: '#5DFF86',   // bright phosphor
        secondary: '#2F9A55', // dim phosphor
        accent: '#5DFF86',
        dark: '#0A140C',      // green glass
        positive: '#5DFF86',
        negative: '#FF6B5E',  // alarm
        info: '#2F9A55',
        warning: '#FFB347',   // signal amber
      },
    },
  },
  build: { target: { browser: ['es2022'], node: 'node20' }, vueRouterMode: 'history' },
  devServer: { open: false, host: '0.0.0.0', port: 9000 },
  capacitor: { appId: 'io.personal.os', appName: 'Personal OS' }
}))
