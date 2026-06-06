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
import CapturePage from '../pages/CapturePage.vue'
import TasksPage from '../pages/TasksPage.vue'
import StudyCompanionPage from '../pages/StudyCompanionPage.vue'
import ConnectorsPage from '../pages/ConnectorsPage.vue'
import OnboardingPage from '../pages/OnboardingPage.vue'
import BackupRestorePage from '../pages/BackupRestorePage.vue'
import DevicePairingPage from '../pages/DevicePairingPage.vue'
import SyncHealthPage from '../pages/SyncHealthPage.vue'
import ConnectorWorkerPage from '../pages/ConnectorWorkerPage.vue'
import ConflictResolutionPage from '../pages/ConflictResolutionPage.vue'
import OfflineQueuePage from '../pages/OfflineQueuePage.vue'
import CertificationPage from '../pages/CertificationPage.vue'
import ReleaseCenterPage from '../pages/ReleaseCenterPage.vue'
import ModelRuntimePage from '../pages/ModelRuntimePage.vue'
import LiveStackPage from '../pages/LiveStackPage.vue'
import InitialVersionReadinessPage from '../pages/InitialVersionReadinessPage.vue'

export default [
  { path: '/', component: HomePage },
  { path: '/study', component: StudyPage },
  { path: '/zettelkasten', component: ZettelkastenPage },
  { path: '/geospatial', component: GeospatialPage },
  { path: '/research', component: ResearchPage },
  { path: '/ar-memory', component: ARMemoryPage },
  { path: '/automation', component: AutomationPage },
  { path: '/digital-twin', component: DigitalTwinPage },
  { path: '/capture', component: CapturePage },
  { path: '/tasks', component: TasksPage },
  { path: '/study-companion', component: StudyCompanionPage },
  { path: '/sync', component: SyncPage },
  { path: '/sync-health', component: SyncHealthPage },
  { path: '/connectors', component: ConnectorsPage },
  { path: '/onboarding', component: OnboardingPage },
  { path: '/backup-restore', component: BackupRestorePage },
  { path: '/device-pairing', component: DevicePairingPage },
  { path: '/connector-worker', component: ConnectorWorkerPage },
  { path: '/conflicts', component: ConflictResolutionPage },
  { path: '/offline-queue', component: OfflineQueuePage },
  { path: '/certification', component: CertificationPage },
  { path: '/release-center', component: ReleaseCenterPage },
  { path: '/model-runtime', component: ModelRuntimePage },
  { path: '/live-stack', component: LiveStackPage },
  { path: '/initial-readiness', component: InitialVersionReadinessPage },
  { path: '/modules/:id', component: ModulePage, props: true }
]
