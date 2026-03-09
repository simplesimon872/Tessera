import Link from 'next/link'
import HandleSearchInput from '@/components/HandleSearchInput'

export default function HomePage() {
  return (
    <div className="max-w-5xl mx-auto px-6">

      {/* Hero */}
      <section className="pt-24 pb-20 border-b border-border">
        <div className="fade-in fade-in-1">
          <p className="font-mono text-xs text-accent tracking-widest uppercase mb-6">
            Onchain Behavioral Attestation Protocol
          </p>
        </div>
        <div className="fade-in fade-in-2">
          <h1 className="font-sans font-extrabold text-5xl sm:text-7xl leading-none tracking-tight mb-6">
            Your reputation,<br />
            <span className="text-accent">sealed onchain.</span>
          </h1>
        </div>
        <div className="fade-in fade-in-3">
          <p className="font-sans text-muted text-lg max-w-xl leading-relaxed mb-10">
            Tessera scores your posting behavior over 30-day epochs — originality, focus,
            consistency, and depth — then seals the result permanently on Avalanche.
            No edits. No deletions. A tamper-proof record of who you are on Arena.
          </p>
        </div>
        <div className="fade-in fade-in-4 flex flex-col sm:flex-row gap-4">
          <a
            href="https://arena.social"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 bg-accent text-bg font-mono font-medium text-sm px-6 py-3 hover:bg-primary transition-colors tracking-wide"
          >
            @bannerusmaximus claim →
          </a>
          <Link
            href="/leaderboard"
            className="inline-flex items-center gap-2 border border-border text-primary font-mono text-sm px-6 py-3 hover:border-muted transition-colors tracking-wide"
          >
            View leaderboard
          </Link>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 border-b border-border">
        <div className="fade-in fade-in-1">
          <p className="font-mono text-xs text-muted tracking-widest uppercase mb-12">
            How it works
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-px bg-border">
          {[
            {
              step: '01',
              title: 'Claim',
              body: 'Tag @bannerusmaximus claim on Arena. Your behavioral record starts immediately.',
              mono: '@bannerusmaximus claim',
            },
            {
              step: '02',
              title: 'Score',
              body: 'Every 30 days, Tessera fetches your posts, classifies them with a frozen LLM prompt, and runs a deterministic scoring engine.',
              mono: '@bannerusmaximus reveal',
            },
            {
              step: '03',
              title: 'Seal',
              body: 'At epoch boundary, your snapshot hash is anchored to Avalanche C-Chain. Immutable. Verifiable. Forever.',
              mono: 'TesseraAnchor.sol',
            },
          ].map(({ step, title, body, mono }) => (
            <div key={step} className="bg-bg p-8 relative overflow-hidden scan-hover">
              <p className="font-mono text-xs text-border mb-6 select-none">{step}</p>
              <h3 className="font-sans font-bold text-xl mb-3">{title}</h3>
              <p className="font-sans text-muted text-sm leading-relaxed mb-6">{body}</p>
              <p className="font-mono text-xs text-accent">{mono}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Scores */}
      <section className="py-20 border-b border-border">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-16 items-start">
          <div>
            <p className="font-mono text-xs text-muted tracking-widest uppercase mb-6">
              What gets measured
            </p>
            <h2 className="font-sans font-extrabold text-4xl leading-tight mb-6">
              Four dimensions.<br />One composite.
            </h2>
            <p className="font-sans text-muted text-sm leading-relaxed">
              All scores are deterministic — the same posts always produce the same result.
              The classification prompt is frozen at v5 and recorded in every onchain attestation.
            </p>
          </div>
          <div className="space-y-5">
            {[
              { label: 'Originality', value: 80, desc: 'Topic diversity via Shannon entropy' },
              { label: 'Focus',       value: 74, desc: 'Coherence across the epoch window' },
              { label: 'Consistency', value: 68, desc: 'Posting regularity over 30 days' },
              { label: 'Depth',       value: 61, desc: 'Engagement quality and signal' },
            ].map(({ label, value, desc }, i) => (
              <div key={label}>
                <div className="flex justify-between items-baseline mb-1.5">
                  <span className="font-sans text-sm font-medium">{label}</span>
                  <span className="font-mono text-sm text-accent">{value}.0</span>
                </div>
                <div className="h-px bg-border w-full relative overflow-hidden">
                  <div
                    className="score-bar h-px bg-accent absolute left-0 top-0"
                    style={{
                      '--target-width': `${value}%`,
                      '--delay': `${i * 120}ms`,
                    } as React.CSSProperties}
                  />
                </div>
                <p className="font-mono text-xs text-muted mt-1.5">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Search */}
      <section className="py-20 border-b border-border">
        <div className="text-center">
          <p className="font-mono text-xs text-muted tracking-widest uppercase mb-4">
            Look up any handle
          </p>
          <h2 className="font-sans font-extrabold text-3xl mb-8">
            Check a record
          </h2>
          <HandleSearchInput />
        </div>
      </section>

      {/* Key properties */}
      <section className="pb-20 pt-20">
        <p className="font-mono text-xs text-muted tracking-widest uppercase mb-12">
          Key properties
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
          {[
            {
              title: 'Deterministic',
              body: 'Same posts. Same prompt. Same score. Every time. No randomness, no model drift.',
            },
            {
              title: 'Verifiable',
              body: 'Every sealed epoch is anchored onchain. Anyone can reproduce the snapshot hash independently.',
            },
            {
              title: 'Manipulation-resistant',
              body: 'Epoch boundaries prevent burst gaming. Consistency rewards sustained behavior, not activity spikes.',
            },
          ].map(({ title, body }) => (
            <div key={title} className="border-t border-border pt-6">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-accent text-xs">◆</span>
                <h3 className="font-sans font-bold text-sm uppercase tracking-wide">{title}</h3>
              </div>
              <p className="font-sans text-muted text-sm leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
      </section>

    </div>
  )
}
