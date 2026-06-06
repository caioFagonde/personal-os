import { createApp } from 'vue'
import { Quasar } from 'quasar'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import routes from './router/routes'
import 'quasar/src/css/index.sass'

const app = createApp(App)
const router = createRouter({ history: createWebHistory(), routes })
app.use(Quasar, {})
app.use(createPinia())
app.use(router)
app.mount('#q-app')
