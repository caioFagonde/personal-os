import HomePage from '../pages/HomePage.vue'
import StudyPage from '../pages/StudyPage.vue'
import ZettelkastenPage from '../pages/ZettelkastenPage.vue'
import GeospatialPage from '../pages/GeospatialPage.vue'
import SyncPage from '../pages/SyncPage.vue'
import ModulePage from '../pages/ModulePage.vue'

export default [
  { path: '/', component: HomePage },
  { path: '/study', component: StudyPage },
  { path: '/zettelkasten', component: ZettelkastenPage },
  { path: '/geospatial', component: GeospatialPage },
  { path: '/sync', component: SyncPage },
  { path: '/modules/:id', component: ModulePage, props: true }
]
