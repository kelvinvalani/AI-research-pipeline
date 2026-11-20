---
name: 04-lead-evaluation
description: >-
  Stage 4 of the research pipeline: synthesize verified evidence into an honest evaluation.md
  verdict (confirmed, falsified, inconclusive, or parked), update project tracking, propose
  follow-up leads, and promote battle-tested primitives to src/rpipe/shared/.
---

# Stage 4: Lead Evaluation, Synthesis & Next Leads

Use this skill after Stage 3 verification is complete (or when intentionally parking/falsifying a lead).

## Objective

Close the loop cleanly so the researcher (and any future LLM session) can understand the outcome of this lead in under 60 seconds without re-reading every script or log.

## Procedure

### 1. Audit Evidence Against `lead.yaml` Criteria
Read:
- `lead.yaml` (`success_criteria`, `falsification_criteria`, `assumptions`)
- Latest `runs/<run_id>/manifest.json` and `summary.json`
- Latest `rpipe verify` output

Evaluate **every** criterion explicitly as `MET`, `NOT MET`, or `INCONCLUSIVE`, citing exact numbers, run IDs, or proof artifacts.

### 2. Assign an Honest Final Verdict
Choose exactly one terminal/resting status:
- `confirmed` — all success criteria met AND verification gate passed with no unresolved caveats that invalidate the claim.
- `falsified` — at least one falsification criterion triggered by a verified computation or valid counterexample. *Document the exact counterexample or failure mechanism — falsified leads are high-value research outputs!*
- `inconclusive` — evidence is mixed, computational regime was too narrow, or proof attempt hit an open sub-lemma; state precisely what is needed to settle it.
- `parked` — paused intentionally due to priority shift or missing prerequisites; leave crisp resumption notes.

Update status via CLI:
```bash
uv run rpipe set-status projects/<project>/leads/<lead-id> <confirmed|falsified|inconclusive|parked>
```

### 3. Write `evaluation.md`
Fill every section of `evaluation.md`:
1. **Executive Summary** (2–4 sentences: hypothesis, method, bottom-line result).
2. **Criteria Table** mapping each `lead.yaml` criterion to exact evidence.
3. **Key Results** (equations, tables, key metrics, relative paths to plots/proofs/runs).
4. **Verification Audit** (what invariants, limiting cases, convergence orders, or formal checks passed, plus honest limitations and unverified assumptions).
5. **Next Leads & Promotion Decisions**:
   - Propose 1–3 concrete follow-up leads (with crisp hypotheses and suggested `kind`).
   - Decide whether any clean, general-purpose math/physics utility written in `work/` deserves promotion to `src/rpipe/shared/`.

### 4. Update the Parent Project Index
Update `projects/<project>/README.md` so the Lead Index table reflects the final status and one-line verdict summary. If promoting a primitive to `src/rpipe/shared/`, add unit tests in `tests/` and link it in `projects/<project>/README.md`.

### 5. Present Concise Debrief to Researcher
Summarize the verdict, key quantitative/formal findings, any surprises or caveats, and the top recommended next lead(s).
