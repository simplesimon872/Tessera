# Tessera — Future Scope, Platform Expansion & Grant Budget

*This document outlines the full expansion roadmap, what each phase costs, and how grant funding would be allocated.*

---

## What We've Built (Current Stack Costs)

| Service | Purpose | Monthly Cost |
|---|---|---|
| Render Starter | Backend API hosting | $7 |
| Supabase Free | Database (Postgres) | $0 |
| Cloudflare Pages | Website hosting | $0 |
| Anthropic API (Claude Haiku) | LLM classification | ~$1–5 (usage-based) |
| Avalanche gas | Onchain sealing | ~$0.01–0.05/seal |
| **Total current** | | **~$10–15/month** |

The current stack is extremely lean. The only meaningful cost is Render at $7/month — everything else is effectively free at current scale.

---

## Platform 2 — Farcaster

### What is Farcaster?

Farcaster is a decentralised social protocol — think crypto-native Twitter that no company owns. Your account and posts live on a public protocol, not a corporation's servers. The main client app is Warpcast (like how Twitter.com is the main way people access Twitter).

Key facts relevant to Tessera:
- Posts are called "casts" (not tweets)
- Users identified by numeric FID (Farcaster ID) + optional username
- Fully open API — no gating, no approval process
- Community is heavily crypto-native: developers, DeFi, NFTs — our target audience
- Built on a new consensus layer (Snapchain) launched April 2025 — scales to millions of users
- ~40,000 daily active users as of March 2025, growing
- No native token (unlike Arena's key system)

### Why Farcaster Before X

| | Farcaster | X (Twitter) |
|---|---|---|
| API cost | Free tier available via Neynar | $200/month minimum |
| Rate limits | 300 RPM on free Neynar tier | Severely restricted on free |
| Community alignment | Crypto-native, DeFi, builders | General public |
| API stability | Open protocol, stable | Arbitrary price hikes, breaking changes |
| Bot friendliness | Designed for it | Hostile to bots |
| Build time | ~3 days (same architecture) | ~3 days |

### Neynar — The Farcaster API Layer

Neynar is the main developer platform for Farcaster — handles authentication, cast reads/writes, webhooks, and mention detection. It's what Arena's API is to Tessera now.

**Neynar pricing (confirmed tiers):**
| Tier | Monthly Cost | Rate Limit |
|---|---|---|
| Starter | Free | 300 RPM |
| Growth | ~$50–100/month | 600 RPM |
| Scale | ~$200+/month | 1200 RPM |

The free Starter tier is enough to launch and run Tessera on Farcaster at current scale. We wouldn't need to upgrade until we have hundreds of active Farcaster accounts scoring regularly.

### Farcaster Build Estimate

| Component | Description | Build Time |
|---|---|---|
| `ingestion/farcaster_client.py` | Neynar API wrapper — user lookup, cast timeline fetch, pagination | 1 day |
| `bot/farcaster_listener.py` | Webhook or polling for @mentions | 0.5 day |
| `bot/farcaster_poster.py` | Cast replies via Neynar | 0.5 day |
| Bot identity | New Farcaster account — theme TBD (herald/warden style) | 1 hour |
| Testing + deploy | End-to-end test on Farcaster testnet then mainnet | 0.5 day |
| **Total** | | **~3 days** |

The scoring engine, classifier, database, and attestation layer need zero changes.

### Farcaster Bot Identity

@bannerusmaximus is Arena-native and permanently banned on X. Farcaster needs its own identity that fits the platform's tone — more builder-focused, less arena-fighter. Candidates:
- `@tessera-warden` — guardian of records
- `@tessera-herald` — the herald angle translated
- `@epochkeeper` — epoch-focused, memorable
- `@sealbot` — functional, clear

The Farcaster community appreciates directness and technical credibility. The bot's bio and replies should lean more technical than Arena.

---

## Platform 3 — X (Twitter)

### Why We're Waiting

X API pricing makes this unviable at early stage:

| Tier | Monthly Cost | Read limit | Verdict |
|---|---|---|---|
| Free | $0 | 1 request per 24h | Useless |
| Basic | $200/month | 15,000 reads | Barely enough for small scale |
| Pro | $5,000/month | 1M reads | Needed for real scoring at scale |
| Enterprise | $42,000+/month | Custom | Large org only |

The jump from Basic ($200) to Pro ($5,000) is a 25x increase with no middle option. At Basic, 15,000 reads per month would cover roughly 100 accounts being scored once each with ~150 posts — that's the entire budget gone in a single scoring run for 100 users.

### X Build (When Funded)

Same 3-day build as Farcaster. The ingestion architecture is identical — fetch timeline, filter by date window, clean posts, score. The X API uses OAuth 2.0 and bearer tokens, similar to Arena's pattern.

**Break-even on X:** Tessera would need ~4 B2B API subscribers at $49/month to cover the Basic X API tier alone. Viable post-revenue, not before.

---

## Signal Integrity (Pillar 5) — Full Build Cost

The 5th pillar requires a price data API to evaluate CA call accuracy. Options:

| Service | Purpose | Cost |
|---|---|---|
| DexScreener API | Token price at a point in time | Free (public API, rate limited) |
| CoinGecko API | Historical token prices | Free tier: 30 calls/min; Pro: $129/month |
| CoinGecko Pro | Higher limits for production | $129/month |

DexScreener is free and covers most EVM tokens traded on DEXes — adequate for v1.2. CoinGecko is needed for CEX-listed tokens and Solana. At production scale, CoinGecko Pro at $129/month is the right call.

**Signal Integrity build estimate:**
| Component | Build Time |
|---|---|
| CA detection regex in scoring pipeline | 0.5 day |
| `signal_calls` DB table + `log_signal_call()` | 0.5 day |
| Price API client (DexScreener) | 1 day |
| Accuracy scoring logic in engine v1.2 | 1 day |
| UI updates (TRACKING → score display) | 0.5 day |
| **Total** | **~3.5 days** |

---

## B2B API Layer

| Component | Description | Build Time |
|---|---|---|
| API key management | Issue/revoke keys, associate with tiers | 1 day |
| Rate limiting middleware | Per-key rate limits in FastAPI | 0.5 day |
| Webhook on seal | POST to integrator URL when epoch seals | 1 day |
| Score badge widget | `<TesseraScore handle="@user" />` React component | 1 day |
| Bulk scoring endpoint | Batch handle scoring for launchpad KYC | 1 day |
| Billing integration | Stripe for subscription management | 1.5 days |
| **Total** | | **~6 days** |

---

## Full Running Costs at Scale (100+ B2B Accounts)

| Service | Purpose | Monthly Cost |
|---|---|---|
| Render Starter/Standard | Backend API | $7–25 |
| Supabase Pro | Database (larger data) | $25 |
| Cloudflare Pages | Website | $0 |
| Anthropic API | Claude Haiku classification | $20–50 |
| Neynar (Farcaster) | Farcaster API | Free–$100 |
| X API Basic | X platform (when live) | $200 |
| CoinGecko Pro | Signal Integrity price data | $129 |
| Avalanche gas | Onchain sealing | $1–5 |
| Domain (tessera.xyz) | Custom domain | ~$2/month |
| **Total at scale** | | **~$385–540/month** |

Break-even with 8–12 B2B API subscribers at $49/month. That's a realistic 3–6 month target after launch.

---

## Grant Budget Allocation

*If Tessera received a meaningful grant (e.g., $10,000–50,000), here is how it would be deployed:*

### $10,000 Grant
| Allocation | Amount | Purpose |
|---|---|---|
| Farcaster integration | $0 (self-build) | 3 days builder time |
| Signal Integrity (v1.2) | $0 (self-build) | 3.5 days builder time |
| B2B API layer | $0 (self-build) | 6 days builder time |
| Infrastructure runway | $1,500 | 12 months of current stack + X Basic API for 6 months |
| X API access | $1,200 | 6 months of X Basic API ($200/month) |
| CoinGecko Pro | $1,550 | 12 months of price data for Signal Integrity |
| Marketing/outreach | $2,000 | Arena key purchases for outreach, sponsored posts |
| Audit/security review | $2,000 | Smart contract and API security review |
| Buffer | $1,750 | Unexpected costs |

### $50,000 Grant
| Allocation | Amount | Purpose |
|---|---|---|
| Builder time (6 months) | $24,000 | Full-time development at $4,000/month |
| Infrastructure (2 years) | $10,000 | All services at scale including X Pro API for 2 months |
| X API Pro (2 months) | $10,000 | Full X integration at production scale |
| Marketing budget | $3,000 | Paid distribution, Arena key purchases, outreach |
| Security audit | $2,000 | Smart contract + API review |
| Legal/IP | $1,000 | Basic incorporation and IP protection |

---

## What $50K Would Unlock in 6 Months

1. **Month 1:** Farcaster integration live, bot deployed, first Farcaster epochs scoring
2. **Month 2:** Signal Integrity v1.2 — CA call accuracy scoring live with DexScreener
3. **Month 3:** B2B API layer + billing live, first paying customers
4. **Month 4:** X integration live (Basic tier), first X epochs
5. **Month 5:** Signal Integrity as 5th pillar in composite (v1.3), methodology stable
6. **Month 6:** 3+ platform coverage, B2B pipeline, Series A / follow-on grant ready

The core protocol is already built and working. The grant funds distribution, data access costs, and development time — not foundational infrastructure.

---

## Summary: Why Tessera is Grant-Efficient

Most hackathon projects need grant money to build the core product. Tessera's core is already live:
- ✅ Bot responding on Arena
- ✅ Scoring engine running
- ✅ Onchain sealing on Avalanche mainnet
- ✅ Public website with profiles, leaderboard, audit trail

Grant money goes directly to expansion and distribution — not to proving the concept works. The concept works. The TX hash proves it.

