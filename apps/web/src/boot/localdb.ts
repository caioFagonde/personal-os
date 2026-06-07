import { boot } from 'quasar/wrappers'
import localforage from 'localforage'

localforage.config({ name: 'personal-os', storeName: 'offline_cache' })

export { localforage }

export default boot(() => {
  // Initializes the shared offline cache before the application mounts.
})