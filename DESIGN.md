# DESIGN.md

## Problem framing

Ops agents need to answer questions like _"why hasn't this order shipped"_ quickly, without manually cross-referencing three systems (orders, payments, logistics). The copilot's job is to do that cross-referencing and explain the result in plain language — grounded in real data, never guessed.

## Data model

```text
Customer 1───* Order *───1 Vehicle
                │
                ├──1 Payment
                └──1 Delivery
```

Kept intentionally small (4 entities) because the assignment is about _engineering the copilot layer_, not about modeling a full e-commerce system. Payment and Delivery are separate tables (not columns on Order) because they have independent lifecycles and independent status enums — that separation is exactly what lets the copilot detect "paid but not delivered" as a genuine cross-entity discrepancy rather than a single flag.

## Why tool-calling instead of "dump the DB into the prompt"

Two alternatives were considered:

1. **Stuff the whole orders table into the prompt as context.** Doesn't scale past a few hundred rows, leaks unrelated customer data into every request, and gives the model no way to do a targeted lookup (e.g. search by phone number).

2. **LLM tool-use (chosen).** The model sees only tool _descriptions_, not data, until it explicitly requests a specific order/customer. This scales to any DB size, keeps each request's data exposure minimal, and mirrors how a production agent would actually be built (the same pattern extends cleanly to write-actions, other services, etc.).

`tools.py` is the single source of truth for business logic: the same functions back both the LLM tool-use path and would back any future direct REST endpoints, so there's no logic duplicated between "the AI path" and "the regular API."

## Why a rule-based fallback mode exists

Committing to a hard dependency on a paid LLM API for a take-home the reviewer needs to run is a real risk (rate limits, key provisioning, cost). `LLM_PROVIDER=none` runs a small regex/keyword parser that covers every example query in the brief, so:

- the grader can run and verify correctness with zero setup friction,
- if the Groq API call throws (bad key, rate limit, network), the service degrades gracefully to this path instead of 500ing, and the response's `mode` field is honest about which path answered.

This is _not_ meant as a replacement for the LLM path in production — it's a deliberately narrow safety net, not a second NLU engine.

## Why FastAPI + SQLAlchemy + SQLite

- FastAPI: async-ready, automatic OpenAPI docs (`/docs`) which doubles as living API documentation, and Pydantic validation for free.
- SQLAlchemy: swapping SQLite for Postgres in production is a one-line `DATABASE_URL` change — no query code changes needed.
- SQLite: zero infra for a take-home reviewer to stand up; the schema was written to be Postgres-compatible from day one (explicit types, no SQLite-only features).

## Seed data design

Realism here isn't just "believable names" — it's a realistic _distribution of ops problems_. The seed script deliberately engineers:

- ~12% of paid orders stuck at `not_scheduled` delivery (the exact scenario in the assignment's second example query),
- a smaller slice of delayed deliveries with explanatory notes,
- cancelled orders with refunded/failed payments,

so the copilot has genuine discrepancies to explain rather than only happy-path data where every "what's going on" question has a boring answer.

## Trade-offs and what I'd change with more time

- **Auth/authz**: none implemented. In production this would be an internal service behind SSO, with row-level scoping if agents should only see certain regions/accounts.

- **Conversation memory**: `/query` is stateless (one question, one answer). A real ops copilot would want multi-turn context ("and what about the payment on that one?") — I'd add a `conversation_id` and store message history server-side rather than trusting the client to replay it.

- **Observability**: I'd log every tool call + LLM request/response (with PII redaction) for debuggability and for building an eval set over time.

- **Tool coverage**: only read tools exist. A natural next step is adding write-tools (e.g. `schedule_delivery`) with an explicit human-confirmation step before executing, since letting an LLM take actions unsupervised is a different risk profile than letting it answer questions.

- **Testing**: given the 5-day window I prioritized a correct, runnable system over a full pytest suite. I'd add unit tests for each `tools.py` function (deterministic, no LLM needed) and a handful of integration tests against the rule-based path for CI, since that path requires no API key and is fully deterministic.
