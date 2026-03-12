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
        <div style={{ display: 'flex', flexDirection: 'column', width: 560, paddingTop: 44, paddingLeft: 52 }}>
          <div style={{ display: 'flex', color: '#888890', fontSize: 11 }}>TESSERA PROTOCOL</div>
          <div style={{ display: 'flex', color: '#F0F0F0', fontSize: 64, fontWeight: 700, marginTop: 16 }}>@{cleanHandle}</div>
          <div style={{ display: 'flex', color: '#E8FF47', fontSize: 11, marginTop: 16 }}>UNSEALED</div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', width: 940, paddingTop: 44, paddingLeft: 52 }}>
          <div style={{ display: 'flex', color: '#888890', fontSize: 11 }}>COMPOSITE SCORE</div>
          <div style={{ display: 'flex', color: '#E8FF47', fontSize: 120, fontWeight: 700, marginTop: 8 }}>69.0</div>
        </div>
      </div>
    ),
    { width: 1500, height: 500 },
  )
}
