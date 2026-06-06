export async function fetchModules(apiUrl: string) {
  const response = await fetch(`${apiUrl}/api/modules`)
  if (!response.ok) throw new Error(`Module fetch failed: ${response.status}`)
  return response.json()
}
