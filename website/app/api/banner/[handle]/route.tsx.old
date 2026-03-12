/**
 * GET /api/banner/[handle]
 *
 * Generates a 1500×500 PNG banner (X/Twitter header size) showing the
 * account's latest Tessera epoch scores.
 *
 * Unsealed accounts get a LIVE banner — updates on each request.
 * Sealed accounts get a locked banner representing that epoch.
 *
 * Usage:
 *   <img src="/api/banner/simplesimon872" />
 *   or right-click → Save Image → upload to X as header
 */

import { ImageResponse } from 'next/og'

export const runtime = 'edge'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Brand colours — must match tailwind.config.ts
const C = {
  bg:      '#0A0A0B',
  surface: '#111113',
  border:  '#1E1E22',
  muted:   '#888890',
  primary: '#F0F0F0',
  accent:  '#E8FF47',
  sealed:  '#4AFF91',
  dim:     '#2A2A2E',
}

function fmt(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—'
  return n.toFixed(1)
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ handle: string }> },
) {
  const { handle } = await params
  const cleanHandle = handle.toLowerCase().replace(/^@/, '')

  // ── Fetch profile ──────────────────────────────────────────────────────────
  let profile: any = null
  try {
    const res = await fetch(`${API_URL}/api/score/${cleanHandle}`)
    if (res.ok) {
      const json = await res.json()
      profile = json.ok ? json.data : null
    }
  } catch {
    // render a "no data" banner rather than 500
  }

  const epoch     = profile?.epochs?.[0] ?? null
  const scoresRaw = Array.isArray(epoch?.scores) ? epoch.scores[0] : epoch?.scores
  const anchor    = Array.isArray(epoch?.anchors) ? epoch.anchors[0] : epoch?.anchors
  const isSealed  = epoch?.status === 'sealed'
  const hasClaim  = profile?.claimed ?? false

  const composite   = scoresRaw?.composite   ?? null
  const originality = scoresRaw?.originality ?? null
  const focus       = scoresRaw?.focus       ?? null
  const consistency = scoresRaw?.consistency ?? null
  const depth       = scoresRaw?.depth       ?? null

  const epochStart = epoch?.epoch_start ? fmtDate(epoch.epoch_start) : null
  const epochEnd   = epoch?.epoch_end   ? fmtDate(epoch.epoch_end)   : null

  // ── Fetch fonts ────────────────────────────────────────────────────────────
  // Syne Bold (700) for display text, IBM Plex Mono Regular for data
  let syneData: ArrayBuffer | null = null
  let plexData: ArrayBuffer | null = null
  try {
    const [syneRes, plexRes] = await Promise.all([
      fetch('https://fonts.gstatic.com/s/syne/v22/8vIS7w4qzmVxsWxjBZRjr0FKM_04uQ.woff2'),
      fetch('https://fonts.gstatic.com/s/ibmplexmono/v19/-F6qfjhlbTKRTjr2NfkwnEMBnkQ.woff2'),
    ])
    syneData = await syneRes.arrayBuffer()
    plexData = await plexRes.arrayBuffer()
  } catch {
    // fonts optional — system fallback
  }

  const fonts: any[] = []
  if (syneData) fonts.push({ name: 'Syne',       data: syneData, weight: 700,  style: 'normal' })
  if (plexData) fonts.push({ name: 'IBMPlexMono', data: plexData, weight: 400,  style: 'normal' })

  // ── Pill component helper ──────────────────────────────────────────────────
  const statusColour = isSealed ? C.sealed : C.accent
  const statusLabel  = isSealed ? '◆ SEALED' : hasClaim ? '◇ LIVE' : '◇ UNSEALED'

  // ── Pillar row data ────────────────────────────────────────────────────────
  const pillars = [
    { label: 'ORIG',  value: fmt(originality) },
    { label: 'FOCUS', value: fmt(focus)       },
    { label: 'CONS',  value: fmt(consistency) },
    { label: 'DEPTH', value: fmt(depth)       },
  ]

  // ── Render ─────────────────────────────────────────────────────────────────
  return new ImageResponse(
    (
      <div
        style={{
          width:           1500,
          height:          500,
          background:      C.bg,
          display:         'flex',
          flexDirection:   'row',
          fontFamily:      'Syne, sans-serif',
          position:        'relative',
          overflow:        'hidden',
        }}
      >
        {/* ── Subtle grid lines for texture ─────────────────────────────── */}
        {/* Vertical accent bar far left */}
        <div style={{
          position:   'absolute',
          left:       0,
          top:        0,
          width:      6,
          height:     500,
          background: statusColour,
          opacity:    0.9,
        }} />

        {/* Horizontal hairline mid */}
        <div style={{
          position:   'absolute',
          left:       6,
          right:      0,
          top:        249,
          height:     1,
          background: C.border,
        }} />

        {/* Diagonal watermark lines — purely decorative */}
        <div style={{
          position:   'absolute',
          right:      -40,
          top:        -40,
          width:      500,
          height:     580,
          background: `repeating-linear-gradient(
            -45deg,
            transparent,
            transparent 28px,
            ${C.dim} 28px,
            ${C.dim} 29px
          )`,
          opacity: 0.25,
        }} />

        {/* ── LEFT PANEL — identity ─────────────────────────────────────── */}
        <div style={{
          display:        'flex',
          flexDirection:  'column',
          justifyContent: 'space-between',
          padding:        '44px 48px 44px 52px',
          width:          560,
          flexShrink:     0,
        }}>

          {/* Top: wordmark + status */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{
              fontFamily:  'IBMPlexMono, monospace',
              fontSize:    11,
              color:       C.muted,
              letterSpacing: '0.18em',
              textTransform: 'uppercase',
            }}>
              TESSERA PROTOCOL
            </div>

            <div style={{
              fontSize:    72,
              fontWeight:  700,
              color:       C.primary,
              lineHeight:  1,
              letterSpacing: '-0.03em',
            }}>
              @{cleanHandle}
            </div>

            <div style={{
              display:    'flex',
              alignItems: 'center',
              gap:        10,
            }}>
              <div style={{
                fontFamily:  'IBMPlexMono, monospace',
                fontSize:    11,
                color:       statusColour,
                letterSpacing: '0.12em',
                border:      `1px solid ${statusColour}40`,
                background:  `${statusColour}10`,
                padding:     '4px 10px',
              }}>
                {statusLabel}
              </div>
              {isSealed && anchor?.tx_hash && (
                <div style={{
                  fontFamily:  'IBMPlexMono, monospace',
                  fontSize:    10,
                  color:       C.muted,
                  letterSpacing: '0.06em',
                }}>
                  TX {anchor.tx_hash.slice(0, 12)}…
                </div>
              )}
            </div>
          </div>

          {/* Bottom: epoch dates + site */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {epochStart && epochEnd && (
              <div style={{
                fontFamily:  'IBMPlexMono, monospace',
                fontSize:    11,
                color:       C.muted,
                letterSpacing: '0.08em',
              }}>
                {epochStart} → {epochEnd}
              </div>
            )}
            <div style={{
              fontFamily:  'IBMPlexMono, monospace',
              fontSize:    11,
              color:       C.border,
              letterSpacing: '0.08em',
            }}>
              tessera-8x7.pages.dev
            </div>
          </div>
        </div>

        {/* ── DIVIDER ───────────────────────────────────────────────────── */}
        <div style={{
          width:      1,
          background: C.border,
          margin:     '40px 0',
          flexShrink: 0,
        }} />

        {/* ── RIGHT PANEL — scores ──────────────────────────────────────── */}
        <div style={{
          display:        'flex',
          flexDirection:  'column',
          justifyContent: 'space-between',
          padding:        '44px 52px 44px 52px',
          flex:           1,
        }}>

          {/* Composite */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{
              fontFamily:  'IBMPlexMono, monospace',
              fontSize:    11,
              color:       C.muted,
              letterSpacing: '0.18em',
              textTransform: 'uppercase',
            }}>
              COMPOSITE SCORE
            </div>
            <div style={{
              fontSize:    120,
              fontWeight:  700,
              color:       composite !== null ? C.accent : C.border,
              lineHeight:  1,
              letterSpacing: '-0.04em',
            }}>
              {fmt(composite)}
            </div>
          </div>

          {/* Four pillars */}
          <div style={{
            display:       'flex',
            flexDirection: 'row',
            gap:           0,
          }}>
            {pillars.map(({ label, value }, i) => (
              <div
                key={label}
                style={{
                  display:        'flex',
                  flexDirection:  'column',
                  gap:            8,
                  flex:           1,
                  borderLeft:     i > 0 ? `1px solid ${C.border}` : 'none',
                  paddingLeft:    i > 0 ? 24 : 0,
                }}
              >
                <div style={{
                  fontFamily:  'IBMPlexMono, monospace',
                  fontSize:    10,
                  color:       C.muted,
                  letterSpacing: '0.16em',
                }}>
                  {label}
                </div>
                <div style={{
                  fontSize:    36,
                  fontWeight:  700,
                  color:       value === '—' ? C.border : C.primary,
                  letterSpacing: '-0.02em',
                  lineHeight:  1,
                }}>
                  {value}
                </div>
              </div>
            ))}
          </div>

          {/* Avalanche indicator */}
          <div style={{
            display:    'flex',
            alignItems: 'center',
            gap:        8,
          }}>
            <div style={{
              width:      6,
              height:     6,
              borderRadius: 3,
              background: isSealed ? C.sealed : C.border,
            }} />
            <div style={{
              fontFamily:  'IBMPlexMono, monospace',
              fontSize:    10,
              color:       C.muted,
              letterSpacing: '0.12em',
            }}>
              {isSealed ? 'AVALANCHE C-CHAIN MAINNET' : 'PENDING SEAL'}
            </div>
          </div>
        </div>
      </div>
    ),
    {
      width:  1500,
      height: 500,
      fonts,
    },
  )
}
