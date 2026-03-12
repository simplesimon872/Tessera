/**
 * Step 4 - two columns, no borders, no borderRadius, no flex:1, no lineHeight
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
      <div style={{ width: 1500, height: 500, backgroundColor: '#0A0A0B', display: 'flex', flexDirection: 'row' }}>

        <div style={{ display: 'flex', flexDirection: 'column', width: 560, paddingTop: 44, paddingLeft: 52 }}>
          <div style={{ fontSize: 11, color: '#888890', fontFamily: 'sans-serif' }}>TESSERA PROTOCOL</div>
          <div style={{ fontSize: 64, fontWeight: 700, color: '#F0F0F0', fontFamily: 'sans-serif', marginTop: 16 }}>@{cleanHandle}</div>
          <div style={{ fontSize: 11, color: '#E8FF47', fontFamily: 'sans-serif', marginTop: 16 }}>UNSEALED</div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', width: 940, paddingTop: 44, paddingLeft: 52 }}>
          <div style={{ fontSize: 11, color: '#888890', fontFamily: 'sans-serif' }}>COMPOSITE SCORE</div>
          <div style={{ fontSize: 148, fontWeight: 700, color: '#E8FF47', fontFamily: 'sans-serif', marginTop: 8 }}>69.0</div>
        </div>

      </div>
    ),
    { width: 1500, height: 500 },
  )
}
