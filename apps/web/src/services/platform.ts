export type PlatformKind = 'mobile' | 'desktop' | 'web'

export function detectPlatform(userAgent = globalThis.navigator?.userAgent || '', width = globalThis.innerWidth || 1280): PlatformKind {
  const ua = userAgent.toLowerCase()
  if (/android|iphone|ipad|ipod/.test(ua) || width < 720) return 'mobile'
  if (/tauri|electron|windows nt|macintosh|x11|linux/.test(ua) && width >= 960) return 'desktop'
  return 'web'
}

export function preferredLayout(kind: PlatformKind) {
  return {
    drawer: kind !== 'mobile',
    bottomNav: kind === 'mobile',
    commandPaletteShortcut: kind === 'desktop' ? 'Ctrl/⌘ K' : 'Search',
    density: kind === 'mobile' ? 'comfortable' : 'compact'
  }
}

export function safeAreaStyle(kind: PlatformKind) {
  return kind === 'mobile'
    ? { paddingBottom: 'calc(env(safe-area-inset-bottom) + 72px)' }
    : { paddingBottom: '24px' }
}
