/**
 * GET /api/banner/[handle]
 * Minimal test version - hardcoded to confirm ImageResponse works on Cloudflare edge
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
          width:          1500,
          height:         500,
          background:     '#0A0A0B',
          display:        'flex',
          alignItems:     'center',
          justifyContent: 'center',
          color:          '#E8FF47',
          fontSize:       80,
          fontWeight:     700,
        }}
      >
        @{cleanHandle}
      </div>
    ),
    {
      width:  1500,
      height: 500,
    },
  )
}
