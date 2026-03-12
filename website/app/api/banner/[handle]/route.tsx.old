import { ImageResponse } from 'next/og'
export const runtime = 'edge'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function fmt(n: number | null | undefined): string {
  if (n === null || n === undefined) return '--'
  return n.toFixed(1)
}

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
  } catch { return '' }
}

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ handle: string }> },
) {
  const { handle } = await params
  const cleanHandle = handle.toLowerCase().replace(/^@/, '')

  // Fetch real profile data
  let profile: any = null
  try {
    const res = await fetch(`${API_URL}/api/score/${cleanHandle}`)
    if (res.ok) {
      const json = await res.json()
      profile = json.ok ? json.data : null
    }
  } catch { /* render no-data banner */ }

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

  const epochStart  = epoch?.epoch_start ? fmtDate(epoch.epoch_start) : null
  const epochEnd    = epoch?.epoch_end   ? fmtDate(epoch.epoch_end)   : null
  const dateLine    = epochStart && epochEnd ? `${epochStart} to ${epochEnd}` : ''
  const txShort     = anchor?.tx_hash ? (anchor.tx_hash as string).slice(0, 14) + '...' : ''

  const statusLabel  = isSealed ? 'SEALED' : hasClaim ? 'LIVE' : 'UNSEALED'
  const statusColour = isSealed ? '#4AFF91' : '#E8FF47'
  const chainLabel   = isSealed ? 'AVALANCHE C-CHAIN MAINNET' : 'PENDING SEAL'
  const dotColour    = isSealed ? '#4AFF91' : '#1E1E22'
  const scoreColour  = composite !== '--' ? statusColour : '#1E1E22'

  return new ImageResponse(
    (
      <div style={{ width: 1500, height: 500, background: '#0A0A0B', display: 'flex', flexDirection: 'row' }}>

        {/* Accent bar */}
        <div style={{ display: 'flex', width: 6, height: 500, background: statusColour }} />

        {/* LEFT PANEL */}
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', width: 554, paddingTop: 44, paddingBottom: 44, paddingLeft: 46, paddingRight: 48, borderRight: '1px solid #1E1E22' }}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', color: '#888890', fontSize: 11, letterSpacing: 3 }}>TESSERA PROTOCOL</div>
            <div style={{ display: 'flex', color: '#F0F0F0', fontSize: 60, fontWeight: 700, marginTop: 16 }}>@{cleanHandle}</div>
            <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', marginTop: 16 }}>
              <div style={{ display: 'flex', color: statusColour, fontSize: 11, letterSpacing: 2 }}>{statusLabel}</div>
              {txShort ? <div style={{ display: 'flex', color: '#888890', fontSize: 10, marginLeft: 16 }}>TX {txShort}</div> : null}
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {dateLine ? <div style={{ display: 'flex', color: '#888890', fontSize: 11, marginBottom: 6 }}>{dateLine}</div> : null}
            <div style={{ display: 'flex', color: '#2A2A2E', fontSize: 11 }}>tessera-8x7.pages.dev</div>
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', width: 940, paddingTop: 44, paddingBottom: 44, paddingLeft: 52, paddingRight: 60 }}>

          {/* Composite */}
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', color: '#888890', fontSize: 11, letterSpacing: 3 }}>COMPOSITE SCORE</div>
            <div style={{ display: 'flex', color: scoreColour, fontSize: 120, fontWeight: 700, marginTop: 4 }}>{composite}</div>
          </div>

          {/* Pillars */}
          <div style={{ display: 'flex', flexDirection: 'row' }}>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', color: '#888890', fontSize: 10, letterSpacing: 2 }}>ORIG</div>
              <div style={{ display: 'flex', color: '#F0F0F0', fontSize: 44, fontWeight: 700, marginTop: 8 }}>{originality}</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', marginLeft: 48, paddingLeft: 48, borderLeft: '1px solid #1E1E22' }}>
              <div style={{ display: 'flex', color: '#888890', fontSize: 10, letterSpacing: 2 }}>FOCUS</div>
              <div style={{ display: 'flex', color: '#F0F0F0', fontSize: 44, fontWeight: 700, marginTop: 8 }}>{focus}</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', marginLeft: 48, paddingLeft: 48, borderLeft: '1px solid #1E1E22' }}>
              <div style={{ display: 'flex', color: '#888890', fontSize: 10, letterSpacing: 2 }}>CONS</div>
              <div style={{ display: 'flex', color: '#F0F0F0', fontSize: 44, fontWeight: 700, marginTop: 8 }}>{consistency}</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', marginLeft: 48, paddingLeft: 48, borderLeft: '1px solid #1E1E22' }}>
              <div style={{ display: 'flex', color: '#888890', fontSize: 10, letterSpacing: 2 }}>DEPTH</div>
              <div style={{ display: 'flex', color: '#F0F0F0', fontSize: 44, fontWeight: 700, marginTop: 8 }}>{depth}</div>
            </div>
          </div>

          {/* Chain indicator */}
          <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center' }}>
            <div style={{ width: 8, height: 8, borderRadius: 4, background: dotColour, marginRight: 8 }} />
            <div style={{ display: 'flex', color: '#888890', fontSize: 10, letterSpacing: 2 }}>{chainLabel}</div>
          </div>

        </div>
      </div>
    ),
    { width: 1500, height: 500 },
  )
}
