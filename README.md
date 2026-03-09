# Tessera

![Python](https://img.shields.io/badge/Python-Backend-blue)
![Avalanche](https://img.shields.io/badge/Avalanche-C--Chain-red)
![LLM](https://img.shields.io/badge/Claude-Haiku-purple)
![License](https://img.shields.io/badge/License-MIT-green)

**Onchain behavioral attestation protocol for Arena social accounts.**

Tessera scores your posting behavior over a 30-day epoch — originality, focus, consistency, and depth — then seals the result permanently on the Avalanche blockchain. No edits. No deletions. A tamper-proof record of behavioral activity on Arena, sealed onchain.

> Tag `@bannerusmaximus claim` on Arena to activate your record.

---

## Problem

Crypto social platforms are filled with anonymous accounts and short-lived identities. Follower counts and engagement metrics are easily gamed, and there is no reliable way to verify whether an account has demonstrated consistent behavior over time.

## Solution

Tessera creates a verifiable behavioral record by analyzing posting patterns across fixed epochs and sealing the resulting scores onchain.

Instead of reputation based on popularity, Tessera measures behavioral signals — originality, focus, consistency, and depth — and produces an immutable attestation for each epoch.

---

## System Overview

```
        Arena Social Platform
                │
                │  @bannerusmaximus reveal
                ▼
        Tessera Bot Listener
       (Arena Agents API Polling)
                │
                ▼
         Post Ingestion Layer
      (Arena API → Epoch Window)
                │
                ▼
         LLM Classification
      (Claude Haiku — Prompt v5)
                │
                ▼
      Deterministic Scoring Engine
(Originality • Focus • Consistency • Depth)
                │
                ▼
       Snapshot Canonicalization
          (SHA-256 Hashing)
                │
                ▼
      Onchain Attestation Layer
    (Avalanche C-Chain Smart Contract)
                │
                ▼
         Verifiable Epoch Record
```

---

## Key Properties

**Deterministic scoring**
All scoring logic is deterministic. Given the same classified posts, Tessera will always produce the same score output.

**Verifiable outputs**
Every epoch snapshot is hashed and anchored onchain, creating a tamper-proof record that can be independently verified.

**Behavior over popularity**
Tessera measures behavioral signals rather than social metrics such as followers or engagement counts. The protocol evaluates how an account behaves over time rather than how popular it is.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Bot interface | `@bannerusmaximus` — Arena social account |
| Agent backend | `tessera_agent` — Arena Agents API |
| LLM classification | Claude Haiku (temperature=0, prompt v5) |
| Scoring engine | Python, deterministic |
| Blockchain | Avalanche C-Chain (chainId 43114) |
| Smart contract | Solidity — `TesseraAnchor.sol` |
| Database | PostgreSQL via Supabase |
| API | FastAPI |
| Hosting | Railway (backend) |
| Frontend | Planned (profile explorer for sealed epochs) |

---

## Architecture Decisions

Tessera is designed around deterministic scoring with verifiable outputs.

LLM usage is restricted to classification only, with temperature set to 0 and a frozen prompt version. This ensures that post categorisation is reproducible and prevents score drift between epochs.

All scoring logic is implemented in a deterministic Python engine. Given the same classified inputs, the system will always produce the same scores.

To preserve transparency, the final scoring snapshot is hashed and anchored onchain via a Solidity contract. This creates a tamper-proof attestation of the behavioral fingerprint for each epoch.

The system intentionally separates three layers:

- **ingestion** — collecting public social data from Arena
- **evaluation** — LLM classification and deterministic scoring
- **attestation** — immutable onchain record

This separation ensures the scoring methodology can be audited independently of the data collection layer.

---

## Why Epochs

Tessera evaluates behavior in 30-day epochs rather than continuous scoring.

This prevents short-term manipulation and ensures that scores represent sustained behavioral patterns rather than temporary activity spikes.

Once an epoch is sealed onchain, it becomes a permanent historical record that can be independently verified.

---

## On-Chain vs Off-Chain Logic

**Off-chain components:**
- Post ingestion from Arena API
- LLM post classification
- Deterministic scoring engine
- Epoch state storage (Supabase)

**On-chain components:**
- Final epoch attestation via `TesseraAnchor.sol`
- Storage of snapshot hash and score metadata
- Immutable verification layer for historical scores

The onchain layer does not perform computation. It acts as a cryptographic anchor guaranteeing that a published score cannot be altered after sealing.

---

## Security and Manipulation Resistance

Tessera is designed from the ground up to be resistant to gaming, retroactive editing, and score manipulation. Each layer of the system contributes to this.

### Frozen Prompt and Methodology Versioning

The LLM classification prompt is frozen at version 5 with a published SHA-256 hash (`1deff518231c...`). The scoring methodology is versioned at v1.0. Both identifiers are written into every onchain attestation.

This means:
- The classification rules cannot be quietly changed between epochs
- Any future methodology change produces a different version identifier, making it auditable
- Historical scores remain comparable across time because the rules that produced them are immutable and on record

### Deterministic Scoring Engine

The scoring engine is fully deterministic. Given identical classified inputs, it will always produce identical outputs — no randomness, no model temperature, no floating point variance across runs.

This means anyone with the raw post data and the prompt version can independently reproduce a score and verify it matches the onchain attestation. The system is auditable end-to-end.

### Epoch Boundaries Prevent Burst Gaming

Scores are computed over a fixed 30-day window. A user cannot inflate their score by posting heavily in the days before a `reveal` call — the engine measures consistency across the full epoch, and frequency variance is a direct scoring input.

Sudden activity spikes penalise consistency. Sustained, regular posting is rewarded.

### Onchain Immutability

Once an epoch is sealed via `TesseraAnchor.sol`, the attestation is permanent. The contract stores the SHA-256 hash of the full scoring snapshot alongside individual dimension scores. There is no admin function, no upgrade proxy, and no mechanism to alter or delete a sealed record. The contract contains no administrative override functions.

A user's historical behavioral record cannot be revised, removed, or improved retroactively.

### Snapshot Hashing

Before sealing, the full scoring snapshot — including all post metadata, classification results, and computed scores — is serialised to canonical JSON and hashed with SHA-256. This hash is what gets written onchain.

Any tampering with the off-chain snapshot after sealing would produce a different hash, making the discrepancy immediately detectable by comparing the stored hash against a recomputed one.

### Separation of Layers

Ingestion, evaluation, and attestation are fully decoupled. The ingestion layer cannot influence scoring logic. The scoring layer cannot influence what gets attested. Each layer can be audited independently.

This prevents a class of attacks where corrupted input data silently produces inflated scores that then get legitimised by an onchain seal.

### Bot Abuse Prevention

The bot enforces rate limiting at two levels:

- **Per user**: 5 commands per hour, tracked in Supabase
- **Global**: 30 commands per minute across all users

This prevents automated scripts from spamming `reveal` to probe the scoring system or exhaust API quotas. Repeated API failures trigger an automatic 5-minute backoff to prevent runaway loops.

### No Self-Reporting

Users do not submit their own posts for scoring. Tessera fetches posts directly from the Arena API using the user's public account ID. There is no mechanism for a user to selectively include or exclude posts from their epoch window.

### Public Verifiability

Every sealed epoch produces a Snowtrace-verifiable transaction. Anyone can look up a handle's attestation, retrieve the snapshot hash, and independently verify it against the scoring output. The entire scoring pipeline — prompt, engine, methodology version — is open source.

---

## Quick Start

Interact with Tessera directly on Arena.

**1. Activate your record**
```
@bannerusmaximus claim
```

**2. Reveal your current epoch score**
```
@bannerusmaximus reveal
```

**3. Inspect another account**
```
@bannerusmaximus inspect @handle
```

Scores are computed immediately. Epochs are sealed automatically onchain at the epoch boundary.

---

## Architecture

```
User on Arena
    │
    │  @bannerusmaximus reveal
    ▼
Listener (bot/listener.py)
    │  polls /agents/notifications every 60s
    │  detects mentions, extracts thread content
    ▼
Parser (bot/parser.py)
    │  strips HTML, identifies command + issuer handle
    ▼
Handler (bot/handlers.py)
    │  ack post sent immediately ("scoring in progress...")
    │  checks DB cache for existing epoch
    ▼
Fetcher (ingestion/fetcher.py)
    │  resolves handle → userId via Arena API
    │  paginates /threads/feed/user for epoch window
    ▼
Classifier (evaluation/classifier.py)
    │  LLM classifies each post into topic buckets
    │  uses frozen prompt v5 (hash: 1deff518231c...)
    ▼
Scoring Engine (scoring/engine.py)
    │  computes originality, focus, consistency, depth
    │  deterministic — same inputs always produce same output
    ▼
Attestation (attestation/)
    │  seals snapshot hash + scores onchain
    │  TesseraAnchor.sol on Avalanche C-Chain
    ▼
Poster (bot/poster.py)
    │  formats and posts reply as @bannerusmaximus
    ▼
User sees scores on Arena
```

---

## Scoring Dimensions

All dimensions score 0–100.

| Dimension | What It Measures |
|---|---|
| **Originality** | Topic diversity across the epoch — Shannon entropy over 6 content buckets |
| **Focus** | Coherence — how concentrated posts are in a primary topic area |
| **Consistency** | Posting regularity — frequency variance across weekly windows |
| **Depth** | Engagement quality — weighted combination of replies, quotes, tip activity |
| **Composite** | Equally weighted average of all four dimensions |

### Locked Parameters
- Epoch window: 30 days, truncated to minute
- Minimum posts: 5 (MVP) → 20 (production)
- Prompt version: v5, hash `1deff518231c...`, accuracy 84%
- Entropy buckets: 6, max entropy = log₂(6) ≈ 2.585
- Methodology version: v1.0

---

## Bot Commands

All commands are issued by mentioning `@bannerusmaximus` in an Arena post.

| Command | Usage | Response |
|---|---|---|
| `claim` | `@bannerusmaximus claim` | Registers your account, confirms activation |
| `reveal` | `@bannerusmaximus reveal` | Scores your current epoch, returns results |
| `inspect` | `@bannerusmaximus inspect @handle` | Shows another user's latest epoch |

### Rate Limits
- 5 commands per user per hour
- 30 commands per minute globally
- 3 consecutive API failures → 5 minute backoff

---

## Project Structure

```
Tessera/
├── attestation/          # Avalanche C-Chain sealing
│   ├── anchor.py         # TesseraAnchor contract interaction
│   └── TesseraAnchor.sol # Smart contract
├── bot/                  # Arena bot layer
│   ├── listener.py       # Notification polling loop
│   ├── parser.py         # HTML → ParsedCommand
│   ├── handlers.py       # claim / reveal / inspect logic
│   ├── poster.py         # All Arena reply formatters
│   └── bannerus_client.py# Regular Arena API (Bearer auth)
├── config/
│   └── chain.py          # Avalanche chain config
├── database/
│   └── client.py         # Supabase client + query helpers
├── evaluation/
│   └── classifier.py     # LLM post classifier
├── ingestion/
│   ├── arena_client.py   # Arena Agents API client
│   └── fetcher.py        # Post fetching + epoch windowing
├── scoring/
│   └── engine.py         # Deterministic scoring engine
├── api/
│   └── app.py            # FastAPI internal API
├── .env.example          # Required environment variables
└── README.md
```

---

## Database Schema

| Table | Purpose |
|---|---|
| `users` | Registered Arena accounts |
| `epochs` | 30-day epoch records per user |
| `scores` | Snapshot JSON + individual dimension scores |
| `attestations` | Onchain TX hashes and seal metadata |
| `command_log` | Rate limiting — commands issued per user |
| `bot_state` | Listener state — last processed notification ID |

---

## Smart Contract

`TesseraAnchor.sol` is deployed on Avalanche Fuji testnet during development, with mainnet deployment planned before production launch.

Each attestation stores:
- `handle` — Arena handle
- `epochStart` / `epochEnd` — epoch window
- `snapshotHash` — SHA-256 of the full scoring snapshot
- `composite` / `originality` / `focus` / `consistency` / `depth` — scores × 100 as uint16
- `promptHash` — frozen classifier prompt identifier
- `methodologyVersion` — scoring methodology version string
- `timestamp` — block timestamp

Once written, attestations are immutable. The contract contains no administrative override functions.

---

## User Journey

1. User discovers Tessera on Arena or via `@bannerusmaximus`
2. Posts `@bannerusmaximus claim` → receives activation confirmation
3. Bot registers the account in Supabase
4. At any time, user posts `@bannerusmaximus reveal`
5. Bot immediately acknowledges ("scoring in progress ⏳")
6. Fetcher pulls 30 days of posts from Arena API
7. Classifier processes each post with Claude Haiku
8. Engine computes all four dimension scores
9. Bot posts the full score breakdown to Arena (unsealed)
10. At epoch boundary (Sunday midnight UTC), cron job seals the snapshot onchain
11. TX hash is stored in Supabase and can be verified on Snowtrace
12. User can inspect any other registered user with `@bannerusmaximus inspect @handle`

---

## MoSCoW Analysis

### Must Have ✅
- Arena bot that responds to `claim`, `reveal`, `inspect`
- Deterministic scoring engine (originality, focus, consistency, depth)
- LLM post classification with frozen prompt
- Onchain attestation via smart contract
- 30-day epoch windowing with automatic sealing
- Rate limiting and crash recovery

### Should Have ✅
- Supabase caching (avoids re-scoring same epoch)
- Verbose logging with graceful shutdown
- Acknowledgment posts before long operations
- Low sample size warnings
- `.env.example` and clean repo structure

### Could Have 🔜
- Public profile website (`tessera.xyz/@handle`)
- Epoch history and leaderboard
- X (Twitter) integration
- Signal integrity pillar — rug detector (tracks CA call accuracy)

### Won't Have (this build)
- Manual score overrides (defeats the purpose)
- Paid tiers or gating
- Cross-chain attestation
- Real-time scoring (epoch-based by design)

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values. Never commit `.env`.

```
ARENA_API_KEY        # tessera_agent account — Arena Agents API key
BANNERUS_API_KEY     # bannerusmaximus account — Bearer token
ANTHROPIC_API_KEY    # Claude API key (Haiku for classification)
SUPABASE_URL         # Supabase project URL
SUPABASE_KEY         # Supabase anon/service key
PRIVATE_KEY          # Wallet private key for onchain sealing
CONTRACT_ADDRESS     # Deployed TesseraAnchor address
RPC_URL              # Avalanche RPC endpoint
```

---

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill environment variables
cp .env.example .env

# Run the bot listener
python -m bot.listener

# Run the API server
uvicorn api.app:app --reload
```

---

## Live Demo

The bot is live on Arena. Mention `@bannerusmaximus claim` on Arena to activate your record.

Walkthrough video: [YouTube](...)
