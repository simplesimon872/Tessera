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

  let profile: any = null
  try {
    const res = await fetch(`${API_URL}/api/score/${cleanHandle}`)
    if (res.ok) {
      const json = await res.json()
      profile = json.ok ? json.data : null
    }
  } catch { /* no-data banner */ }

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

  // Avatar safe zone: ~220px from left, ~180px diameter, bottom-left
  // We clear the bottom-left ~280px wide x 220px tall
  // Left panel starts at 300px to keep identity text clear of avatar
  // Composite sits far right — completely safe

  return new ImageResponse(
    (
      <div style={{ width: 1500, height: 500, background: '#0A0A0B', display: 'flex', flexDirection: 'column' }}>

        {/* Top accent bar */}
        <div style={{ display: 'flex', width: 1500, height: 5, background: statusColour }} />

        {/* TOP ROW — full width header */}
        <div style={{
          display: 'flex',
          flexDirection: 'row',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
          paddingTop: 32,
          paddingLeft: 52,
          paddingRight: 52,
          paddingBottom: 20,
          borderBottom: '1px solid #1E1E22',
        }}>
          {/* Left — wordmark + handle */}
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', color: '#888890', fontSize: 16, letterSpacing: 3, marginBottom: 10 }}>
              TESSERA PROTOCOL
            </div>
            <div style={{ display: 'flex', color: '#F0F0F0', fontSize: 68, fontWeight: 700, lineHeight: 1 }}>
              @{cleanHandle}
            </div>
          </div>

          {/* Right — status + dates */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
            <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
              <div style={{ display: 'flex', color: statusColour, fontSize: 13, letterSpacing: 3, fontWeight: 600 }}>
                {statusLabel}
              </div>
              {txShort ? (
                <div style={{ display: 'flex', color: '#888890', fontSize: 10, marginLeft: 16 }}>
                  TX {txShort}
                </div>
              ) : null}
            </div>
            {dateLine ? (
              <div style={{ display: 'flex', color: '#888890', fontSize: 11 }}>{dateLine}</div>
            ) : null}
          </div>
        </div>

        {/* BOTTOM ROW — avatar safe zone left, scores right */}
        <div style={{ display: 'flex', flexDirection: 'row', flex: 1 }}>

          {/* AVATAR SAFE ZONE — left ~300px kept intentionally sparse */}
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'flex-start',
            width: 300,
            paddingTop: 20,
            paddingLeft: 52,
          }}>
            {/* Just the site URL tucked top-left — above where avatar lands */}
            <div style={{ display: 'flex', color: '#2A2A2E', fontSize: 11, letterSpacing: 1 }}>
              tessera-8x7.pages.dev
            </div>
          </div>

          {/* PILLARS — centre, clear of avatar */}
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            flex: 1,
            paddingLeft: 40,
            paddingRight: 40,
            borderLeft: '1px solid #1E1E22',
            borderRight: '1px solid #1E1E22',
          }}>
            <div style={{ display: 'flex', color: '#888890', fontSize: 10, letterSpacing: 3, marginBottom: 14 }}>
              BEHAVIORAL SCORES
            </div>
            <div style={{ display: 'flex', flexDirection: 'row' }}>
              <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
                <div style={{ display: 'flex', color: '#888890', fontSize: 10, letterSpacing: 2, marginBottom: 8 }}>ORIGINALITY</div>
                <div style={{ display: 'flex', color: '#F0F0F0', fontSize: 48, fontWeight: 700 }}>{originality}</div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', flex: 1, borderLeft: '1px solid #1E1E22', paddingLeft: 28 }}>
                <div style={{ display: 'flex', color: '#888890', fontSize: 10, letterSpacing: 2, marginBottom: 8 }}>FOCUS</div>
                <div style={{ display: 'flex', color: '#F0F0F0', fontSize: 48, fontWeight: 700 }}>{focus}</div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', flex: 1, borderLeft: '1px solid #1E1E22', paddingLeft: 28 }}>
                <div style={{ display: 'flex', color: '#888890', fontSize: 10, letterSpacing: 2, marginBottom: 8 }}>CONSISTENCY</div>
                <div style={{ display: 'flex', color: '#F0F0F0', fontSize: 48, fontWeight: 700 }}>{consistency}</div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', flex: 1, borderLeft: '1px solid #1E1E22', paddingLeft: 28 }}>
                <div style={{ display: 'flex', color: '#888890', fontSize: 10, letterSpacing: 2, marginBottom: 8 }}>DEPTH</div>
                <div style={{ display: 'flex', color: '#F0F0F0', fontSize: 48, fontWeight: 700 }}>{depth}</div>
              </div>
            </div>
          </div>

          {/* COMPOSITE — far right, totally safe from avatar */}
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            width: 300,
            paddingLeft: 32,
            paddingRight: 52,
          }}>
            <div style={{ display: 'flex', color: '#888890', fontSize: 10, letterSpacing: 3, marginBottom: 10 }}>
              COMPOSITE
            </div>
            <div style={{ display: 'flex', color: scoreColour, fontSize: 110, fontWeight: 700, lineHeight: 1 }}>
              {composite}
            </div>
            <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', marginTop: 14 }}>
              <div style={{ width: 7, height: 7, borderRadius: 4, background: dotColour, marginRight: 7 }} />
              <div style={{ display: 'flex', color: '#888890', fontSize: 9, letterSpacing: 2 }}>
                {chainLabel}
              </div>
            </div>
          </div>

        </div>
      </div>
    ),
    { width: 1500, height: 500 },
  )
}
