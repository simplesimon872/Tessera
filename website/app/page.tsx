import Link from 'next/link'
import HandleSearchInput from '@/components/HandleSearchInput'
import { getLeaderboard } from '@/lib/api'

export const runtime = 'edge'

export const metadata = {
  title: 'Tessera — Onchain Behavioral Reputation',
  description: 'Cryptographically sealed behavioral scores for Arena social accounts.',
}

export default async function HomePage() {
  let topEntries: any[] = []
  try {
    const leaderboard = await getLeaderboard()
    topEntries = (leaderboard?.entries as unknown as any[])?.slice(0, 3) ?? []
  } catch {
    topEntries = []
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-16">

      {/* Hero */}
      <div className="fade-in fade-in-1 mb-20">
        <p className="font-mono text-xs text-accent tracking-widest uppercase mb-4">
          Behavioral reputation protocol
        </p>
        <h1 className="font-sans font-extrabold text-5xl sm:text-7xl tracking-tight leading-none mb-6">
          Tessera
        </h1>
        <p className="font-sans text-muted text-lg max-w-xl mb-12">
          Cryptographically sealed behavioral scores for Arena social accounts.
          Originality. Focus. Consistency. Depth. Anchored onchain.
        </p>

        {/* Search */}
        <div className="max-w-md">
          <p className="font-mono text-xs text-muted tracking-widest uppercase mb-3">
            Look up a handle
          </p>
          <HandleSearchInput />
        </div>
      </div>

      {/* How it works */}
      <div className="fade-in fade-in-2 mb-20">
        <p className="font-mono text-xs text-muted tracking-widest uppercase mb-8">
          How it works
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-px bg-border">
          {[
            { step: '01', title: 'Score', desc: 'Posts are analyzed across four behavioral dimensions each epoch.' },
            { step: '02', title: 'Seal', desc: 'Epoch scores are hashed and anchored to Avalanche C-Chain.' },
            { step: '03', title: 'Verify', desc: 'Anyone can verify a score against the onchain record.' },
          ].map(({ step, title, desc }) => (
            <div key={step} className="bg-bg p-8">
              <p className="font-mono text-xs text-accent mb-4">{step}</p>
              <p className="font-sans font-bold text-lg mb-2">{title}</p>
              <p className="font-sans text-sm text-muted">{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Top 3 preview */}
      {topEntries.length > 0 && (
        <div className="fade-in fade-in-3 mb-12">
          <div className="flex items-center justify-between mb-6">
            <p className="font-mono text-xs text-muted tracking-widest uppercase">
              Top accounts
            </p>
            <Link href="/leaderboard" className="font-mono text-xs text-accent hover:text-primary transition-colors">
              VIEW ALL →
            </Link>
          </div>
          <div className="space-y-px">
            {topEntries.map((entry: any, i: number) => (
              <Link
                key={entry.handle}
                href={`/${entry.handle}`}
                className="flex items-center justify-between bg-surface border-b border-border px-6 py-4 hover:bg-border/20 transition-colors group"
              >
                <div className="flex items-center gap-4">
                  <span className="font-mono text-xs text-muted w-4">{i + 1}</span>
                  <span className="font-mono text-sm">@{entry.handle}</span>
                </div>
                <div className="flex items-center gap-6">
                  <span className="font-mono text-sm text-accent">{entry.composite?.toFixed(1) ?? '—'}</span>
                  <span className="font-mono text-xs text-muted group-hover:translate-x-1 transition-transform">→</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* CTA */}
      <div className="fade-in fade-in-4 border border-border p-8">
        <p className="font-mono text-xs text-accent mb-3">CLAIM YOUR TESSERA</p>
        <p className="font-sans text-sm text-muted mb-6">
          Tag <span className="font-mono text-primary">@bannerusmaximus claim</span> on Arena
          to activate your behavioral record and start accruing sealed epochs.
        </p>
        <div className="flex flex-wrap gap-4">
          <a
            href="https://arena.social"
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-xs text-bg bg-accent px-4 py-2 hover:bg-primary transition-colors"
          >
            Open Arena →
          </a>
          <Link
            href="/leaderboard"
            className="font-mono text-xs text-muted border border-border px-4 py-2 hover:text-primary hover:border-primary transition-colors"
          >
            View leaderboard →
          </Link>
        </div>
      </div>

    </div>
  )
}
