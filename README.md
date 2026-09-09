# Cars24 AI Operations Copilot

A backend service that lets an ops team ask natural-language questions about orders, payments, and deliveries — e.g. _"Customer says they've paid for order #1289 but delivery isn't scheduled — what's going on?"_ — and get a factual, data-grounded answer.

Built for the Cars24 Backend Engineering take-home (Problem 1).

## Why Problem 1

Of the three options, this one maps most directly onto a real ops workflow (order/payment/delivery reconciliation), has a small, well-defined data model that's easy to seed realistically, and showcases the core skill being tested: wiring an LLM to real backend data via tool-calling rather than letting it hallucinate answers.

## Architecture at a glance

```text
Client ──> POST /query ──> Groq tool-use loop ──> tools.py ──> SQLite (orders/payments/deliveries)
                                  │
                                  └─ falls back to a rule-based parser if no API key is configured
```

See [DESIGN.md](./DESIGN.md) for the full write-up of design decisions and trade-offs.

## Tech stack

- **Language / framework:** Python 3.11+, FastAPI
- **DB:** SQLite via SQLAlchemy (swappable to Postgres by changing one env var)
- **LLM:** Groq (tool-use / function-calling), with a zero-dependency rule-based fallback mode so the service is fully testable without an API key
- **Seed data:** Faker, with a hand-tuned distribution of realistic edge cases

## Setup

### 1. Clone and install

```bash
git clone <this-repo-url>

cd cars24-ops-copilot

python -m venv venv

source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

- To use the real LLM copilot: set `LLM_PROVIDER=groq` and add your `GROQ_API_KEY`.

- To run without any API key (rule-based fallback mode, fully offline): set `LLM_PROVIDER=none`.

  This mode still correctly answers every example query in the assignment brief.

### 3. Seed the database

```bash
python -m app.seed_data
```

This creates `cars24_ops.db` with 25 customers, 15 catalog vehicles, and 60 orders — each with a payment and delivery record. The generator deliberately seeds a handful of "interesting" cases (payment confirmed but delivery never scheduled, delayed deliveries, failed payments) so the copilot has real discrepancies to reason about, not just happy-path data.

### 4. Run the server

```bash
uvicorn app.main:app --reload
```

The API is now live at `http://127.0.0.1:8000`. Interactive docs (Swagger UI) are auto-generated at `http://127.0.0.1:8000/docs`.

## API documentation

### `POST /query`

The core copilot endpoint. Accepts a free-text ops question.

**Request:**

```json
{
  "query": "Customer says they've paid for order #16 but delivery isn't scheduled - what's going on?"
}
```

**Response:**

```json
{
  "answer": "Order #16: the customer is correct -- payment is confirmed (Net Banking, paid 2026-08-06T09:57:56), but delivery has not been scheduled yet. This needs ops follow-up to allocate a delivery slot.",
  "mode": "llm",
  "data": {
    "...": "raw structured data the answer was grounded in"
  }
}
```

`mode` tells you whether the answer came from the LLM tool-use path, the rule-based fallback, or the fallback triggered by an LLM error — useful for debugging and for grading without an API key.

Other example queries that work out of the box:

- `"What's the payment status for order #4521?"`
- `"Give me a full status summary for order #2231."`
- `"What orders need attention right now?"` (proactive: finds paid-but-unscheduled orders)

### `GET /orders/{order_id}`

Direct REST lookup of a single order (no LLM involved) — full nested order/customer/vehicle/payment/delivery detail.

### `GET /orders?skip=0&limit=20`

Paginated listing of all orders.

### `GET /health`

Basic liveness check.

## Running the seed script again

`python -m app.seed_data` is idempotent — it drops and recreates all tables each time it's run, so you always get a clean, reproducible dataset (seeded with a fixed random seed).

## Design notes, trade-offs, and what I'd do with more time

See [DESIGN.md](./DESIGN.md).

## A note on the walkthrough video

Not included — optional per the brief. Happy to record one on request.
