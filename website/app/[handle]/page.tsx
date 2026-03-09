import { getProfile, getAudit, formatDate, formatScore } from '@/lib/api'
import { ScoreGrid } from '@/components/ScoreGrid'
import Link from 'next/link'

interface PageProps {
  params: { handle: string }
}

export async function generateMetadata({ params }: PageProps) {
  return {
    title: `@${params.handle} — Tessera`,
    description: `Behavioral epoch record for @${params.handle} on Tessera.`,
  }
}

// API returns scores as an array — extract first element
function extractScores(epoch: any) {
  if (!epoch) return null
  const s = Array.isArray(epoch.scores) ? epoch.scores[0] : epoch.scores
  if (!s) return null
  return {
    composite:   s.composite,
    originality: s.originality,
    focus:       s.focus,
    consistency: s.consistency,
    depth:       s.depth,
  }
}

function extractAnchor(epoch: any) {
  if (!epoch) return null
  const anchors = Array.isArray(epoch.anchors) ? epoch.anchors : []
  return anchors[0] ?? null
}

export default async function ProfilePage({ params }: PageProps) {
  const handle = params.handle.toLowerCase()
  const profile = await getProfile(handle)

  if (!profile) {
    return <NotFoundState handle={handle} />
  }

  const latestEpoch = profile.epochs?.[0] ?? null
  const latestScores = extractScores(latestEpoch)
  const latestAnchor = extractAnchor(latestEpoch)
  const isSealed = latestEpoch?.status === 'sealed'

  return (
    <div className="max-w-5xl mx-auto px-6 py-16">

      {/* Header */}
      <div className="fade-in fade-in-1 mb-12">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <p className="font-mono text-xs text-muted tracking-widest uppercase mb-2">
              Behavioral record
            </p>
            <h1 className="font-sans font-extrabold text-4xl sm:text-5xl tracking-tight">
              @{handle}
            </h1>
          </div>
          <div className="flex flex-col items-end gap-2">
            {profile.claimed ? (
              <span className="font-mono text-xs text-sealed border border-sealed/30 bg-sealed/5 px-3 py-1">
                ◆ CLAIMED
              </span>
            ) : (
              <span className="font-mono text-xs text-muted border border-border px-3 py-1">
                UNCLAIMED
              </span>
            )}
            {profile.claimed_at && (
              <p className="font-mono text-xs text-muted">
                since {formatDate(profile.claimed_at)}
              </p>
            )}
          </div>
        </div>
      </div>

      {latestEpoch && latestScores ? (
        <>
          {/* Current epoch scores */}
          <div className="fade-in fade-in-2 grid grid-cols-1 sm:grid-cols-2 gap-px bg-border mb-px">
            <div className="bg-bg p-8">
              <div className="flex items-center justify-between mb-6">
                <p className="font-mono text-xs text-muted tracking-widest uppercase">
                  Current epoch
                </p>
                {isSealed ? (
                  <span className="font-mono text-xs text-sealed">SEALED ✓</span>
                ) : (
                  <span className="font-mono text-xs text-accent">LIVE</span>
                )}
              </div>
              <p className="font-mono text-xs text-muted mb-1">
                {formatDate(latestEpoch.epoch_start)} → {formatDate(latestEpoch.epoch_end)}
              </p>
              {isSealed && latestAnchor && (
                <a
                  href={latestAnchor.snowtrace_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-xs text-muted hover:text-accent transition-colors mt-1 block"
                >
                  TX: {latestAnchor.tx_hash.slice(0, 18)}…
                </a>
              )}
            </div>
            <div className="bg-bg p-8">
              <ScoreGrid scores={latestScores} />
            </div>
          </div>

          {/* Audit link */}
          <div className="fade-in fade-in-3 mb-12">
            <Link
              href={`/audit/${latestEpoch.id}`}
              className="w-full flex items-center justify-between border-b border-border py-4 text-muted hover:text-primary font-mono text-xs tracking-wide group transition-colors"
            >
              <span>VIEW FULL AUDIT TRAIL</span>
              <span className="group-hover:translate-x-1 transition-transform">→</span>
            </Link>
          </div>
        </>
      ) : (
        <div className="fade-in fade-in-2 border border-border p-12 text-center mb-12">
          <p className="font-mono text-xs text-muted mb-4">NO EPOCH DATA</p>
          <p className="font-sans text-sm text-muted">
            This account hasn&apos;t been scored yet.
          </p>
          {!profile.claimed && (
            <p className="font-sans text-sm text-muted mt-2">
              Tag{' '}
              <span className="font-mono text-accent">@bannerusmaximus claim</span>
              {' '}on Arena to activate.
            </p>
          )}
        </div>
      )}

      {/* Epoch history */}
      {profile.epochs && profile.epochs.length > 1 && (
        <div className="fade-in fade-in-4">
          <p className="font-mono text-xs text-muted tracking-widest uppercase mb-6">
            Epoch history
          </p>
          <div className="space-y-px">
            {profile.epochs.slice(1).map((epoch) => {
              const scores = extractScores(epoch)
              return (
                <div
                  key={epoch.id}
                  className="bg-surface border-b border-border p-5 flex flex-col sm:flex-row sm:items-center gap-4 hover:bg-border/20 transition-colors"
                >
                  <div className="flex-1">
                    <p className="font-mono text-xs text-muted">
                      {formatDate(epoch.epoch_start)} → {formatDate(epoch.epoch_end)}
                    </p>
                  </div>
                  <div className="flex items-center gap-8">
                    <div className="text-right">
                      <p className="font-mono text-xs text-muted mb-0.5">Composite</p>
                      <p className="font-mono text-sm text-accent">{formatScore(scores?.composite)}</p>
                    </div>
                    {epoch.status === 'sealed' ? (
                      <span className="font-mono text-xs text-sealed w-16 text-right">SEALED</span>
                    ) : (
                      <span className="font-mono text-xs text-muted w-16 text-right">UNSEALED</span>
                    )}
                    <Link
                      href={`/audit/${epoch.id}`}
                      className="font-mono text-xs text-muted hover:text-accent transition-colors"
                    >
                      AUDIT →
                    </Link>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Not claimed CTA */}
      {!profile.claimed && (
        <div className="fade-in fade-in-5 mt-16 border border-border p-8">
          <p className="font-mono text-xs text-accent mb-3">THIS RECORD IS UNSEALED</p>
          <p className="font-sans text-sm text-muted mb-6">
            @{handle} hasn&apos;t claimed their Tessera. Their record is visible — but
            it won&apos;t be sealed onchain until they activate.
          </p>
          <a
            href="https://arena.social"
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-xs text-bg bg-accent px-4 py-2 hover:bg-primary transition-colors"
          >
            @bannerusmaximus claim →
          </a>
        </div>
      )}

    </div>
  )
}

function NotFoundState({ handle }: { handle: string }) {
  return (
    <div className="max-w-5xl mx-auto px-6 py-32 text-center">
      <p className="font-mono text-xs text-muted tracking-widest uppercase mb-4">NOT FOUND</p>
      <h1 className="font-sans font-extrabold text-4xl mb-4">@{handle}</h1>
      <p className="font-sans text-muted text-sm mb-8">
        No Tessera record exists for this handle yet.
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
