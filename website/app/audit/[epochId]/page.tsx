import { getAudit, formatDate, formatScore } from '@/lib/api'
import Link from 'next/link'

export const runtime = 'edge'

interface PageProps {
  params: { epochId: string }
}

export default async function AuditPage({ params }: PageProps) {
  const audit = await getAudit(params.epochId)

  if (!audit) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-32 text-center">
        <p className="font-mono text-xs text-muted mb-4">NOT FOUND</p>
        <p className="font-sans text-sm text-muted">Epoch record not found.</p>
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-16">

      {/* Header */}
      <div className="fade-in fade-in-1 mb-12">
        <Link
          href={`/${audit.epoch.handle}`}
          className="font-mono text-xs text-muted hover:text-accent transition-colors mb-6 block"
        >
          ← @{audit.epoch.handle}
        </Link>
        <p className="font-mono text-xs text-muted tracking-widest uppercase mb-3">
          Audit trail
        </p>
        <h1 className="font-sans font-extrabold text-4xl tracking-tight mb-2">
          @{audit.epoch.handle}
        </h1>
        <p className="font-mono text-xs text-muted">
          {formatDate(audit.epoch.epoch_start)} → {formatDate(audit.epoch.epoch_end)}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-px bg-border mb-px">

        {/* Scores */}
        <div className="fade-in fade-in-2 bg-bg p-8">
          <p className="font-mono text-xs text-muted tracking-widest uppercase mb-6">Scores</p>
          <div className="space-y-3">
            {[
              { label: 'Composite',   value: audit.scores.composite,   accent: true },
              { label: 'Originality', value: audit.scores.originality, accent: false },
              { label: 'Focus',       value: audit.scores.focus,       accent: false },
              { label: 'Consistency', value: audit.scores.consistency, accent: false },
              { label: 'Depth',       value: audit.scores.depth,       accent: false },
            ].map(({ label, value, accent }) => (
              <div key={label} className="flex justify-between items-center">
                <span className={`font-sans text-sm ${accent ? 'font-bold' : ''}`}>{label}</span>
                <span className={`font-mono text-sm ${accent ? 'text-accent' : 'text-muted'}`}>
                  {formatScore(value)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Methodology */}
        <div className="fade-in fade-in-2 bg-bg p-8">
          <p className="font-mono text-xs text-muted tracking-widest uppercase mb-6">Methodology</p>
          <div className="space-y-3">
            {[
              { label: 'Version',      value: audit.methodology.version },
              { label: 'Prompt',       value: audit.methodology.prompt_hash },
              { label: 'Model',        value: audit.methodology.model },
              { label: 'Weights',      value: audit.methodology.weights },
              { label: 'Consistency',  value: audit.scores.consistency_mode },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between items-start gap-4">
                <span className="font-sans text-xs text-muted shrink-0">{label}</span>
                <span className="font-mono text-xs text-primary text-right break-all">{value ?? '—'}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Post breakdown */}
        <div className="fade-in fade-in-3 bg-bg p-8">
          <p className="font-mono text-xs text-muted tracking-widest uppercase mb-6">Post breakdown</p>
          <div className="space-y-3">
            {[
              { label: 'Total posts',     value: audit.post_breakdown.total },
              { label: 'Classified',      value: audit.post_breakdown.classified },
              { label: 'Greeting/noise',  value: audit.post_breakdown.greeting },
              { label: 'Null/empty',      value: audit.post_breakdown.null },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between">
                <span className="font-sans text-xs text-muted">{label}</span>
                <span className="font-mono text-sm text-primary">{value ?? '—'}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Onchain anchor */}
        <div className="fade-in fade-in-3 bg-bg p-8">
          <p className="font-mono text-xs text-muted tracking-widest uppercase mb-6">
            Onchain anchor
          </p>
          {audit.anchor ? (
            <div className="space-y-3">
              <div className="flex justify-between items-start gap-4">
                <span className="font-sans text-xs text-muted shrink-0">Status</span>
                <span className="font-mono text-xs text-sealed">SEALED ✓</span>
              </div>
              <div className="flex justify-between items-start gap-4">
                <span className="font-sans text-xs text-muted shrink-0">Block</span>
                <span className="font-mono text-xs text-primary">{audit.anchor.block_number}</span>
              </div>
              <div className="flex justify-between items-start gap-4">
                <span className="font-sans text-xs text-muted shrink-0">Anchored</span>
                <span className="font-mono text-xs text-primary">{formatDate(audit.anchor.anchored_at)}</span>
              </div>
              <div className="flex justify-between items-start gap-4">
                <span className="font-sans text-xs text-muted shrink-0">TX</span>
                <a
                  href={audit.anchor.snowtrace_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-xs text-accent hover:text-primary transition-colors break-all text-right"
                >
                  {audit.anchor.tx_hash.slice(0, 22)}…
                </a>
              </div>
            </div>
          ) : (
            <div>
              <p className="font-mono text-xs text-muted mb-2">NOT YET SEALED</p>
              <p className="font-sans text-xs text-muted">
                This epoch has not been anchored onchain yet. Sealing occurs automatically at the epoch boundary.
              </p>
            </div>
          )}
        </div>

      </div>

      {/* Snapshot hash */}
      <div className="fade-in fade-in-4 bg-surface border-b border-border p-6 mb-px">
        <p className="font-mono text-xs text-muted tracking-widest uppercase mb-3">Snapshot hash</p>
        <p className="font-mono text-xs text-primary break-all">{audit.snapshot_hash ?? '—'}</p>
        <p className="font-mono text-xs text-muted mt-2">
          SHA-256 of canonical JSON snapshot. Reproduce by hashing the snapshot_json field above with the same methodology.
        </p>
      </div>

      {/* Disclaimer */}
      <div className="fade-in fade-in-5 pt-8">
        <p className="font-mono text-xs text-muted leading-relaxed border-l-2 border-border pl-4">
          {audit.disclaimer}
        </p>
      </div>

    </div>
  )
}
