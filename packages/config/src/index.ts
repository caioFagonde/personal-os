export const config = {
  apiUrl: import.meta.env?.VITE_API_URL ?? 'http://localhost:8080',
  syncUrl: import.meta.env?.VITE_SYNC_URL ?? 'http://localhost:8081',
  commandBusUrl: import.meta.env?.VITE_COMMAND_BUS_URL ?? 'http://localhost:8082'
}
