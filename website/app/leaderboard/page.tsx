import { getLeaderboard, formatDate, formatScore } from '@/lib/api'
import Link from 'next/link'

export const metadata = {
  title: 'Leaderboard — Tessera',
  description: 'Top behavioral scores across all registered Tessera accounts.',
}

export default async function LeaderboardPage() {
  const entries = await getLeaderboard()

  return (
    <div className="max-w-5xl mx-auto px-6 py-16">

      {/* Header */}
      <div className="fade-in fade-in-1 mb-12 border-b border-border pb-12">
        <p className="font-mono text-xs text-muted tracking-widest uppercase mb-4">
          Tessera Protocol
        </p>
        <h1 className="font-sans font-extrabold text-5xl tracking-tight mb-4">
          Leaderboard
        </h1>
        <p className="font-sans text-muted text-sm max-w-lg">
          Ranked by composite score across the most recent sealed epoch.
          All scores are deterministic and onchain-verified.
        </p>
      </div>

      {entries.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          {/* Top 3 podium */}
          {entries.length >= 3 && (
            <div className="fade-in fade-in-2 grid grid-cols-3 gap-px bg-border mb-px">
              {[entries[1], entries[0], entries[2]].map((entry, i) => {
                const rank = i === 1 ? 1 : i === 0 ? 2 : 3
                const isFirst = rank === 1
                return (
                  <Link
                    key={entry.handle}
                    href={`/${entry.handle}`}
                    className="bg-bg p-6 text-center hover:bg-surface transition-colors group"
                  >
                    <p className={`font-mono text-xs mb-4 ${isFirst ? 'text-accent' : 'text-muted'}`}>
                      #{rank}
                    </p>
                    <p className={`font-mono text-3xl font-medium mb-2 ${isFirst ? 'text-accent' : 'text-primary'}`}>
                      {formatScore(entry.composite)}
                    </p>
                    <p className="font-sans font-bold text-sm group-hover:text-accent transition-colors">
                      @{entry.handle}
                    </p>
                    {entry.status === 'sealed' && (
                      <p className="font-mono text-xs text-sealed mt-2">SEALED</p>
                    )}
                  </Link>
                )
              })}
            </div>
          )}

          {/* Full table */}
          <div className="fade-in fade-in-3">
            {/* Table header */}
            <div className="grid grid-cols-8 gap-2 px-5 py-3 border-b border-border">
              <p className="font-mono text-xs text-muted col-span-1">#</p>
              <p className="font-mono text-xs text-muted col-span-2">Handle</p>
              <p className="font-mono text-xs text-muted text-right">Composite</p>
              <p className="font-mono text-xs text-muted text-right hidden sm:block">Orig.</p>
              <p className="font-mono text-xs text-muted text-right hidden sm:block">Focus</p>
              <p className="font-mono text-xs text-muted text-right hidden sm:block">Cons.</p>
              <p className="font-mono text-xs text-muted text-right hidden sm:block">Depth</p>
            </div>

            {/* Rows */}
            <div className="space-y-px">
              {entries.map((entry, index) => (
                <Link
                  key={entry.handle}
                  href={`/${entry.handle}`}
                  className="grid grid-cols-8 gap-2 px-5 py-4 bg-surface border-b border-border hover:bg-border/30 transition-colors group items-center"
                >
                  <p className="font-mono text-xs text-muted col-span-1">
                    {index + 1}
                  </p>
                  <p className="font-sans font-semibold text-sm col-span-2 group-hover:text-accent transition-colors truncate">
                    @{entry.handle}
                  </p>
                  <p className="font-mono text-sm text-accent text-right">
                    {formatScore(entry.composite)}
                  </p>
                  <p className="font-mono text-xs text-muted text-right hidden sm:block">
                    {formatScore(entry.originality)}
                  </p>
                  <p className="font-mono text-xs text-muted text-right hidden sm:block">
                    {formatScore(entry.focus)}
                  </p>
                  <p className="font-mono text-xs text-muted text-right hidden sm:block">
                    {formatScore(entry.consistency)}
                  </p>
                  <p className="font-mono text-xs text-muted text-right hidden sm:block">
                    {formatScore(entry.depth)}
                  </p>
                </Link>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Footer note */}
      <div className="fade-in fade-in-4 mt-16 border-t border-border pt-8">
        <p className="font-mono text-xs text-muted leading-relaxed max-w-xl">
          Scores are computed over 30-day epochs using a deterministic engine and frozen
          classification prompt (v5). Sealed epochs are permanently anchored on Avalanche C-Chain.
        </p>
      </div>

    </div>
  )
}

function EmptyState() {
  return (
    <div className="border border-border p-16 text-center">
      <p className="font-mono text-xs text-muted mb-4">NO RECORDS YET</p>
      <p className="font-sans text-sm text-muted mb-8">
        Be the first to claim your Tessera.
      </p>
      <a
        href="https://arena.social"
        target="_blank"
        rel="noopener noreferrer"
        className="font-mono text-xs text-bg bg-accent px-6 py-3 hover:bg-primary transition-colors"
      >
        @bannerusmaximus claim →
      </a>
    </div>
  )
}
