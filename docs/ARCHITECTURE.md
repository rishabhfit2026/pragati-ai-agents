# Architecture

## What this is

A prototype tender-intelligence pipeline for Pragati Defence Systems: upload a
tender/RFP PDF, and a chain of specialized agents turns it into a structured,
traceable, explainable bid decision (PURSUE / REVIEW / DO NOT PURSUE).

It uses only two kinds of data:
1. **Public information** about Pragati scraped from pragatidefence.com (`/knowledge`).
2. **Clearly labelled synthetic demo tenders** (`apps/api/app/demo/`), marked
   `DEMO DATA` everywhere they appear in the UI and API.

No confidential Pragati data is used or assumed anywhere in this codebase.

## System architecture

```
apps/web  (Next.js)  ---HTTP (JSON)--->  apps/api (FastAPI)  ---reads--->  /knowledge (JSON files)
                                              |
                                              +--> SQLite (dev) / Postgres+pgvector (docker-compose)
```

The frontend never talks to an LLM/OCR provider or the knowledge base
directly — every request goes through the API, which is the only place
provider credentials or file-system paths are known. This is what section 24
("no secrets in frontend") and the public/confidential data boundary require.

## Agent pipeline (the "graph")

`apps/api/app/agents/orchestrator.py` runs eight stages in a fixed order, each
one an isolated module with a typed input/output and its own `AgentRun` log
row (status, duration, retries, model, error):

```
Document Intelligence  ->  Requirement Extraction  ->  Capability Matching
   ->  Eligibility & Compliance  ->  Risk Analysis  ->  Commercial & Strategic
   ->  Opportunity Scoring  ->  Decision  ->  (human review, out of band)
```

This is implemented as an explicit state machine rather than a single prompt,
and rather than a hard dependency on the LangGraph package — the pipeline
shape (explicit nodes, explicit edges, per-node retry/fallback, full
observability) is what actually matters for reliability, and this keeps the
whole thing runnable with zero network dependencies.

Each stage's `_run_stage()` wrapper implements a one-retry
failure → retry → fallback → success loop, used for real (transient LLM/OCR
issues) and, on demand, for the developer-mode failure simulator
(`simulate_failure: OCR_TIMEOUT | LLM_TIMEOUT | INVALID_JSON | TOOL_ERROR`)
that seeds two of the demo tenders with genuine recorded failures.

### Which stages call an LLM

| Stage | LLM? | Notes |
|---|---|---|
| Document Intelligence | OCR only | Nemotron OCR v2 for scanned pages; PyMuPDF for native text |
| Requirement Extraction | **Yes** | Turns raw text into structured requirements |
| Capability Matching | **Yes + RAG** | Lexical retrieval (`app/knowledge/retriever.py`) over the product catalogue, then LLM reasoning over the retrieved candidates |
| Eligibility & Compliance | **Yes** | Reasons over the full (small) capabilities knowledge base |
| Risk Analysis | **Yes** | Reasons over the structured findings from the two agents above |
| Commercial & Strategic | **Yes** | Produces the three business sub-scores + grounded notes |
| Opportunity Scoring | No | Pure deterministic weighted sum — see below |
| Decision | No | Deterministic business rules — see below |
| Human Review | No | UI-driven override, out of band |

Every LLM-backed agent (Capability Matching, Compliance, Risk, Commercial/
Strategic) has a **deterministic twin** (`match_requirement`/`evaluate_compliance`/
`run_deterministic` in each module) that is used automatically when no real
LLM provider is configured (offline/mock mode) and as a per-call safety net
if the LLM's response is missing, malformed, or fails validation (e.g. an
uncited "MATCH", an out-of-range score, an invalid risk category). This is
the same fallback pattern already proven on Requirement Extraction — nothing
about moving these agents to LLM reasoning removes the guarantee that the
system degrades gracefully rather than corrupting the pipeline.

## Why a score is trustworthy

The **Opportunity Score is pure arithmetic** (`agents/scoring.py`) over the
outputs of the earlier agents — six weighted sub-scores (Technical Fit,
Capability Fit, Compliance Readiness, Strategic Fit, Commercial
Attractiveness, Delivery Feasibility). No LLM ever emits the number directly.
`WEIGHTS_BY_VERSION` makes the weighting itself a versioned, replayable
configuration (`score-v1` vs `score-v2`), which is what Replay compares.

The **Decision** (`agents/decision.py`) is deterministic business rules over
those same structured facts (mandatory-gap counts, unresolved-compliance
counts, score bands) — the LLM narrative explains the decision, it never
makes it.

The **Capability Matching Agent** and **Compliance Agent** are two distinct,
deliberately different lenses over the same requirements, both LLM-reasoned
when a real provider is configured:
- Capability Matching asks "does a Pragati product plausibly cover this?"
  (broad, engineering-oriented — RAG over the public product catalogue, then
  LLM judgement grounded in only the retrieved candidates; a MATCH citing a
  product id that wasn't actually retrieved is rejected and downgraded, so
  the model can't hallucinate a citation).
- Compliance asks "can we prove it?" (narrow, conservative — a certification
  claim in marketing copy is `UNKNOWN`, never `MATCH`, until independently
  verified — enforced both in the prompt and, for the deterministic fallback,
  in code). An `Unknown` can never silently become a pass in either lens.

## Data model

`apps/api/app/models/`: a `Tender` (the upload + extracted header metadata)
has many `Analysis` rows (one per pipeline run — supports re-analysis and
Replay). Each `Analysis` owns its own `Requirement`, `CapabilityMatch`,
`ComplianceItem`, `Risk`, and `AgentRun` rows, plus the six score fields and
the decision/override fields. `AuditEvent` rows are tender-scoped and carry an
optional `analysis_id`, giving a single running timeline across
re-analyses/replays/overrides (section 18).

## Provider abstractions

- **LLM** (`app/llm/`): `MockLLMProvider` is a real rule-based/regex extraction
  engine (not a stub) tuned to Indian government/defence tender phrasing —
  it's the default so the whole system runs with zero API keys. `AnthropicProvider`,
  `OpenAIProvider`, `GroqProvider`, `GeminiProvider`, and `NvidiaProvider` are
  real, optional, and gated by both `LLM_PROVIDER=...` **and**
  `ALLOW_EXTERNAL_LLM_CALLS=true` — enforced server-side in
  `get_llm_provider()`, not left to the caller. The last four share one
  `OpenAICompatibleProvider` base (`app/llm/openai_compatible.py`) since Groq,
  Gemini, and NVIDIA NIM all speak the OpenAI chat-completions wire format.
  `LLM_PROVIDER=failover` (`app/llm/failover_provider.py`) chains several of
  these — configured via `LLM_FAILOVER_ORDER`, e.g. Groq → Gemini → NVIDIA —
  and moves to the next provider on any error (rate limit, auth, outage,
  timeout, or unparseable response), which matters in practice: free-tier
  keys rate-limit fast, and stacking two or three turns that into a non-issue.
  Whichever provider actually served a given request is recorded on the
  `Analysis`/`AgentRun` rows for real observability, not just "failover" as
  an opaque label.
- **OCR** (`app/ocr/`): tries Tesseract if installed, otherwise a clearly
  labelled mock ("Simulated OCR output... no OCR engine installed") so the
  demo never overstates what happened to a scanned page. `OCR_PROVIDER=nvidia`
  (`app/ocr/nvidia_ocr_provider.py`) swaps in NVIDIA's hosted Nemotron OCR v2
  vision model instead — same `ALLOW_EXTERNAL_LLM_CALLS` gate applies, since a
  scanned page image is document content leaving the server just as much as
  extracted text is. The rendered page image is recompressed (JPEG, adaptive
  quality/resolution) to fit NVIDIA's inline base64 request budget rather than
  implementing their separate multi-step assets-upload API.

## Security posture

- File upload: extension allow-list, size cap, PDF magic-byte check, safe
  in-memory PyMuPDF parsing (no shelling out, no temp-file execution).
- CORS locked to the configured frontend origin(s).
- All configuration via environment variables (`app/config.py`); no secrets
  in the Next.js bundle — the browser only ever calls this API.
- External LLM calls are opt-in and double-gated (see above); the mock
  provider means the default deployment never sends document content
  anywhere.
- Audit log (`AuditEvent`) is append-only from the API's perspective and
  records every state-changing action, including human overrides, with actor
  and reason.

## Frontend

Next.js (App Router) + TypeScript, hand-styled dark "enterprise ops" theme
(no component library) talking to the API via `lib/api.ts`. Key pages:
`/` (Opportunity Center dashboard), `/upload`, `/tenders/[id]` (executive
summary + 7 tabs: Requirements, Compliance, Risks, Score, Timeline, Agent
Runs, Replay), `/search`, `/knowledge`, `/admin` (cross-tender agent
observability).
