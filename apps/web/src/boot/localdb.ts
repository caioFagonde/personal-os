import localforage from 'localforage'
localforage.config({ name: 'personal-os', storeName: 'offline_cache' })
export default localforage
