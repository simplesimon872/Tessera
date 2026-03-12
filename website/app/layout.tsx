import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  metadataBase: new URL('https://tessera-8x7.pages.dev'),
  title: 'Tessera — Onchain Behavioral Attestation',
  description: 'Verifiable behavioral records for Arena social accounts. Sealed onchain on Avalanche.',
  openGraph: {
    title: 'Tessera',
    description: 'Onchain behavioral attestation protocol for Arena.',
    type: 'website',
    url: 'https://tessera-8x7.pages.dev',
  },
  icons: {
    icon: '/tessera-icon-lg.svg',
    shortcut: '/tessera-icon-lg.svg',
  },
}

// Inline SVG icon component — 3x3 grid, centre tile accent coloured
function TesseraIcon({ size = 20, sealed = false }: { size?: number, sealed?: boolean }) {
  const accent = sealed ? '#4AFF91' : '#E8FF47'
  const dim = '#2A2A2E'
  const gap = size * 0.1
  const tile = (size - gap * 2) / 3

  const pos = (i: number) => i * (tile + gap)

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} xmlns="http://www.w3.org/2000/svg">
      {[0, 1, 2].flatMap(row =>
        [0, 1, 2].map(col => (
          <rect
            key={`${row}-${col}`}
            x={pos(col)}
            y={pos(row)}
            width={tile}
            height={tile}
            fill={row === 1 && col === 1 ? accent : dim}
            rx={size * 0.03}
          />
        ))
      )}
    </svg>
  )
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-bg text-primary min-h-screen">
        <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border bg-bg/80 backdrop-blur-sm">
          <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
            <a href="/" className="font-sans font-bold text-lg tracking-tight flex items-center gap-3">
              <TesseraIcon size={22} />
              <span>Tessera</span>
            </a>
            <div className="flex items-center gap-6">
              <a
                href="/leaderboard"
                className="font-mono text-xs text-muted hover:text-primary transition-colors tracking-wider uppercase"
              >
                Leaderboard
              </a>
              <a
                href="https://arena.social/?ref=SimpleSimon872"
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-xs bg-accent text-bg px-3 py-1.5 hover:bg-primary transition-colors tracking-wider uppercase font-medium"
              >
                Try it →
              </a>
            </div>
          </div>
        </nav>
        <main className="pt-14">
          {children}
        </main>
        <footer className="border-t border-border mt-32">
          <div className="max-w-5xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <TesseraIcon size={18} />
              <span className="font-sans font-semibold text-sm">Tessera</span>
            </div>
            <p className="font-mono text-xs text-muted">
              Deterministic scoring · Onchain attestation · Avalanche C-Chain
            </p>
          </div>
        </footer>
      </body>
    </html>
  )
}
