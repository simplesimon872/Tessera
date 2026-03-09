import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Tessera — Onchain Behavioral Attestation',
  description: 'Verifiable behavioral records for Arena social accounts. Sealed onchain on Avalanche.',
  openGraph: {
    title: 'Tessera',
    description: 'Onchain behavioral attestation protocol for Arena.',
    type: 'website',
  },
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
            <a href="/" className="font-sans font-bold text-lg tracking-tight flex items-center gap-2">
              <span className="text-accent">◆</span>
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
                href="https://arena.social"
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
            <div className="flex items-center gap-2">
              <span className="text-accent text-sm">◆</span>
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
