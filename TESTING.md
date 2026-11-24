# Testing FactAnchor

Manual test plan for GenLayer Studio (StudioNet) or Testnet Bradbury.
The contract is a single file: `fact_anchor.py`. Keep the runner header on
line 1 exactly as written — the GenVM rejects a deployment without it.

## Setup

1. Open GenLayer Studio (https://studio.genlayer.com) or set the CLI to
   Bradbury: `genlayer network set testnet-bradbury`.
2. Deploy `fact_anchor.py` with no constructor arguments.
3. Confirm `get_fact_count()` and `get_check_count()` both return `0`.

## Happy path — anchor a fact

Call:

```
anchor_fact("https://docs.genlayer.com", "What is the chain ID of the Bradbury testnet?")
```

Expected:

- The transaction reaches consensus (leader + validators extract the same
  short answer from the page).
- `get_fact_count()` returns `1`.
- `get_fact("0")` returns the docs URL, the exact question, your address as
  submitter, and the extracted answer.

## Happy path — check a claim

Call:

```
check_claim("https://www.genlayer.com", "GenLayer is building an intelligent blockchain")
```

Expected: `get_check_count()` returns `1` and `get_check("0")` shows the
claim with the consensus boolean.

## Failure cases (all should revert or fail consensus — never store junk)

1. **Unanswerable question**
   `anchor_fact("https://docs.genlayer.com", "What is the CEO's favourite colour?")`
   → extraction returns `NOT_FOUND`; the call raises
   "The page does not contain an answer to this question" and nothing is
   stored (`get_fact_count()` unchanged).

2. **Invalid URL**
   `anchor_fact("docs.genlayer.com", "Any question?")`
   → raises "URL must start with http:// or https://".

3. **Empty / oversized inputs**
   Empty question, a question over 200 characters, or a claim over 280
   characters → input validation raises before any web fetch happens.

4. **Ambiguous question**
   A question whose answer is a long opinionated sentence should fail the
   strict equivalence check across validators (extractions diverge) rather
   than being stored. This is intended behaviour: FactAnchor only anchors
   short factual values.

## Notes for reviewers

- The non-deterministic work (web fetch + LLM extraction) happens inside
  closures passed to `gl.eq_principle_strict_eq`; deterministic code only
  validates inputs and writes the agreed result to storage.
- Extraction prompts demand JSON-only output; the result is parsed and
  re-serialized with sorted keys before comparison so formatting noise
  cannot cause false mismatches.
- Page content is truncated to 6,000 characters to bound prompt size.
