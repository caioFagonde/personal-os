import HomePage from '../pages/HomePage.vue'
import ModulePage from '../pages/ModulePage.vue'
import SyncPage from '../pages/SyncPage.vue'

export default [
  { path: '/', component: HomePage },
  { path: '/study', component: ModulePage, props: { id: 'study' } },
  { path: '/zettelkasten', component: ModulePage, props: { id: 'zettelkasten' } },
  { path: '/geospatial', component: ModulePage, props: { id: 'geospatial' } },
  { path: '/sync', component: SyncPage }
]
