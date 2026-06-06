export interface RuntimePolicyInput {
  platform: 'android' | 'ios' | 'web'
  network: 'wifi' | 'cellular' | 'offline' | 'unknown'
  batteryLevel: number
  charging: boolean
  pendingMutations: number
}

export function mobileRuntimePolicy(input: RuntimePolicyInput) {
  const canBackgroundSync = input.network !== 'offline' && (input.charging || input.batteryLevel >= 0.18 || input.pendingMutations >= 10)
  const preferWifi = input.pendingMutations > 50 || input.network === 'cellular'
  const notificationPriority = input.pendingMutations > 25 ? 'high' : 'default'
  return {
    canBackgroundSync,
    preferWifi,
    notificationPriority,
    syncBudgetMs: input.charging ? 20_000 : 7_500,
    cameraAllowed: input.platform !== 'web'
  }
}
