/**
 * GET /api/banner/[handle]
 * Step 2 test - full layout with hardcoded data, no fetch
 */

import { ImageResponse } from 'next/og'

export const runtime = 'edge'

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ handle: string }> },
) {
  const { handle } = await params
  const cleanHandle = handle.toLowerCase().replace(/^@/, '')

  const statusColour = '#E8FF47'
  const pillars = [
    { label: 'ORIG',  value: '72.0' },
    { label: 'FOCUS', value: '81.0' },
    { label: 'CONS',  value: '65.0' },
    { label: 'DEPTH', value: '58.0' },
  ]

  return new ImageResponse(
    (
      <div
        style={{
          width:           1500,
          height:          500,
          backgroundColor: '#0A0A0B',
          display:         'flex',
          flexDirection:   'row',
          position:        'relative',
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

        {/* LEFT PANEL */}
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
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{
              fontSize:    11,
              color:       '#888890',
              marginBottom: 16,
              fontFamily:  'sans-serif',
            }}>
              TESSERA PROTOCOL
            </div>
            <div style={{
              fontSize:    64,
              fontWeight:  700,
              color:       '#F0F0F0',
              lineHeight:  1,
              fontFamily:  'sans-serif',
              marginBottom: 20,
            }}>
              @{cleanHandle}
            </div>
            <div style={{
              display:         'flex',
              fontSize:        11,
              color:           statusColour,
              border:          '1px solid #E8FF4750',
              backgroundColor: '#E8FF4715',
              paddingTop:      4,
              paddingBottom:   4,
              paddingLeft:     12,
              paddingRight:    12,
              fontFamily:      'sans-serif',
            }}>
              UNSEALED
            </div>
          </div>
          <div style={{
            fontSize:   11,
            color:      '#2A2A2E',
            fontFamily: 'sans-serif',
          }}>
            tessera-8x7.pages.dev
          </div>
        </div>

        {/* RIGHT PANEL */}
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
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{
              fontSize:    11,
              color:       '#888890',
              fontFamily:  'sans-serif',
              marginBottom: 8,
            }}>
              COMPOSITE SCORE
            </div>
            <div style={{
              fontSize:   148,
              fontWeight: 700,
              color:      '#E8FF47',
              lineHeight: 1,
              fontFamily: 'sans-serif',
            }}>
              69.0
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'row' }}>
            {pillars.map(({ label, value }, i) => (
              <div
                key={label}
                style={{
                  display:       'flex',
                  flexDirection: 'column',
                  flex:          1,
                  borderLeft:    i > 0 ? '1px solid #1E1E22' : 'none',
                  paddingLeft:   i > 0 ? 24 : 0,
                }}
              >
                <div style={{
                  fontSize:    10,
                  color:       '#888890',
                  fontFamily:  'sans-serif',
                  marginBottom: 8,
                }}>
                  {label}
                </div>
                <div style={{
                  fontSize:   44,
                  fontWeight: 700,
                  color:      '#F0F0F0',
                  lineHeight: 1,
                  fontFamily: 'sans-serif',
                }}>
                  {value}
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center' }}>
            <div style={{
              width:           8,
              height:          8,
              borderRadius:    4,
              backgroundColor: '#1E1E22',
              marginRight:     8,
            }} />
            <div style={{
              fontSize:   10,
              color:      '#888890',
              fontFamily: 'sans-serif',
            }}>
              PENDING SEAL
            </div>
          </div>
        </div>
      </div>
    ),
    { width: 1500, height: 500 },
  )
}
