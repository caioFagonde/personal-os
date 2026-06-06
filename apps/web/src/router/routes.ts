import HomePage from '../pages/HomePage.vue'
import StudyPage from '../pages/StudyPage.vue'
import ZettelkastenPage from '../pages/ZettelkastenPage.vue'
import GeospatialPage from '../pages/GeospatialPage.vue'
import SyncPage from '../pages/SyncPage.vue'
import ModulePage from '../pages/ModulePage.vue'
import ResearchPage from '../pages/ResearchPage.vue'
import ARMemoryPage from '../pages/ARMemoryPage.vue'
import AutomationPage from '../pages/AutomationPage.vue'
import DigitalTwinPage from '../pages/DigitalTwinPage.vue'

export default [
  { path: '/', component: HomePage },
  { path: '/study', component: StudyPage },
  { path: '/zettelkasten', component: ZettelkastenPage },
  { path: '/geospatial', component: GeospatialPage },
  { path: '/research', component: ResearchPage },
  { path: '/ar-memory', component: ARMemoryPage },
  { path: '/automation', component: AutomationPage },
  { path: '/digital-twin', component: DigitalTwinPage },
  { path: '/sync', component: SyncPage },
  { path: '/modules/:id', component: ModulePage, props: true }
]
