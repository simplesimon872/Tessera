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
      <div style={{ width: 1500, height: 500, background: '#0A0A0B', display: 'flex', flexDirection: 'row' }}>

        {/* LEFT PANEL */}
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', width: 560, paddingTop: 44, paddingBottom: 44, paddingLeft: 52, paddingRight: 48, borderRight: '1px solid #1E1E22' }}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', color: '#888890', fontSize: 11, letterSpacing: 3 }}>TESSERA PROTOCOL</div>
            <div style={{ display: 'flex', color: '#F0F0F0', fontSize: 64, fontWeight: 700, marginTop: 16 }}>@{cleanHandle}</div>
            <div style={{ display: 'flex', color: '#E8FF47', fontSize: 11, marginTop: 16, letterSpacing: 2 }}>UNSEALED</div>
          </div>
          <div style={{ display: 'flex', color: '#2A2A2E', fontSize: 11 }}>tessera-8x7.pages.dev</div>
        </div>

        {/* RIGHT PANEL */}
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', width: 940, paddingTop: 44, paddingBottom: 44, paddingLeft: 52, paddingRight: 60 }}>

          {/* Composite */}
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', color: '#888890', fontSize: 11, letterSpacing: 3 }}>COMPOSITE SCORE</div>
            <div style={{ display: 'flex', color: '#E8FF47', fontSize: 120, fontWeight: 700, marginTop: 4 }}>69.0</div>
          </div>

          {/* Pillars */}
          <div style={{ display: 'flex', flexDirection: 'row' }}>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', color: '#888890', fontSize: 10, letterSpacing: 2 }}>ORIG</div>
              <div style={{ display: 'flex', color: '#F0F0F0', fontSize: 44, fontWeight: 700, marginTop: 8 }}>72.0</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', marginLeft: 48, paddingLeft: 48, borderLeft: '1px solid #1E1E22' }}>
              <div style={{ display: 'flex', color: '#888890', fontSize: 10, letterSpacing: 2 }}>FOCUS</div>
              <div style={{ display: 'flex', color: '#F0F0F0', fontSize: 44, fontWeight: 700, marginTop: 8 }}>81.0</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', marginLeft: 48, paddingLeft: 48, borderLeft: '1px solid #1E1E22' }}>
              <div style={{ display: 'flex', color: '#888890', fontSize: 10, letterSpacing: 2 }}>CONS</div>
              <div style={{ display: 'flex', color: '#F0F0F0', fontSize: 44, fontWeight: 700, marginTop: 8 }}>65.0</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', marginLeft: 48, paddingLeft: 48, borderLeft: '1px solid #1E1E22' }}>
              <div style={{ display: 'flex', color: '#888890', fontSize: 10, letterSpacing: 2 }}>DEPTH</div>
              <div style={{ display: 'flex', color: '#F0F0F0', fontSize: 44, fontWeight: 700, marginTop: 8 }}>58.0</div>
            </div>
          </div>

          {/* Chain indicator */}
          <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center' }}>
            <div style={{ width: 8, height: 8, borderRadius: 4, background: '#1E1E22', marginRight: 8 }} />
            <div style={{ display: 'flex', color: '#888890', fontSize: 10, letterSpacing: 2 }}>PENDING SEAL</div>
          </div>

        </div>
      </div>
    ),
    { width: 1500, height: 500 },
  )
}
