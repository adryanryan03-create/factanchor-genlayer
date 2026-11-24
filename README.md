# FactAnchor — Consensus-Verified Web Fact Snapshots

FactAnchor is a GenLayer Intelligent Contract that stores **facts extracted
from public web pages and verified by validator consensus**. A stored record
does not mean "someone claims this page says X" — it means GenLayer's
validators independently fetched the page, extracted the answer, and agreed
on it exactly before anything was written on-chain.

## Live deployment (StudioNet)

FactAnchor is deployed and finalized on GenLayer StudioNet:

- **Contract:** `0xa5b15C2F47770BD6F10f51BE0bBf945f8149D127`
- **Explorer:** https://explorer-studio.genlayer.com/address/0xa5b15C2F47770BD6F10f51BE0bBf945f8149D127
- **Deploy tx:** `0x323d25c7aeb94e96172b48d9601c616b5154f705740c09ef737cbc843af41914`
- Deployed from GenLayer Studio; read methods `get_fact`, `get_fact_count`, `get_check`, `get_check_count` and write methods `anchor_fact`, `check_claim` are live.

## Why this is useful

Smart contracts cannot read the web, and a single oracle feed is a single
point of trust. FactAnchor turns any public web page into a consensus-backed
data source for short factual values:

- **Prediction / event markets** — resolve "did X happen?" against the page
  that reports it, with the verdict produced by consensus, not one reporter.
- **Price & status monitoring** — anchor a number or status shown on a public
  page (a price board, a leaderboard, a service status page) as an
  on-chain snapshot anyone can audit later.
- **Compliance & provenance snapshots** — prove what a public page stated at
  a point in time (terms, supplies, rankings) with the source URL and the
  exact question preserved next to the answer.

## How consensus is used

Both write methods follow the same leader/validator pattern:

1. The **leader** fetches the page (`gl.nondet.web.get`) and asks an LLM to
   extract the answer as compact JSON (`gl.exec_prompt`).
2. Every **validator** independently repeats the fetch and the extraction.
3. The extracted JSON is compared with the **strict equivalence principle**
   (`gl.eq_principle_strict_eq`). The result is stored only if all
   extractions match exactly.

Strict equality is a deliberate design choice, not a shortcut: the contract
only accepts **short factual answers** (names, numbers, dates, booleans),
where two honest extractions of the same fact from the same page should be
byte-identical. A hallucinated, manipulated, or ambiguous answer diverges
and fails consensus instead of being averaged in. If the page does not
contain the answer, the extraction returns `NOT_FOUND` and the transaction
reverts — the contract never stores a guess.

## Contract API

State: two `TreeMap` stores with sequential ids — `facts` and `checks` —
each record keeping the submitter address, source URL, and the exact
question/claim next to the verified result.

| Method | Type | Description |
| --- | --- | --- |
| `anchor_fact(url, question)` | write | Fetch `url`, extract the answer to `question`, store it if consensus agrees and an answer exists. |
| `check_claim(url, claim)` | write | Fetch `url`, decide whether the page directly supports `claim`, store the boolean verdict. |
| `get_fact(fact_id)` | view | Return `{submitter, url, question, answer}` for a stored fact. |
| `get_fact_count()` | view | Number of stored facts. |
| `get_check(check_id)` | view | Return `{submitter, url, claim, supported}` for a stored claim check. |
| `get_check_count()` | view | Number of stored claim checks. |

Input rules: URLs must start with `http://` or `https://` (max 512 chars),
questions max 200 chars, claims max 280 chars. Page content is truncated to
the first 6,000 characters before extraction.

## Example session (GenLayer Studio / Bradbury testnet)

1. Deploy `fact_anchor.py` (runner header on line 1 selects the
   `py-genlayer` runner — keep it intact).
2. Anchor a fact:
   `anchor_fact("https://docs.genlayer.com", "What is the chain ID of the Bradbury testnet?")`
   → after consensus, `get_fact("0")` returns the verified answer with its
   source URL and question.
3. Check a claim:
   `check_claim("https://www.genlayer.com", "GenLayer is an intelligent blockchain for the agentic economy")`
   → `get_check("0")` returns `supported: true/false` as agreed by the
   validators.

See `TESTING.md` for a fuller test walkthrough, including the failure cases
(question the page cannot answer → revert; mismatched extraction →
consensus failure).

## Limitations

- Page content can change after a snapshot; a record proves what the page
  said at call time, which is exactly what an audit trail needs — but it is
  not a live feed.
- Pages behind logins, paywalls, or heavy JavaScript may not return their
  visible content to a plain fetch.
- Questions must be answerable with a short factual value; open-ended or
  opinion questions are out of scope by design (they would fail strict
  equivalence, correctly).

## Files

- `fact_anchor.py` — the Intelligent Contract (single file, no dependencies
  beyond the GenLayer Python SDK).
- `TESTING.md` — manual test plan for Studio/Bradbury.
- `README.md` — this document.
