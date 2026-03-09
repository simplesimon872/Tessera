# Tessera — Classification Rubric v1.0
# Read this in full before labelling a single post.
# This document freezes category semantics for the evaluation dataset.
# Do not modify after labelling begins.

---

## Categories

---

### Market & Price
**Qualifies:**
- Price predictions, targets, speculation about price movement
- "X coin will hit $Y" / "support at Z" / "looking bullish/bearish"
- Trading setups, entry/exit discussions
- Market sentiment commentary ("market is bleeding", "everything pumping")
- Chart analysis, technical analysis references

**Does NOT qualify:**
- Commentary about why a price moved (that's Technology or DeFi)
- General market meta-commentary about the industry cycle (that's Market Meta → Other)
- News about a project that has price implications but isn't price-focused

**Examples:**
- "BTC looks like it's forming a double bottom here, eyes on 85k" → Market & Price ✓
- "ETH fees spiking again lol" → Technology & Infrastructure (about the network, not price)
- "This bull run feels different" → Other (vibes/meta, not specific price analysis)

---

### Technology & Infrastructure
**Qualifies:**
- Layer 1 / Layer 2 technical discussions
- Protocol upgrades, hard forks, network performance
- Developer tools, SDKs, APIs, infrastructure
- Security, audits, exploits (technical framing)
- Scaling solutions, consensus mechanisms
- AI infrastructure (model training, inference, hardware, data pipelines) qualifies as Technology & Infrastructure unless the post is about autonomous agents or agent systems, which belong to AI & Agents

**Does NOT qualify:**
- Price of a tech-focused token (that's Market & Price)
- "X protocol is going to win" without technical substance (that's Market & Price or Other)
- AI chatbots, LLM applications, autonomous agents (that's AI & Agents)

**Examples:**
- "Ethereum's blob fees have dropped 99% since EIP-4844" → Technology & Infrastructure ✓
- "ETH going to flip BTC" → Market & Price
- "Base is building good UX" → lean toward Technology if technical substance is present
- "Running inference on 8xH100s for onchain model" → Technology & Infrastructure ✓
- "This agent just autonomously traded my portfolio" → AI & Agents (agent system, not infrastructure)

---

### DeFi & Protocols
**Qualifies:**
- DEXs, AMMs, lending protocols, yield farming
- Liquidity discussions, TVL, protocol mechanics
- Stablecoins and their mechanisms (not price speculation)
- DeFi risks, liquidations, protocol exploits with DeFi framing
- Specific protocol commentary (Uniswap, Aave, Compound, Curve, etc.)

**Does NOT qualify:**
- Token price of a DeFi project (that's Market & Price)
- General "DeFi is going to win" narratives without substance (Other)
- NFT financialisation (Other)

**Examples:**
- "Aave v3 liquidation cascade looks ugly right now" → DeFi & Protocols ✓
- "UNI pumping 30%" → Market & Price
- "This new yield strategy auto-compounds every 8 hours" → DeFi & Protocols ✓

---

### AI & Agents
**Qualifies:**
- AI agents, autonomous agents, agent frameworks
- LLMs, foundation models, AI applications in crypto
- AI x crypto intersections
- Onchain AI, agent economies
- Commentary on AI tools, AI workflows, AI capabilities

**Does NOT qualify:**
- AI infrastructure and model training hardware (that's Technology & Infrastructure)
- Price speculation on AI tokens (that's Market & Price)
- "AI is going to change everything" without substance (Other)

**Examples:**
- "This agent just autonomously executed 3 DeFi trades" → AI & Agents ✓
- "GOAT is mooning" → Market & Price
- "Claude just helped me debug my smart contract" → AI & Agents ✓
- "Training a new model on 1000 GPUs" → Technology & Infrastructure (infrastructure, not agents)

---

### Governance & DAOs
**Qualifies:**
- DAO proposals, voting, governance decisions
- Treasury management discussions
- Protocol governance, parameter changes
- Decentralisation debates with governance framing
- Community coordination, contributor evaluation

**Does NOT qualify:**
- Regulatory/government discussions (Other)
- "DAOs are the future" without substance (Other)
- Price implications of governance events (Market & Price if price-focused)

**Examples:**
- "Uniswap DAO just passed the fee switch proposal" → Governance & DAOs ✓
- "Governments are going to ban crypto" → Other
- "Just voted on the Aave proposal" → Governance & DAOs ✓

---

### Other
**Qualifies (absorbs these original categories):**
- NFTs and digital assets
- Memecoins and culture
- Macro and tradfi commentary
- Market meta / cycle commentary
- Personal and lifestyle content
- Regulatory and political commentary
- General crypto culture / community content
- Anything that does not fit the five above clearly

**Critical constraint:**
Do not use Other if a post clearly fits one of the five primary buckets, even if weakly. Other is not a fallback for uncertainty — it is for content that genuinely does not fit the five defined structural domains. If in doubt and a primary bucket is plausible, use the primary bucket.

**Use Other when:**
- The post is clearly about crypto/web3 but does not fit a specific structural bucket
- The post is personal, social, or lifestyle content
- The post is a meme, joke, or cultural reference
- The post is macro (rates, inflation, etc.) without DeFi/crypto specifics

**Examples:**
- "Just bought my first NFT" → Other ✓
- "DOGE to the moon 🚀🚀🚀" → Other ✓
- "Fed raised rates again, feels bad man" → Other ✓
- "gm everyone" → Other (or Null if < 5 meaningful words)

**Expected dataset share: 10–25 posts out of 100. If you are above 35, you are over-using Other.**

---

### Null
**Qualifies:**
- Posts with fewer than 5 meaningful words (see definition below)
- Posts where content is entirely non-textual (image only, link only with no commentary)
- Posts so ambiguous that no category is defensible
- HTML-stripped posts that reduce to empty or near-empty strings
- Pure reaction posts with no classifiable content

**Important — Null means "no topic", not "no value":**
Greeting posts (gm, gn, ge) are Null for classification purposes because they carry no topic signal. However, they are NOT discarded by the scoring engine — they are tracked separately as engagement signals that feed Consistency and Depth. Label them Null in the dataset. The pipeline handles them correctly downstream.

**Definition of "meaningful word":**
A meaningful word contains semantic content related to crypto, AI, governance, macro, or social commentary. Filler words ("the", "and", "this", "it", "a", "is", "lol") do not count toward the meaningful word count.

If fewer than 5 meaningful words AND no specific crypto, AI, governance, or macro subject is mentioned → Null. Vague hype posts with no identifiable subject are Null, not Other.

- "ETH up again" → 3 meaningful words (ETH, up, again) → NOT Null → Market & Price
- "gm all" → 0 meaningful words → Null (but counted as engagement signal in scoring)
- "This." → 0 meaningful words → Null
- "Interesting thread" → 1 meaningful word → Null
- "Great alpha right here" → 1 meaningful domain word ("alpha") but no specific subject → Null

**Null is a valid first-class classification. It is not an error.**

**Examples:**
- "gm" → Null ✓ (tracked as greeting in scoring engine)
- "gm frens ♥" → Null ✓ (tracked as greeting in scoring engine)
- "🔥🔥🔥" → Null ✓
- "This." → Null ✓
- "Exactly." → Null ✓

**Expected dataset share: 5–15 posts out of 100. If you are above 20, you are being too aggressive.**

---

## Ambiguity Resolution Rules

When a post could belong to two categories, apply these rules in order:

1. **Price mention present?** If a post mentions price AND another topic, ask: is the price the point? If yes → Market & Price. If the price is context for a technical/DeFi/governance point → use the other category.

2. **Specific protocol mentioned?** If a specific DeFi protocol is the subject → DeFi & Protocols, unless purely price-focused.

3. **Technical substance present?** If the post explains how something works, even briefly → Technology & Infrastructure.

4. **< 5 meaningful words or no specific subject?** → Null. Evaluate this before Other — Null is a structural constraint, not a semantic one.

5. **None of the above?** → Other.

---

## Category Priority Order (Tie-Breaking)

If a post legitimately qualifies for multiple categories and ambiguity remains after applying the rules above, use this priority order:

1. Market & Price
2. DeFi & Protocols
3. Technology & Infrastructure
4. AI & Agents
5. Governance & DAOs
6. Other
7. Null

Higher categories override lower ones in borderline cases. This ensures consistent resolution across the full dataset and prevents human labelling drift after the first 50 posts.

---

## What "Primary Category" Means

Every post gets exactly one label — the category that best describes the PRIMARY subject of the post. If a post is 70% price commentary and 30% technical, it is Market & Price.

Do not average. Do not split. Do not hedge.

---

## Expected Dataset Distribution

Use this as a sanity check during labelling — not a target to force:

| Category | Expected range |
|---|---|
| Market & Price | 15–25 |
| Technology & Infrastructure | 15–25 |
| DeFi & Protocols | 10–20 |
| AI & Agents | 5–15 |
| Governance & DAOs | 5–15 |
| Other | 10–25 |
| Null | 5–15 |

If Other > 35: you are over-using it.
If Null > 20: you are being too aggressive.

---

## Labelling Discipline

- Label all 100 posts in one session.
- Do not revisit or relabel earlier posts once labelling begins.
- Do not modify this rubric mid-process.
- If uncertain, apply the ambiguity rules and priority order, then move forward.
- Consistency is more important than perfection.

---

*Rubric version: v1.0*
*Frozen: do not modify after labelling begins*
