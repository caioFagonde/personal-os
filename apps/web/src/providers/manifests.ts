export type ProviderState =
  | 'not_installed'
  | 'needs_config'
  | 'malformed_config'
  | 'ready_to_authorize'
  | 'connected'
  | 'degraded'
  | 'dry_run_only'
  | 'failed'

export type CostTag =
  | 'local'
  | 'private_mesh'
  | 'external_provider'
  | 'free_tier_possible'
  | 'paid_external'
  | 'verify_pricing'

export type ProviderCategory =
  | 'oauth_identity'
  | 'messaging'
  | 'infrastructure'
  | 'ai_models'
  | 'cloud_providers'
  | 'developer_tools'

export interface EnvRequirement {
  key: string
  label: string
  secret?: boolean
}

export interface ProviderManifest {
  id: string
  name: string
  icon: string
  category: ProviderCategory
  description: string
  costTags: CostTag[]
  envRequirements: EnvRequirement[]
  docsUrl?: string
  capabilities: string[]
  cloudSafetyNote?: string
}

export const PROVIDER_CATEGORIES: Record<ProviderCategory, { label: string; icon: string }> = {
  oauth_identity: { label: 'OAuth & Identity', icon: 'mdi-shield-key-outline' },
  messaging: { label: 'Messaging & Notifications', icon: 'mdi-message-outline' },
  infrastructure: { label: 'Infrastructure & Storage', icon: 'mdi-server-outline' },
  ai_models: { label: 'AI & Model Providers', icon: 'mdi-brain' },
  cloud_providers: { label: 'Cloud Providers', icon: 'mdi-cloud-outline' },
  developer_tools: { label: 'Developer Tools', icon: 'mdi-wrench-outline' },
}

export const STATE_DISPLAY: Record<ProviderState, { label: string; color: string; icon: string }> = {
  not_installed: { label: 'Not installed', color: 'grey-7', icon: 'mdi-download-outline' },
  needs_config: { label: 'Needs config', color: 'warning', icon: 'mdi-cog-outline' },
  malformed_config: { label: 'Malformed config', color: 'negative', icon: 'mdi-alert-outline' },
  ready_to_authorize: { label: 'Ready to authorize', color: 'info', icon: 'mdi-key-outline' },
  connected: { label: 'Connected', color: 'positive', icon: 'mdi-check-circle-outline' },
  degraded: { label: 'Degraded', color: 'orange', icon: 'mdi-alert-circle-outline' },
  dry_run_only: { label: 'Dry-run only', color: 'info', icon: 'mdi-flask-outline' },
  failed: { label: 'Failed', color: 'negative', icon: 'mdi-close-circle-outline' },
}

export const COST_DISPLAY: Record<CostTag, { label: string; color: string }> = {
  local: { label: 'Local', color: 'positive' },
  private_mesh: { label: 'Private mesh', color: 'teal' },
  external_provider: { label: 'External', color: 'info' },
  free_tier_possible: { label: 'Free tier', color: 'teal' },
  paid_external: { label: 'Paid', color: 'orange' },
  verify_pricing: { label: 'Verify pricing', color: 'warning' },
}

export const PROVIDER_MANIFESTS: ProviderManifest[] = [
  {
    id: 'google',
    name: 'Google',
    icon: 'mdi-google',
    category: 'oauth_identity',
    description: 'Google OAuth for Gmail, Drive backup, and Calendar sync.',
    costTags: ['external_provider', 'free_tier_possible'],
    envRequirements: [
      { key: 'GOOGLE_CLIENT_ID', label: 'OAuth Client ID' },
      { key: 'GOOGLE_CLIENT_SECRET', label: 'OAuth Client Secret', secret: true },
      { key: 'GOOGLE_REDIRECT_URI', label: 'Redirect URI' },
    ],
    capabilities: ['Gmail send', 'Drive backup upload', 'Calendar sync'],
  },
  {
    id: 'microsoft',
    name: 'Microsoft',
    icon: 'mdi-microsoft',
    category: 'oauth_identity',
    description: 'Microsoft OAuth for Outlook mail and OneDrive backup.',
    costTags: ['external_provider', 'free_tier_possible'],
    envRequirements: [
      { key: 'MICROSOFT_CLIENT_ID', label: 'OAuth Client ID' },
      { key: 'MICROSOFT_CLIENT_SECRET', label: 'OAuth Client Secret', secret: true },
      { key: 'MICROSOFT_REDIRECT_URI', label: 'Redirect URI' },
      { key: 'MICROSOFT_TENANT', label: 'Tenant ID' },
    ],
    capabilities: ['Outlook send', 'OneDrive backup upload'],
  },
  {
    id: 'twilio',
    name: 'Twilio',
    icon: 'mdi-message-text-outline',
    category: 'messaging',
    description: 'WhatsApp and SMS messaging through Twilio.',
    costTags: ['paid_external', 'verify_pricing'],
    envRequirements: [
      { key: 'TWILIO_ACCOUNT_SID', label: 'Account SID' },
      { key: 'TWILIO_AUTH_TOKEN', label: 'Auth Token', secret: true },
      { key: 'TWILIO_WHATSAPP_FROM', label: 'WhatsApp From number' },
    ],
    capabilities: ['WhatsApp send', 'SMS send', 'Sandbox mode'],
  },
  {
    id: 'ntfy',
    name: 'ntfy',
    icon: 'mdi-bell-outline',
    category: 'messaging',
    description: 'Lightweight push notifications via ntfy.sh or self-hosted.',
    costTags: ['local', 'free_tier_possible'],
    envRequirements: [
      { key: 'NTFY_BASE_URL', label: 'Base URL' },
      { key: 'NTFY_TOPIC', label: 'Topic' },
    ],
    capabilities: ['Push notifications', 'Mobile alerts', 'Private topics'],
  },
  {
    id: 'tailscale',
    name: 'Tailscale',
    icon: 'mdi-lan-connect',
    category: 'infrastructure',
    description: 'Private WireGuard mesh for secure device-to-device access.',
    costTags: ['private_mesh', 'free_tier_possible'],
    envRequirements: [
      { key: 'TAILSCALE_AUTHKEY', label: 'Auth Key (optional)', secret: true },
    ],
    capabilities: ['Private mesh network', 'Phone-to-PC access', 'MagicDNS'],
  },
  {
    id: 'aws',
    name: 'AWS',
    icon: 'mdi-aws',
    category: 'cloud_providers',
    description: 'Amazon Web Services. S3 backup, Bedrock models, and compute.',
    costTags: ['paid_external', 'verify_pricing'],
    envRequirements: [
      { key: 'AWS_ACCESS_KEY_ID', label: 'Access Key ID', secret: true },
      { key: 'AWS_SECRET_ACCESS_KEY', label: 'Secret Access Key', secret: true },
      { key: 'AWS_REGION', label: 'Region' },
    ],
    cloudSafetyNote: 'No automatic paid provisioning. Dry-run plan only. Explicit approval required for any cloud actions.',
    capabilities: ['S3 backup', 'Bedrock models', 'Lambda compute'],
  },
  {
    id: 'azure',
    name: 'Azure',
    icon: 'mdi-microsoft-azure',
    category: 'cloud_providers',
    description: 'Microsoft Azure. Blob storage, OpenAI models, and compute.',
    costTags: ['paid_external', 'verify_pricing'],
    envRequirements: [
      { key: 'AZURE_SUBSCRIPTION_ID', label: 'Subscription ID' },
      { key: 'AZURE_TENANT_ID', label: 'Tenant ID' },
      { key: 'AZURE_CLIENT_ID', label: 'Client ID' },
      { key: 'AZURE_CLIENT_SECRET', label: 'Client Secret', secret: true },
    ],
    cloudSafetyNote: 'No automatic paid provisioning. Dry-run plan only. Explicit approval required for any cloud actions.',
    capabilities: ['Blob storage', 'Azure OpenAI', 'Container instances'],
  },
  {
    id: 'gcp',
    name: 'Google Cloud',
    icon: 'mdi-google-cloud',
    category: 'cloud_providers',
    description: 'Google Cloud Platform. GCS backup, Vertex AI, and compute.',
    costTags: ['paid_external', 'verify_pricing'],
    envRequirements: [
      { key: 'GCP_PROJECT_ID', label: 'Project ID' },
      { key: 'GCP_SERVICE_ACCOUNT_KEY', label: 'Service Account Key path' },
    ],
    cloudSafetyNote: 'No automatic paid provisioning. Dry-run plan only. Explicit approval required for any cloud actions.',
    capabilities: ['GCS backup', 'Vertex AI', 'Cloud Run'],
  },
  {
    id: 'github',
    name: 'GitHub',
    icon: 'mdi-github',
    category: 'developer_tools',
    description: 'GitHub integration for repo access, issues, and coding agent workflows.',
    costTags: ['external_provider', 'free_tier_possible'],
    envRequirements: [
      { key: 'GITHUB_TOKEN', label: 'Personal Access Token', secret: true },
    ],
    capabilities: ['Repository access', 'Issue tracking', 'Coding agent workspace'],
  },
  {
    id: 'claude-code',
    name: 'Claude Code',
    icon: 'mdi-robot-outline',
    category: 'ai_models',
    description: 'Claude Code agent for safe, approval-gated coding tasks.',
    costTags: ['paid_external', 'verify_pricing'],
    envRequirements: [
      { key: 'ANTHROPIC_API_KEY', label: 'Anthropic API Key', secret: true },
      { key: 'CODING_AGENT_EXECUTE', label: 'Execution enabled (true/false)' },
    ],
    capabilities: ['Coding agent', 'Approval-gated execution', 'Worktree isolation'],
  },
  {
    id: 'ollama',
    name: 'Ollama',
    icon: 'mdi-brain',
    category: 'ai_models',
    description: 'Local LLM inference with Ollama. Runs models on your hardware.',
    costTags: ['local'],
    envRequirements: [
      { key: 'OLLAMA_BASE_URL', label: 'Ollama API URL' },
    ],
    capabilities: ['Local LLM inference', 'Embedding generation', 'Private processing'],
  },
  {
    id: 'qdrant',
    name: 'Qdrant',
    icon: 'mdi-vector-combine',
    category: 'infrastructure',
    description: 'Vector database for semantic search and embeddings.',
    costTags: ['local', 'free_tier_possible'],
    envRequirements: [
      { key: 'QDRANT_URL', label: 'Qdrant URL' },
      { key: 'QDRANT_API_KEY', label: 'API Key (optional)', secret: true },
    ],
    capabilities: ['Vector search', 'Embedding storage', 'Semantic retrieval'],
  },
  {
    id: 'searxng',
    name: 'SearXNG',
    icon: 'mdi-search-web',
    category: 'infrastructure',
    description: 'Privacy-respecting metasearch engine for research ingestion.',
    costTags: ['local'],
    envRequirements: [
      { key: 'SEARXNG_URL', label: 'SearXNG URL' },
    ],
    capabilities: ['Web search', 'Research ingestion', 'Privacy-first search'],
  },
  {
    id: 'n8n',
    name: 'n8n',
    icon: 'mdi-sitemap-outline',
    category: 'infrastructure',
    description: 'Workflow automation engine for event-driven pipelines.',
    costTags: ['local', 'free_tier_possible'],
    envRequirements: [
      { key: 'N8N_BASE_URL', label: 'n8n URL' },
      { key: 'N8N_API_KEY', label: 'API Key (optional)', secret: true },
    ],
    capabilities: ['Workflow automation', 'Webhooks', 'Event pipelines'],
  },
  {
    id: 'minio',
    name: 'MinIO',
    icon: 'mdi-database-outline',
    category: 'infrastructure',
    description: 'S3-compatible local object storage for backups and artifacts.',
    costTags: ['local'],
    envRequirements: [
      { key: 'MINIO_ENDPOINT', label: 'MinIO Endpoint' },
      { key: 'MINIO_ACCESS_KEY', label: 'Access Key', secret: true },
      { key: 'MINIO_SECRET_KEY', label: 'Secret Key', secret: true },
    ],
    capabilities: ['Object storage', 'Backup storage', 'Artifact management'],
  },
  {
    id: 'tileserver',
    name: 'TileServer GL',
    icon: 'mdi-map-outline',
    category: 'infrastructure',
    description: 'Local vector tile server for offline map rendering.',
    costTags: ['local'],
    envRequirements: [
      { key: 'TILESERVER_URL', label: 'TileServer URL' },
    ],
    capabilities: ['Offline maps', 'Vector tiles', 'Geospatial rendering'],
  },
  {
    id: 'openai',
    name: 'OpenAI',
    icon: 'mdi-creation-outline',
    category: 'ai_models',
    description: 'OpenAI API for GPT models, DALL-E, and embeddings.',
    costTags: ['paid_external', 'verify_pricing'],
    envRequirements: [
      { key: 'OPENAI_API_KEY', label: 'API Key', secret: true },
    ],
    capabilities: ['GPT inference', 'Embeddings', 'Image generation'],
  },
]

export function getManifest(id: string): ProviderManifest | undefined {
  return PROVIDER_MANIFESTS.find(p => p.id === id)
}

export function getManifestsByCategory(): Record<ProviderCategory, ProviderManifest[]> {
  const result = {} as Record<ProviderCategory, ProviderManifest[]>
  for (const cat of Object.keys(PROVIDER_CATEGORIES) as ProviderCategory[]) {
    result[cat] = PROVIDER_MANIFESTS.filter(p => p.category === cat)
  }
  return result
}

export interface ProviderLiveStatus {
  id: string
  state: ProviderState
  message: string
  configured: boolean
  hasOAuth?: boolean
}

const BACKEND_PROVIDERS = new Set(['google', 'microsoft', 'twilio', 'ntfy', 'tailscale'])

export function deriveProviderState(
  manifest: ProviderManifest,
  backendStatus?: { configured: boolean; status: string; message: string },
): ProviderLiveStatus {
  if (backendStatus && BACKEND_PROVIDERS.has(manifest.id)) {
    let state: ProviderState = 'needs_config'
    if (backendStatus.status === 'connected' || backendStatus.status === 'active') state = 'connected'
    else if (backendStatus.status === 'ready' || backendStatus.status === 'configured') state = backendStatus.configured ? 'connected' : 'ready_to_authorize'
    else if (backendStatus.status === 'needs_oauth_client' || backendStatus.status === 'needs_configuration') state = 'needs_config'
    else if (backendStatus.status === 'manual_authorization_required') state = 'ready_to_authorize'
    else if (backendStatus.status === 'degraded') state = 'degraded'
    else if (backendStatus.status === 'failed') state = 'failed'
    return {
      id: manifest.id,
      state,
      message: backendStatus.message,
      configured: backendStatus.configured,
      hasOAuth: manifest.id === 'google' || manifest.id === 'microsoft',
    }
  }
  return {
    id: manifest.id,
    state: 'not_installed',
    message: `Configure ${manifest.name} to get started.`,
    configured: false,
  }
}
