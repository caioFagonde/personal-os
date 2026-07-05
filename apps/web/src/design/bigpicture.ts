/**
 * Big Picture design tokens.
 *
 * Every module gets an identity: an accent hue that drives the WebGL aurora,
 * a short verb-first description for the hero, and quick actions.
 * Extends (does not replace) src/design/tokens.ts.
 */
import { allModules, navigationModules, secondaryModules } from './tokens'

export interface BigPictureAction {
  label: string
  path: string
  icon: string
}

export interface BigPictureModule {
  id: string
  label: string
  path: string
  icon: string
  group: string
  /** Primary accent — drives tile art and the aurora hue when focused. */
  accent: string
  /** Secondary accent — the aurora's counter-band. */
  accent2: string
  /** One line, verb-first, owner's voice. Shown in the hero. */
  blurb: string
  actions?: BigPictureAction[]
}

const identity: Record<string, Omit<BigPictureModule, 'id' | 'label' | 'path' | 'icon' | 'group'>> = {
  'command-center': {
    accent: '#7DD3FC', accent2: '#A78BFA',
    blurb: 'See the whole system at a glance — metrics, health, and the fastest path into every module.',
    actions: [{ label: 'Open dashboard', path: '/command-center', icon: 'mdi-view-dashboard-outline' }],
  },
  capture: {
    accent: '#FBBF24', accent2: '#FB7185',
    blurb: 'Get it off your mind in two keystrokes. Notes, tasks, and slash commands land in one inbox.',
    actions: [
      { label: 'Open capture', path: '/capture', icon: 'mdi-lightning-bolt-outline' },
      { label: 'Review inbox', path: '/tasks', icon: 'mdi-inbox-arrow-down-outline' },
    ],
  },
  tasks: {
    accent: '#34D399', accent2: '#22D3EE',
    blurb: 'Your execution list. Review, complete, or delegate — due dates and follow-ups in one tap.',
    actions: [{ label: 'Open tasks', path: '/tasks', icon: 'mdi-checkbox-marked-circle-auto-outline' }],
  },
  'digital-twin': {
    accent: '#A78BFA', accent2: '#F472B6',
    blurb: 'Your personal state model — goals, timeline, inferred state, and privacy-aware memory.',
    actions: [{ label: 'Open twin', path: '/digital-twin', icon: 'mdi-brain' }],
  },
  study: {
    accent: '#F472B6', accent2: '#FBBF24',
    blurb: 'Notes, decks, and spaced repetition. Learn it once, keep it for good.',
    actions: [{ label: 'Study notes', path: '/study', icon: 'mdi-school-outline' }],
  },
  'study-companion': {
    accent: '#FB7185', accent2: '#A78BFA',
    blurb: 'Paste text or snap a page — get learning atoms and a review schedule back.',
    actions: [
      { label: 'Paste text', path: '/study-companion', icon: 'mdi-camera-iris' },
      { label: 'Review queue', path: '/study', icon: 'mdi-cards-outline' },
    ],
  },
  zettelkasten: {
    accent: '#60A5FA', accent2: '#2DD4BF',
    blurb: 'Atomic notes with backlinks, tags, and geospatial anchors. Obsidian-compatible export.',
    actions: [{ label: 'Open notes', path: '/zettelkasten', icon: 'mdi-graph-outline' }],
  },
  research: {
    accent: '#2DD4BF', accent2: '#60A5FA',
    blurb: 'Search open-access papers, ingest authorized PDFs, and run local full-text search.',
    actions: [{ label: 'Search papers', path: '/research', icon: 'mdi-file-search-outline' }],
  },
  geospatial: {
    accent: '#4ADE80', accent2: '#38BDF8',
    blurb: 'Your maps, tiles, and field data — fully offline-capable.',
    actions: [{ label: 'Open maps', path: '/geospatial', icon: 'mdi-map-search-outline' }],
  },
  'ar-memory': {
    accent: '#C084FC', accent2: '#22D3EE',
    blurb: 'Anchor memories to places and objects. Recall them where they happened.',
    actions: [{ label: 'Open AR memory', path: '/ar-memory', icon: 'mdi-cube-scan' }],
  },
  connectors: {
    accent: '#38BDF8', accent2: '#34D399',
    blurb: 'Bring your accounts in — Google, Microsoft, messaging, mesh — with encrypted tokens.',
    actions: [{ label: 'Manage connectors', path: '/connectors', icon: 'mdi-connection' }],
  },
  automation: {
    accent: '#FB923C', accent2: '#FBBF24',
    blurb: 'Workflows that run themselves. Triggers, approvals, and agentic pipelines.',
    actions: [{ label: 'Open automation', path: '/automation', icon: 'mdi-transit-connection-variant' }],
  },
  'coding-agent': {
    accent: '#818CF8', accent2: '#38BDF8',
    blurb: 'Delegate coding jobs to an agent and review the diffs when they land.',
    actions: [{ label: 'New coding job', path: '/coding-agent', icon: 'mdi-code-braces' }],
  },
  sync: {
    accent: '#22D3EE', accent2: '#7DD3FC',
    blurb: 'Every device, the same truth. Watch replication and resolve drift.',
    actions: [{ label: 'Open sync', path: '/sync', icon: 'mdi-sync-circle' }],
  },
  'sync-health': {
    accent: '#5EEAD4', accent2: '#22D3EE',
    blurb: 'Latency, lag, and replication health across the fleet.',
  },
  'backup-restore': {
    accent: '#93C5FD', accent2: '#5EEAD4',
    blurb: 'Encrypted backups out, clean restores back. Your data, recoverable.',
  },
  'model-runtime': {
    accent: '#E879F9', accent2: '#818CF8',
    blurb: 'Local models, embeddings, and runtimes — managed from one place.',
  },
}

const FALLBACK = { accent: '#8B9BBF', accent2: '#5E6E94', blurb: 'System module.' }

function decorate(list: readonly { id: string; label: string; path: string; icon: string; group: string }[]): BigPictureModule[] {
  return list.map((m) => ({ ...m, ...(identity[m.id] ?? FALLBACK) }))
}

/** Primary carousel: the modules you live in. */
export const featuredModules: BigPictureModule[] = decorate(navigationModules)

/** System strip: ops & maintenance surfaces. */
export const systemModules: BigPictureModule[] = decorate(secondaryModules)

export const bigPictureModules: BigPictureModule[] = decorate(allModules)

export function moduleByPath(path: string): BigPictureModule | undefined {
  if (path === '/') return undefined
  if (path.startsWith('/command-center')) return bigPictureModules.find((m) => m.id === 'command-center')
  return bigPictureModules.find((m) => m.path !== '/' && (path === m.path || path.startsWith(m.path + '/')))
}

/** Ordered groups as they appear in the carousel, for section markers. */
export function carouselSections(list: BigPictureModule[]): { group: string; startIndex: number }[] {
  const sections: { group: string; startIndex: number }[] = []
  list.forEach((m, i) => {
    if (!sections.length || sections[sections.length - 1].group !== m.group) {
      sections.push({ group: m.group, startIndex: i })
    }
  })
  return sections
}
