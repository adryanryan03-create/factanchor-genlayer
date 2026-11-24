# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
from dataclasses import dataclass
from genlayer import *


@allow_storage
@dataclass
class Fact:
    submitter: str
    url: str
    question: str
    answer: str


@allow_storage
@dataclass
class ClaimCheck:
    submitter: str
    url: str
    claim: str
    supported: bool


class FactAnchor(gl.Contract):
    """
    FactAnchor stores consensus-verified snapshots of facts taken from
    public web pages.

    Anyone can ask a short factual question about a public URL
    (anchor_fact) or ask whether a page supports a specific claim
    (check_claim). The leader fetches the page and uses an LLM to extract
    the answer; every validator independently repeats the fetch and the
    extraction, and the result is only accepted when the extracted JSON
    matches exactly under the strict equivalence principle. Short factual
    answers (names, numbers, dates, booleans) are deliberately chosen so
    that strict equality is the correct, strongest check: two honest
    extractions of the same fact from the same page should be identical,
    while a hallucinated or manipulated answer will diverge and fail
    consensus.

    The stored record is therefore not "someone said this page says X" —
    it is "GenLayer consensus verified that this page said X at the time
    of the call", which makes the contract usable as a building block for
    prediction-market resolution, price/status monitoring, compliance
    snapshots, and any workflow that needs a tamper-evident web fact.
    """

    facts: TreeMap[str, Fact]
    fact_count: u256
    checks: TreeMap[str, ClaimCheck]
    check_count: u256

    def __init__(self):
        self.fact_count = u256(0)
        self.check_count = u256(0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_url(self, url: str) -> str:
        cleaned = url.strip()
        if not (cleaned.startswith("https://") or cleaned.startswith("http://")):
            raise Exception("URL must start with http:// or https://")
        if len(cleaned) > 512:
            raise Exception("URL must be at most 512 characters")
        return cleaned

    def _fetch_page_text(self, url: str) -> str:
        # Runs inside the non-deterministic block: the leader fetches the
        # page, and each validator fetches it again independently.
        response = gl.nondet.web.get(url)
        return str(response)[:6000]

    def _extract_answer(self, url: str, question: str) -> str:
        def run_extraction() -> str:
            page_text = self._fetch_page_text(url)
            task = f"""
Answer a factual question using ONLY the web page content below.

Question:
{question}

Web page content:
{page_text}

Respond in JSON:
{{
    "answer": str // a short, self-contained factual answer (a name,
                  // number, date, or short phrase). If the page does
                  // not contain the answer, use exactly "NOT_FOUND".
}}
It is mandatory that you respond only using the JSON format above,
nothing else. Your output must be only JSON without any formatting
prefix or suffix, perfectly parsable by a JSON parser.
            """
            result = gl.exec_prompt(task).replace("```json", "").replace("```", "")
            return json.dumps(json.loads(result), sort_keys=True)

        verdict = json.loads(gl.eq_principle_strict_eq(run_extraction))
        answer = str(verdict.get("answer", "NOT_FOUND")).strip()
        return answer

    def _verify_claim(self, url: str, claim: str) -> bool:
        def run_verification() -> str:
            page_text = self._fetch_page_text(url)
            task = f"""
Decide whether the web page content below supports the claim.

Claim:
{claim}

Web page content:
{page_text}

Respond in JSON:
{{
    "supported": bool // true only if the page content directly
                      // supports the claim, otherwise false
}}
It is mandatory that you respond only using the JSON format above,
nothing else. Your output must be only JSON without any formatting
prefix or suffix, perfectly parsable by a JSON parser.
            """
            result = gl.exec_prompt(task).replace("```json", "").replace("```", "")
            return json.dumps(json.loads(result), sort_keys=True)

        verdict = json.loads(gl.eq_principle_strict_eq(run_verification))
        return bool(verdict.get("supported", False))

    # ------------------------------------------------------------------
    # Public write methods
    # ------------------------------------------------------------------

    @gl.public.write
    def anchor_fact(self, url: str, question: str) -> None:
        clean_url = self._validate_url(url)
        clean_question = question.strip()
        if len(clean_question) == 0:
            raise Exception("Question must not be empty")
        if len(clean_question) > 200:
            raise Exception("Question must be at most 200 characters")

        answer = self._extract_answer(clean_url, clean_question)
        if answer == "NOT_FOUND" or len(answer) == 0:
            raise Exception("The page does not contain an answer to this question")

        fact_id = str(int(self.fact_count))
        self.facts[fact_id] = Fact(
            submitter=str(gl.message.sender_address),
            url=clean_url,
            question=clean_question,
            answer=answer,
        )
        self.fact_count = u256(int(self.fact_count) + 1)

    @gl.public.write
    def check_claim(self, url: str, claim: str) -> None:
        clean_url = self._validate_url(url)
        clean_claim = claim.strip()
        if len(clean_claim) == 0:
            raise Exception("Claim must not be empty")
        if len(clean_claim) > 280:
            raise Exception("Claim must be at most 280 characters")

        supported = self._verify_claim(clean_url, clean_claim)

        check_id = str(int(self.check_count))
        self.checks[check_id] = ClaimCheck(
            submitter=str(gl.message.sender_address),
            url=clean_url,
            claim=clean_claim,
            supported=supported,
        )
        self.check_count = u256(int(self.check_count) + 1)

    # ------------------------------------------------------------------
    # Public view methods
    # ------------------------------------------------------------------

    @gl.public.view
    def get_fact(self, fact_id: str) -> dict:
        if fact_id not in self.facts:
            raise Exception("Fact not found")
        fact = self.facts[fact_id]
        return {
            "submitter": fact.submitter,
            "url": fact.url,
            "question": fact.question,
            "answer": fact.answer,
        }

    @gl.public.view
    def get_fact_count(self) -> int:
        return int(self.fact_count)

    @gl.public.view
    def get_check(self, check_id: str) -> dict:
        if check_id not in self.checks:
            raise Exception("Claim check not found")
        check = self.checks[check_id]
        return {
            "submitter": check.submitter,
            "url": check.url,
            "claim": check.claim,
            "supported": check.supported,
        }

    @gl.public.view
    def get_check_count(self) -> int:
        return int(self.check_count)
