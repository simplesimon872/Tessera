# Tessera: I Built a Tamper-Proof Behavioral Reputation System for Crypto Social in 13 Days

*By Simon — builder at @simplesimon872 on Arena*

---

Crypto social reputation is mostly fake.

Follower counts are bought. Engagement is farmed. KOLs with 50,000 followers call contract addresses with zero accountability for what happens next. Protocols hand out whitelist spots based on Discord activity that costs $20 to manufacture. Launchpads vet influencers based on screenshots and vibes.

There's no verified track record. There's no record at all.

I spent 13 days building one.

---

## What Tessera Does

Tessera is a behavioral reputation protocol for social accounts. It scores how you post — not how popular you are — across four dimensions, and seals that score permanently on the Avalanche blockchain.

The four dimensions are:

**Originality** — what fraction of your posts are original content versus replies and quotes. If you spend 90% of your time resharing other people's content, that's in the record.

**Focus** — how concentrated your posting is across topic areas. A crypto analyst who posts exclusively about DeFi infrastructure scores higher than someone who posts about DeFi, memecoins, lifestyle, and sports equally. Measured using Shannon entropy across six topic buckets.

**Consistency** — whether your posting is regular over time or comes in bursts. Bots and farmers post in spikes. Genuine accounts post steadily. Frequency variance across weekly windows within the 30-day epoch captures this directly.

**Depth** — engagement quality. Reply ratio, quote ratio, participation rate. Are you in the conversation or just broadcasting?

Each dimension scores 0–100. The composite is an equal-weighted average. The methodology is version-controlled (currently v1.0), and every score includes the exact prompt hash and methodology version used to produce it.

Every score is deterministic. Given the same posts and the same prompt, Tessera will always produce the same result. This is not a feature you get for free from LLMs — it took deliberate engineering.

---

## Why I Built It This Way

The technical design comes from a specific constraint: **if the score can be gamed or altered retroactively, it's worthless.**

Most reputation systems fail this test in one of three ways:

1. They're black boxes — the score changes over time for reasons the user can't verify
2. They measure the wrong thing — follower counts, on-chain activity, or social graphs are all gameable
3. They require the user to do something (connect a wallet, collect stamps, get vouches) that introduces friction and selection bias

Tessera is designed to fail none of these tests.

**It's not a black box.** The scoring algorithm is open source. The LLM prompt is frozen and published with a SHA-256 hash. The methodology version is stored with every score. Anyone with the raw post data can independently reproduce the result and verify it matches what's onchain. The audit page on every sealed epoch includes step-by-step instructions for doing exactly this.

**It measures behavioral patterns, not social proof.** Posts are pulled directly from the Arena API — the user has no ability to selectively include or exclude content. Topic classification uses a frozen prompt so the categories can't drift between epochs. Shannon entropy makes focus mathematically precise rather than subjective.

**It requires zero friction from the user.** No wallet. No gas. No onboarding flow. You tag `@bannerusmaximus claim` in a normal Arena post and your Tessera is activated. That's it. Everything else — scoring, sealing, notification — happens automatically.

---

## The Technical Architecture

Here's how it actually works under the hood, for anyone who wants to verify or build on it:

```
Arena post history
      ↓
Post ingestion (30-day epoch window, paginated Arena API)
      ↓
Pre-classification (classify / greeting / null routing)
      ↓
LLM topic classification (Claude Haiku, temp=0, prompt v5)
      ↓
Deterministic scoring engine (4 pillars → composite)
      ↓
Canonical JSON snapshot (sort_keys=True, no whitespace, 2dp floats, ISO timestamps)
      ↓
SHA-256 hash
      ↓
TesseraAnchor.sol on Avalanche C-Chain mainnet
      ↓
Public audit trail at tessera-8x7.pages.dev/@handle
```

**The canonicalisation step is where most implementations would fail.** `JSON.stringify(snapshot)` is not deterministic without explicit controls — key ordering varies, float precision varies, whitespace differs across environments. The canonical hash function uses `sort_keys=True`, fixed separators (`','` and `':'`), UTF-8 encoding, all scores rounded to exactly 2 decimal places, and ISO 8601 timestamps with no milliseconds. These constraints are documented in the audit trail so anyone reproducing the hash uses the same rules.

**The smart contract is deliberately minimal:**

```solidity
contract TesseraAnchor {
    event Anchored(
        address indexed sender,
        bytes32 indexed snapshotHash,
        uint256 timestamp
    );

    function anchor(bytes32 snapshotHash) external {
        emit Anchored(msg.sender, snapshotHash, block.timestamp);
    }
}
```

No storage. No access control. No upgrades. Just a timestamped, immutable event log on the blockchain. The contract has no admin key because an admin key would mean the records could be altered. The contract emits events because events are cheaper than storage and sufficient for attestation — anyone can query the event log independently via Snowtrace.

The first live transaction on Avalanche C-Chain mainnet:
`0x5fbed879e76609a851d8b810ac27cedc92dbabc1186a54e9d3a442adee37a8a5`

---

## Why It Can't Be Gamed

**Burst posting doesn't work.** The consistency pillar measures frequency variance across the full 30-day epoch. Posting heavily in the week before a reveal actually hurts your consistency score because it creates exactly the kind of spike the formula penalizes.

**Cherry-picking posts doesn't work.** Tessera fetches posts directly from the Arena API using your public account ID. There is no mechanism for you to choose which posts get included. Everything in the epoch window is scored.

**Retroactive editing doesn't work.** Once an epoch seals, the snapshot hash is on the blockchain. If the off-chain data changes — if a score is edited, if a post count is altered, if even one float is rounded differently — the recomputed hash won't match the onchain hash. The discrepancy is immediately detectable by anyone.

**Changing the scoring rules doesn't work silently.** The prompt hash and methodology version are written into every sealed record. If the classification prompt changes, the hash changes. If the methodology version changes, that version bump is visible in every subsequent epoch. Historical scores remain comparable because the rules that produced them are on record.

**The protocol operator can't retroactively alter scores.** The smart contract has no admin function. There is no override. There is no appeals mechanism. A sealed record is sealed.

---

## The Audit Trail

Every sealed epoch has a public audit page at `tessera-8x7.pages.dev/audit/[epochId]`.

It shows:
- The epoch window (start and end date)
- The full post breakdown (classified / greeting / null)
- All four pillar scores and the composite
- The methodology version and prompt hash used
- The onchain anchor: TX hash, block number, Snowtrace link
- The snapshot hash — with step-by-step instructions to reproduce it

The "How to Verify" section on the audit page walks through the verification process in Python:

```python
import json, hashlib

# Paste snapshot_json from the API
snapshot = { ...full snapshot object... }

canonical = json.dumps(
    snapshot,
    sort_keys=True,
    separators=(',', ':'),
    ensure_ascii=False
)
result = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
print(result)
# Should match the snapshot hash on the audit page exactly
```

If the hash you compute matches the audit page, and that hash matches the `snapshotHash` argument in the Snowtrace transaction, the score has not been altered. Anyone can verify this. No trust required.

---

## What It's For

The immediate use case is individual — you want to know how you actually post, and you want a record that reflects that. The score is a mirror, not a reward.

But the more interesting use cases are commercial:

**Launchpad KOL vetting.** A KOL with 6 sealed Tessera epochs has a verifiable 6-month behavioral track record. Their consistency score tells you whether they post regularly or in bursts around launches. Their focus score tells you whether they're genuinely specialized or generalists who talk about whatever pays. Their originality score tells you how much of their content is original versus reshared. None of this can be faked retroactively.

**Airdrop gating.** Instead of farming Discord activity, protocols can gate eligibility by Tessera composite score. Accounts that score above a threshold across the relevant epoch have demonstrated genuine behavioral engagement. Accounts that were clearly created to farm the airdrop will have no epoch history.

**Whitelist qualification.** Same principle — a Tessera score is a tamper-proof credential that a wallet address corresponds to an account with a genuine behavioral record.

The next version of the scoring system will add a Signal Integrity pillar: tracking CA (contract address) calls in posts and measuring outcomes. An account that consistently calls contracts that subsequently perform well has a different behavioral fingerprint than one that calls projects that rug. This is the pillar that makes Tessera directly useful for launchpad risk assessment.

---

## 13 Days

The first Arena API call was February 26. The submission deadline was March 10. Between those two dates: ingestion layer, evaluation dataset, LLM classifier with determinism testing, scoring engine, onchain attestation, bot listener, FastAPI backend, Next.js 15 frontend, Render deployment, Cloudflare Pages deployment, and everything that went wrong along the way.

The bot went live with days to spare. The contract is on mainnet. The website is live. The first epoch seals this Sunday.

---

## Try It

Tag `@bannerusmaximus claim` on Arena to activate your Tessera.

Tag `@bannerusmaximus inspect @handle` on any Arena account — claimed or not. Their score is computed, their profile goes live, and they're tagged in the reply with a prompt to claim. No permission required.

Every score is public. Every sealed epoch is verifiable. The protocol runs itself.

**tessera-8x7.pages.dev**

---

*Tessera is open source. The methodology is published. The prompt hash is on every sealed epoch. If you find a bug in the scoring logic or a flaw in the verification process, tag @simplesimon872 on Arena.*

