import { configure } from 'quasar/wrappers'

export default configure(() => ({
  boot: ['localdb'],
  css: ['app.scss'],
  extras: ['mdi-v7'],
  framework: { plugins: ['Notify', 'Dialog'] },
  build: { target: { browser: ['es2022'], node: 'node20' }, vueRouterMode: 'history' },
  devServer: { open: false, host: '0.0.0.0', port: 9000 },
  capacitor: { appId: 'io.personal.os', appName: 'Personal OS' }
}))
