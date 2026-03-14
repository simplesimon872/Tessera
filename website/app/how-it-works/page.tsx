import Link from 'next/link'

export const runtime = 'edge'

export const metadata = {
  title: 'How It Works — Tessera',
  description: 'How Tessera scores, seals, and verifies behavioral records onchain.',
}

const steps = [
  {
    index: '01',
    title: 'You post on Arena',
    subtitle: 'The raw material',
    body: `Every post, reply, and quote-post you make on Arena is the input. Tessera doesn't care about likes, reposts, or follower counts — only what you actually write, and how often.

Over a rolling 30-day epoch, every post is collected via the Arena API and timestamped. The collection is hashed (SHA-256) immediately — creating a fingerprint of exactly which posts were included. This hash is stored with every score, so anyone can verify the inputs haven't been tampered with.`,
    detail: 'EPOCH WINDOW: 30 days, rolling. Minimum 5 posts required to score.',
    code: null,
  },
  {
    index: '02',
    title: 'Posts are classified',
    subtitle: 'The LLM layer',
    body: `Each post is classified into one of six topic buckets using Claude Haiku (temperature=0). The prompt is frozen at version 5 and will never change mid-epoch — the same input always produces the same output.

Temperature=0 is non-negotiable. It eliminates randomness from the classification. The prompt hash (SHA-256 of the exact prompt text) is stored with every score so anyone can verify which prompt version was used.

Short posts, greetings (gm/gn), and empty reposts are routed before the LLM — the classifier only sees posts worth classifying.`,
    detail: 'PROMPT: v5, frozen. HASH: 1deff518231c… MODEL: claude-haiku-4-5',
    code: `Categories:
Market & Price        — price analysis, TA, portfolio commentary
Technology & Infra    — chains, L2s, protocol upgrades, node software
DeFi & Protocols      — AMMs, lending, staking, yield, stablecoins
AI & Agents           — AI models, autonomous agents, AI lab news
Governance & DAOs     — proposals, treasury decisions, regulatory
Other                 — memes, general crypto culture, personal
Null                  — greetings only, too short, no content`,
  },
  {
    index: '03',
    title: 'Four pillars are scored',
    subtitle: 'The scoring engine',
    body: `The classified posts feed into four independent scoring algorithms. All four are deterministic — given the same classified posts, the engine always produces the same scores.`,
    detail: 'COMPOSITE: equal-weight average of all four (25% each). Range: 0–100.',
    code: `Originality   = original posts / active posts × 100
               — original: not a reply, not a quote-repost

Focus         = 1 − (Shannon entropy / log₂(6)) × 100
               — low entropy = high focus = high score
               — capped if >50% of posts are "Other"

Consistency   = posting regularity across thirds of the epoch
               — mode A (≥20 posts): topic distribution stability
               — mode B (<20 posts): frequency variance (CV)

Depth         = (replies + quote-posts) / active posts × 100
               — measures engagement, not broadcasting`,
  },
  {
    index: '04',
    title: 'The snapshot is hashed',
    subtitle: 'The integrity layer',
    body: `Before anything goes onchain, the full score snapshot is serialised to canonical JSON (sorted keys, no whitespace, UTF-8) and hashed with SHA-256.

This snapshot hash is what gets anchored — not the scores themselves. The scores are derivable from the hash. If anyone wants to verify a score independently, they reconstruct the snapshot from the audit trail and hash it themselves. If the hashes match, the score is genuine.`,
    detail: 'CANONICAL FORMAT: JSON, sort_keys=True, separators=(",", ":"), ensure_ascii=False.',
    code: `snapshot = {
  "handle":        "simplesimon872",
  "epoch_start":   "2026-02-12T08:32:00+00:00",
  "epoch_end":     "2026-03-14T08:32:00+00:00",
  "scores": { "composite": 68.4, "originality": 72.0, ... },
  "provenance": { "prompt_hash": "1deff518...", "model": "claude-haiku-4-5", ... },
  ...
}

snapshot_hash = SHA256(canonical_json(snapshot))`,
  },
  {
    index: '05',
    title: 'The hash is sealed onchain',
    subtitle: 'The attestation layer',
    body: `Every Sunday at midnight UTC, the sealing cron runs. For each claimed account with a computed epoch, the snapshot hash is written to TesseraAnchor.sol on Avalanche C-Chain mainnet.

The contract stores only the hash — no personal data, no scores. Anyone can query the contract with a hash and confirm it was recorded at a specific block. No admin key. No upgrades. Immutable.

Once sealed, the epoch status is permanently locked. Nothing can change it.`,
    detail: 'CHAIN: Avalanche C-Chain (chainId 43114). CONTRACT: TesseraAnchor.sol.',
    code: `// TesseraAnchor.sol (simplified)
mapping(bytes32 => uint256) public anchors;

function anchor(bytes32 snapshotHash) external {
    require(anchors[snapshotHash] == 0, "already anchored");
    anchors[snapshotHash] = block.number;
    emit Anchored(snapshotHash, block.number, block.timestamp);
}`,
  },
  {
    index: '06',
    title: 'Anyone can verify',
    subtitle: 'The audit trail',
    body: `Every sealed epoch has a public audit page at tessera-8x7.pages.dev/audit/[epoch-id].

The audit page shows every input used to produce the score: the prompt hash, the model, the collection hash, the methodology version, and the full snapshot JSON. To verify independently:

1. Copy the snapshot JSON from the audit page
2. Serialise it to canonical JSON (sort_keys, no whitespace)
3. SHA-256 hash it
4. Compare to the tx_input on Snowtrace

If the hashes match, the score is genuine. No trust required.`,
    detail: 'AUDIT URL: tessera-8x7.pages.dev/audit/[epoch-id]',
    code: `# Reproduce the hash in Python
import json, hashlib

with open("snapshot.json") as f:
    snapshot = json.load(f)

canonical = json.dumps(snapshot, sort_keys=True,
    separators=(",", ":"), ensure_ascii=False)
hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

# Compare to Snowtrace tx input data`,
  },
]

export default function HowItWorksPage() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-16">

      {/* Header */}
      <div className="fade-in fade-in-1 mb-20 border-b border-border pb-16">
        <p className="font-mono text-xs text-accent tracking-widest uppercase mb-4">
          Technical Overview
        </p>
        <h1 className="font-sans font-extrabold text-5xl tracking-tight mb-6">
          How It Works
        </h1>
        <p className="font-sans text-muted text-lg max-w-2xl">
          Tessera turns social posting behavior into a cryptographically verifiable record.
          Six steps from raw post to onchain attestation.
        </p>
      </div>

      {/* Steps */}
      <div className="space-y-0">
        {steps.map((step, i) => (
          <div key={step.index} className="fade-in fade-in-2 group">

            {/* Step container */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-0 border-b border-border py-16">

              {/* Left — step number + title */}
              <div className="lg:col-span-4 mb-8 lg:mb-0 lg:pr-12">
                <p className="font-mono text-xs text-muted tracking-widest mb-2">
                  STEP {step.index}
                </p>
                <h2 className="font-sans font-bold text-2xl mb-1">
                  {step.title}
                </h2>
                <p className="font-mono text-xs text-accent tracking-wide">
                  {step.subtitle}
                </p>
              </div>

              {/* Right — content */}
              <div className="lg:col-span-8">
                {/* Body text */}
                <div className="font-sans text-sm text-muted leading-relaxed space-y-4 mb-6">
                  {step.body.split('\n\n').map((para, j) => (
                    <p key={j}>{para}</p>
                  ))}
                </div>

                {/* Detail line */}
                <p className="font-mono text-xs text-muted border-l-2 border-accent pl-3 mb-6">
                  {step.detail}
                </p>

                {/* Code block */}
                {step.code && (
                  <pre className="font-mono text-xs text-primary bg-surface border border-border p-4 overflow-x-auto leading-relaxed">
                    {step.code}
                  </pre>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Bottom CTA */}
      <div className="fade-in fade-in-3 mt-20 grid grid-cols-1 sm:grid-cols-3 gap-px bg-border">
        <Link
          href="/leaderboard"
          className="bg-bg p-8 hover:bg-surface transition-colors group"
        >
          <p className="font-mono text-xs text-muted mb-3 tracking-widest">SEE THE DATA</p>
          <p className="font-sans font-bold text-lg mb-2 group-hover:text-accent transition-colors">Leaderboard →</p>
          <p className="font-sans text-xs text-muted">Live scores across all claimed and inspected accounts.</p>
        </Link>
        <a
          href="https://arena.social/?ref=SimpleSimon872"
          target="_blank"
          rel="noopener noreferrer"
          className="bg-bg p-8 hover:bg-surface transition-colors group"
        >
          <p className="font-mono text-xs text-muted mb-3 tracking-widest">GET STARTED</p>
          <p className="font-sans font-bold text-lg mb-2 group-hover:text-accent transition-colors">Claim your Tessera →</p>
          <p className="font-sans text-xs text-muted">Tag @bannerusmaximus claim on Arena to activate your record.</p>
        </a>
        <Link
          href="/"
          className="bg-bg p-8 hover:bg-surface transition-colors group"
        >
          <p className="font-mono text-xs text-muted mb-3 tracking-widest">LOOK UP ANYONE</p>
          <p className="font-sans font-bold text-lg mb-2 group-hover:text-accent transition-colors">Inspect a handle →</p>
          <p className="font-sans text-xs text-muted">Tag @bannerusmaximus inspect @handle to score any Arena account.</p>
        </Link>
      </div>

    </div>
  )
}
