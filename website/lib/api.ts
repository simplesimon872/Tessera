const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface EpochScore {
  id: string
  epoch_start: string
  epoch_end: string
  status: 'computed' | 'sealed' | 'seal_failed'
  scores: {
    composite: number
    originality: number
    focus: number
    consistency: number
    depth: number
  }
  anchor?: {
    tx_hash: string
    block_number: number
    anchored_at: string
    snowtrace_url: string
  }
}

export interface ProfileData {
  handle: string
  claimed: boolean
  claimed_at: string | null
  epochs: EpochScore[]
}

export interface AuditData {
  epoch: {
    id: string
    handle: string
    epoch_start: string
    epoch_end: string
    status: string
  }
  scores: {
    composite: number
    originality: number
    focus: number
    consistency: number
    depth: number
    consistency_mode: string
    other_cap_applied: boolean
  }
  methodology: {
    version: string
    prompt_hash: string
    model: string
    weights: string
  }
  post_breakdown: {
    total: number
    classified: number
    greeting: number
    null: number
  }
  snapshot_hash: string
  anchor: {
    tx_hash: string
    block_number: number
    anchored_at: string
    snowtrace_url: string
  } | null
  disclaimer: string
}

export interface LeaderboardEntry {
  handle: string
  composite: number
  originality: number
  focus: number
  consistency: number
  depth: number
  epoch_end: string
  status: string
}

export async function getProfile(handle: string): Promise<ProfileData | null> {
  try {
    const url = `${API_URL}/api/score/${handle}`
    console.log(`[tessera] getProfile → ${url}`)
    const res = await fetch(url, { cache: 'no-store' })
    console.log(`[tessera] getProfile ← ${res.status}`)
    if (!res.ok) return null
    const json = await res.json()
    return json.ok ? json.data : null
  } catch (e) {
    console.error(`[tessera] getProfile failed for ${handle}:`, e)
    return null
  }
}

export async function getAudit(epochId: string): Promise<AuditData | null> {
  try {
    const res = await fetch(`${API_URL}/api/audit/${epochId}`, { cache: 'no-store' })
    if (!res.ok) return null
    const json = await res.json()
    return json.ok ? json.data : null
  } catch (e) {
    console.error(`[tessera] getAudit failed for ${epochId}:`, e)
    return null
  }
}

export async function getLeaderboard(): Promise<LeaderboardEntry[]> {
  try {
    const res = await fetch(`${API_URL}/api/leaderboard`, { cache: 'no-store' })
    if (!res.ok) return []
    const json = await res.json()
    return json.ok ? json.data : []
  } catch (e) {
    console.error(`[tessera] getLeaderboard failed:`, e)
    return []
  }
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return '—'
  return score.toFixed(1)
}
