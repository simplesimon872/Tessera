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
      <div style={{ width: 1500, height: 500, background: '#0A0A0B', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ display: 'flex', color: '#E8FF47', fontSize: 80, fontWeight: 700 }}>
          @{cleanHandle}
        </div>
        <div style={{ display: 'flex', color: '#F0F0F0', fontSize: 80, fontWeight: 700, marginLeft: 40 }}>
          69.0
        </div>
      </div>
    ),
    { width: 1500, height: 500 },
  )
}
