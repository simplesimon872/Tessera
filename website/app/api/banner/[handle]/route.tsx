/**
 * GET /api/banner/[handle]
 *
 * Returns a 1500x500 PNG banner using ImageResponse.
 * X/Twitter header size. Also used as OG image for profile pages.
 *
 * ImageResponse JSX rules (Satori under the hood):
 *  - All elements need display:flex explicitly
 *  - No shorthand CSS (no gap, no border shorthand)
 *  - No CSS gradients on pseudo-elements
 *  - position:absolute requires parent to have position:relative
 *  - No overflow on children
 */

import { ImageResponse } from 'next/og'

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

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ handle: string }> },
) {
  const { handle } = await params
  const cleanHandle = handle.toLowerCase().replace(/^@/, '')

  // Fetch profile
  let profile: any = null
  try {
    const res = await fetch(`${API_URL}/api/score/${cleanHandle}`)
    if (res.ok) {
      const json = await res.json()
      profile = json.ok ? json.data : null
    }
  } catch {
    // render no-data banner
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

  const txShort      = anchor?.tx_hash ? (anchor.tx_hash as string).slice(0, 14) + '...' : ''
  const statusLabel  = isSealed ? 'SEALED' : hasClaim ? 'LIVE' : 'UNSEALED'
  const statusColour = isSealed ? '#4AFF91' : '#E8FF47'
  const chainLabel   = isSealed ? 'AVALANCHE C-CHAIN MAINNET' : 'PENDING SEAL'
  const dotColour    = isSealed ? '#4AFF91' : '#1E1E22'

  const pillars = [
    { label: 'ORIG',  value: originality },
    { label: 'FOCUS', value: focus       },
    { label: 'CONS',  value: consistency },
    { label: 'DEPTH', value: depth       },
  ]

  return new ImageResponse(
    (
      <div
        style={{
          width:          1500,
          height:         500,
          backgroundColor: '#0A0A0B',
          display:        'flex',
          flexDirection:  'row',
          position:       'relative',
        }}
      >
        {/* Left accent bar */}
        <div style={{
          position:        'absolute',
          left:            0,
          top:             0,
          width:           6,
          height:          500,
          backgroundColor: statusColour,
          display:         'flex',
        }} />

        {/* Horizontal hairline */}
        <div style={{
          position:        'absolute',
          left:            6,
          top:             249,
          width:           1494,
          height:          1,
          backgroundColor: '#1E1E22',
          display:         'flex',
        }} />

        {/* Vertical panel divider */}
        <div style={{
          position:        'absolute',
          left:            566,
          top:             40,
          width:           1,
          height:          420,
          backgroundColor: '#1E1E22',
          display:         'flex',
        }} />

        {/* Stripe decoration — top right, using stacked divs */}
        {[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14].map((i) => (
          <div
            key={i}
            style={{
              position:        'absolute',
              right:           -20 + (i * 30),
              top:             -20,
              width:           1,
              height:          580,
              backgroundColor: '#1A1A1E',
              transform:       'rotate(45deg)',
              display:         'flex',
            }}
          />
        ))}

        {/* ── LEFT PANEL ── */}
        <div style={{
          display:        'flex',
          flexDirection:  'column',
          justifyContent: 'space-between',
          paddingTop:     44,
          paddingBottom:  44,
          paddingLeft:    52,
          paddingRight:   48,
          width:          560,
        }}>

          {/* Top */}
          <div style={{ display: 'flex', flexDirection: 'column' }}>

            <div style={{
              fontSize:      11,
              color:         '#888890',
              letterSpacing: '3px',
              fontFamily:    'sans-serif',
              marginBottom:  16,
            }}>
              TESSERA PROTOCOL
            </div>

            <div style={{
              fontSize:      64,
              fontWeight:    700,
              color:         '#F0F0F0',
              lineHeight:    1,
              letterSpacing: '-1px',
              fontFamily:    'sans-serif',
              marginBottom:  20,
            }}>
              @{cleanHandle}
            </div>

            {/* Status pill */}
            <div style={{
              display:         'flex',
              flexDirection:   'row',
              alignItems:      'center',
            }}>
              <div style={{
                display:         'flex',
                fontSize:        11,
                color:           statusColour,
                letterSpacing:   '2px',
                border:          `1px solid ${statusColour}50`,
                backgroundColor: `${statusColour}15`,
                paddingTop:      4,
                paddingBottom:   4,
                paddingLeft:     12,
                paddingRight:    12,
                fontFamily:      'sans-serif',
                marginRight:     12,
              }}>
                {statusLabel}
              </div>
              {txShort && (
                <div style={{
                  display:    'flex',
                  fontSize:   10,
                  color:      '#888890',
                  fontFamily: 'sans-serif',
                }}>
                  TX {txShort}
                </div>
              )}
            </div>
          </div>

          {/* Bottom */}
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {dateLine && (
              <div style={{
                fontSize:      11,
                color:         '#888890',
                letterSpacing: '1px',
                fontFamily:    'sans-serif',
                marginBottom:  8,
              }}>
                {dateLine}
              </div>
            )}
            <div style={{
              fontSize:      11,
              color:         '#2A2A2E',
              letterSpacing: '1px',
              fontFamily:    'sans-serif',
            }}>
              tessera-8x7.pages.dev
            </div>
          </div>
        </div>

        {/* ── RIGHT PANEL ── */}
        <div style={{
          display:        'flex',
          flexDirection:  'column',
          justifyContent: 'space-between',
          paddingTop:     44,
          paddingBottom:  44,
          paddingLeft:    52,
          paddingRight:   60,
          flex:           1,
        }}>

          {/* Composite */}
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{
              fontSize:      11,
              color:         '#888890',
              letterSpacing: '3px',
              fontFamily:    'sans-serif',
              marginBottom:  8,
            }}>
              COMPOSITE SCORE
            </div>
            <div style={{
              fontSize:      148,
              fontWeight:    700,
              color:         composite !== '--' ? '#E8FF47' : '#1E1E22',
              lineHeight:    1,
              letterSpacing: '-4px',
              fontFamily:    'sans-serif',
            }}>
              {composite}
            </div>
          </div>

          {/* Four pillars */}
          <div style={{
            display:       'flex',
            flexDirection: 'row',
          }}>
            {pillars.map(({ label, value }, i) => (
              <div
                key={label}
                style={{
                  display:         'flex',
                  flexDirection:   'column',
                  flex:            1,
                  borderLeft:      i > 0 ? '1px solid #1E1E22' : 'none',
                  paddingLeft:     i > 0 ? 24 : 0,
                }}
              >
                <div style={{
                  fontSize:      10,
                  color:         '#888890',
                  letterSpacing: '2px',
                  fontFamily:    'sans-serif',
                  marginBottom:  8,
                }}>
                  {label}
                </div>
                <div style={{
                  fontSize:      44,
                  fontWeight:    700,
                  color:         value === '--' ? '#1E1E22' : '#F0F0F0',
                  letterSpacing: '-1px',
                  lineHeight:    1,
                  fontFamily:    'sans-serif',
                }}>
                  {value}
                </div>
              </div>
            ))}
          </div>

          {/* Chain indicator */}
          <div style={{
            display:    'flex',
            flexDirection: 'row',
            alignItems: 'center',
          }}>
            <div style={{
              width:           8,
              height:          8,
              borderRadius:    4,
              backgroundColor: dotColour,
              marginRight:     8,
            }} />
            <div style={{
              fontSize:      10,
              color:         '#888890',
              letterSpacing: '2px',
              fontFamily:    'sans-serif',
            }}>
              {chainLabel}
            </div>
          </div>

        </div>
      </div>
    ),
    {
      width:  1500,
      height: 500,
    },
  )
}
