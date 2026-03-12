/**
 * GET /api/banner/[handle]
 * Step 3 - no position:absolute, no .map(), no dynamic data
 */

import { ImageResponse } from 'next/og'

export const runtime = 'edge'

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ handle: string }> },
) {
  const { handle } = await params
  const cleanHandle = handle.toLowerCase().replace(/^@/, '')

  return new ImageResponse(
    (
      <div
        style={{
          width:           1500,
          height:          500,
          backgroundColor: '#0A0A0B',
          display:         'flex',
          flexDirection:   'row',
        }}
      >
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
          borderRight:    '1px solid #1E1E22',
        }}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ fontSize: 11, color: '#888890', fontFamily: 'sans-serif', marginBottom: 16 }}>
              TESSERA PROTOCOL
            </div>
            <div style={{ fontSize: 64, fontWeight: 700, color: '#F0F0F0', lineHeight: 1, fontFamily: 'sans-serif', marginBottom: 20 }}>
              @{cleanHandle}
            </div>
            <div style={{ display: 'flex', fontSize: 11, color: '#E8FF47', fontFamily: 'sans-serif' }}>
              UNSEALED
            </div>
          </div>
          <div style={{ fontSize: 11, color: '#2A2A2E', fontFamily: 'sans-serif' }}>
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
            <div style={{ fontSize: 11, color: '#888890', fontFamily: 'sans-serif', marginBottom: 8 }}>
              COMPOSITE SCORE
            </div>
            <div style={{ fontSize: 148, fontWeight: 700, color: '#E8FF47', lineHeight: 1, fontFamily: 'sans-serif' }}>
              69.0
            </div>
          </div>

          {/* Pillars - no map, explicit */}
          <div style={{ display: 'flex', flexDirection: 'row' }}>
            <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
              <div style={{ fontSize: 10, color: '#888890', fontFamily: 'sans-serif', marginBottom: 8 }}>ORIG</div>
              <div style={{ fontSize: 44, fontWeight: 700, color: '#F0F0F0', lineHeight: 1, fontFamily: 'sans-serif' }}>72.0</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', flex: 1, borderLeft: '1px solid #1E1E22', paddingLeft: 24 }}>
              <div style={{ fontSize: 10, color: '#888890', fontFamily: 'sans-serif', marginBottom: 8 }}>FOCUS</div>
              <div style={{ fontSize: 44, fontWeight: 700, color: '#F0F0F0', lineHeight: 1, fontFamily: 'sans-serif' }}>81.0</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', flex: 1, borderLeft: '1px solid #1E1E22', paddingLeft: 24 }}>
              <div style={{ fontSize: 10, color: '#888890', fontFamily: 'sans-serif', marginBottom: 8 }}>CONS</div>
              <div style={{ fontSize: 44, fontWeight: 700, color: '#F0F0F0', lineHeight: 1, fontFamily: 'sans-serif' }}>65.0</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', flex: 1, borderLeft: '1px solid #1E1E22', paddingLeft: 24 }}>
              <div style={{ fontSize: 10, color: '#888890', fontFamily: 'sans-serif', marginBottom: 8 }}>DEPTH</div>
              <div style={{ fontSize: 44, fontWeight: 700, color: '#F0F0F0', lineHeight: 1, fontFamily: 'sans-serif' }}>58.0</div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center' }}>
            <div style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: '#1E1E22', marginRight: 8 }} />
            <div style={{ fontSize: 10, color: '#888890', fontFamily: 'sans-serif' }}>PENDING SEAL</div>
          </div>
        </div>
      </div>
    ),
    { width: 1500, height: 500 },
  )
}
