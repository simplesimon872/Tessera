/**
 * GET /api/banner/[handle]
 *
 * Returns a 1500x500 SVG banner — X/Twitter header size.
 * SVG approach used instead of ImageResponse (not supported on this Cloudflare edge build).
 * Renders correctly in browsers and as OG preview images.
 */

export const runtime = 'edge'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function fmt(n: number | null | undefined): string {
  if (n === null || n === undefined) return '--'
  return n.toFixed(1)
}

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-GB', {
      day: 'numeric', month: 'short', year: 'numeric',
    })
  } catch {
    return ''
  }
}

function esc(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ handle: string }> },
) {
  const { handle } = await params
  const cleanHandle = esc(handle.toLowerCase().replace(/^@/, ''))

  // Fetch profile
  let profile: any = null
  try {
    const res = await fetch(`${API_URL}/api/score/${cleanHandle}`, {
      headers: { 'Accept': 'application/json' },
    })
    if (res.ok) {
      const json = await res.json()
      profile = json.ok ? json.data : null
    }
  } catch {
    // no-data banner
  }

  const epoch     = profile?.epochs?.[0] ?? null
  const scoresRaw = Array.isArray(epoch?.scores) ? epoch.scores[0] : epoch?.scores
  const anchor    = Array.isArray(epoch?.anchors) ? epoch.anchors[0] : epoch?.anchors
  const isSealed  = epoch?.status === 'sealed'
  const hasClaim  = profile?.claimed ?? false

  const composite   = fmt(scoresRaw?.composite)
  const originality = fmt(scoresRaw?.originality)
  const focus       = fmt(scoresRaw?.focus)
  const consistency = fmt(scoresRaw?.consistency)
  const depth       = fmt(scoresRaw?.depth)

  const epochStart = epoch?.epoch_start ? fmtDate(epoch.epoch_start) : null
  const epochEnd   = epoch?.epoch_end   ? fmtDate(epoch.epoch_end)   : null
  const dateLine   = epochStart && epochEnd ? `${epochStart} to ${epochEnd}` : ''

  const txShort    = anchor?.tx_hash ? esc((anchor.tx_hash as string).slice(0, 14) + '...') : ''
  const statusLabel  = isSealed ? 'SEALED' : hasClaim ? 'LIVE' : 'UNSEALED'
  const statusColour = isSealed ? '#4AFF91' : '#E8FF47'
  const chainLabel   = isSealed ? 'AVALANCHE C-CHAIN MAINNET' : 'PENDING SEAL'
  const dotColour    = isSealed ? '#4AFF91' : '#1E1E22'

  const pillars = [
    { label: 'ORIG',  value: originality, x: 620 },
    { label: 'FOCUS', value: focus,       x: 790 },
    { label: 'CONS',  value: consistency, x: 960 },
    { label: 'DEPTH', value: depth,       x: 1130 },
  ]

  // Stripe pattern IDs need to be unique per request to avoid SVG caching issues
  const patternId = `stripes-${cleanHandle}`

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="500" viewBox="0 0 1500 500">
  <defs>
    <pattern id="${patternId}" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
      <rect width="40" height="40" fill="#0A0A0B"/>
      <line x1="20" y1="0" x2="20" y2="40" stroke="#1A1A1E" stroke-width="1"/>
    </pattern>
  </defs>

  <!-- Background -->
  <rect width="1500" height="500" fill="#0A0A0B"/>

  <!-- Diagonal stripe decoration top-right -->
  <rect x="1020" y="-60" width="540" height="620" fill="url(#${patternId})" opacity="0.8"/>

  <!-- Left accent bar -->
  <rect x="0" y="0" width="6" height="500" fill="${statusColour}"/>

  <!-- Horizontal hairline -->
  <line x1="6" y1="250" x2="1500" y2="250" stroke="#1E1E22" stroke-width="1"/>

  <!-- Vertical divider between panels -->
  <line x1="566" y1="40" x2="566" y2="460" stroke="#1E1E22" stroke-width="1"/>

  <!-- ── LEFT PANEL ── -->

  <!-- TESSERA PROTOCOL label -->
  <text x="52" y="88" font-family="system-ui, sans-serif" font-size="11" fill="#888890" letter-spacing="3">TESSERA PROTOCOL</text>

  <!-- Handle -->
  <text x="52" y="180" font-family="system-ui, sans-serif" font-size="72" font-weight="700" fill="#F0F0F0" letter-spacing="-1">@${cleanHandle}</text>

  <!-- Status pill -->
  <rect x="52" y="200" width="${statusLabel.length * 9 + 24}" height="28" fill="${statusColour}15" stroke="${statusColour}50" stroke-width="1" rx="1"/>
  <text x="64" y="219" font-family="system-ui, sans-serif" font-size="11" font-weight="500" fill="${statusColour}" letter-spacing="2">${statusLabel}</text>

  ${txShort ? `<text x="${52 + statusLabel.length * 9 + 40}" y="219" font-family="system-ui, sans-serif" font-size="10" fill="#888890" letter-spacing="1">TX ${txShort}</text>` : ''}

  <!-- Epoch dates -->
  ${dateLine ? `<text x="52" y="408" font-family="system-ui, sans-serif" font-size="11" fill="#888890" letter-spacing="1">${esc(dateLine)}</text>` : ''}

  <!-- Site URL -->
  <text x="52" y="430" font-family="system-ui, sans-serif" font-size="11" fill="#2A2A2E" letter-spacing="1">tessera-8x7.pages.dev</text>

  <!-- ── RIGHT PANEL ── -->

  <!-- COMPOSITE SCORE label -->
  <text x="614" y="88" font-family="system-ui, sans-serif" font-size="11" fill="#888890" letter-spacing="3">COMPOSITE SCORE</text>

  <!-- Composite number -->
  <text x="610" y="230" font-family="system-ui, sans-serif" font-size="148" font-weight="700" fill="${composite !== '--' ? '#E8FF47' : '#1E1E22'}" letter-spacing="-4">${composite}</text>

  <!-- Pillar dividers -->
  <line x1="790" y1="310" x2="790" y2="450" stroke="#1E1E22" stroke-width="1"/>
  <line x1="960" y1="310" x2="960" y2="450" stroke="#1E1E22" stroke-width="1"/>
  <line x1="1130" y1="310" x2="1130" y2="450" stroke="#1E1E22" stroke-width="1"/>

  <!-- Pillars -->
  ${pillars.map(({ label, value, x }) => `
  <text x="${x}" y="336" font-family="system-ui, sans-serif" font-size="10" fill="#888890" letter-spacing="2">${label}</text>
  <text x="${x}" y="390" font-family="system-ui, sans-serif" font-size="44" font-weight="700" fill="${value === '--' ? '#1E1E22' : '#F0F0F0'}" letter-spacing="-1">${value}</text>
  `).join('')}

  <!-- Chain indicator dot -->
  <circle cx="618" cy="463" r="4" fill="${dotColour}"/>
  <text x="630" y="467" font-family="system-ui, sans-serif" font-size="10" fill="#888890" letter-spacing="2">${chainLabel}</text>

</svg>`

  return new Response(svg, {
    headers: {
      'Content-Type':  'image/svg+xml',
      'Cache-Control': isSealed
        ? 'public, max-age=86400, stale-while-revalidate=3600'
        : 'public, max-age=300, stale-while-revalidate=60',
    },
  })
}
