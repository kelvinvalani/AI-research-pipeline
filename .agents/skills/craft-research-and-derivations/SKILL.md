---
name: craft-research-and-derivations
description: >-
  Craft skill for theoretical math and physics background research, notation hygiene,
  assumptions tracking, and rigorous step-by-step LaTeX/Markdown derivations.
---

# Craft: Research Notes & Mathematical Derivations

Load this skill whenever researching background context, writing `notes/*.md`, or performing analytical derivations before or alongside computation.

## Principles

1. **Conventions First, Equations Second**
   Always open a derivation note with an explicit conventions table:
   - Metric signature (e.g., $(-,+,+,+)$ vs $(+,-,-,-)$)
   - Fourier transform factors ($\frac{1}{\sqrt{2\pi}}$ vs $\frac{1}{2\pi}$ and sign of $e^{\pm i k x}$)
   - Units / nondimensionalization ($\hbar = c = m = 1$ or explicit SI/natural units)
   - Domain and function spaces (e.g., $u \in H^1(\mathbb{R}^d)$, compact support, periodic BCs)

2. **Explicit Assumptions Ledger**
   Whenever a derivation uses an assumption — smoothness, small parameter $\epsilon \ll 1$, vanishing boundary terms in integration by parts, commuting limits, non-degeneracy of a Hessian — record it immediately in `notes/` AND propagate critical assumptions to `lead.yaml`.

3. **Zero Fabricated Citations**
   - Only cite papers, arXiv IDs, theorems, or textbook sections you have actually verified or that the researcher provided.
   - If recalling a standard result from memory without direct verification, mark it explicitly as `[standard result — verify exact reference]` rather than inventing an author/year/equation number.

4. **Check Every Analytical Step**
   - Verify dimensional homogeneity at every intermediate line.
   - Check limiting cases ($a \to 0$, $d = 1$, linear limit) immediately on derived expressions.
   - For non-trivial algebraic manipulations (more than ~5 lines of expansion, commutators, or index contractions), verify the result in SymPy (`craft-symbolic-math`) rather than trusting manual algebra alone.

5. **Working with Reference Papers & Dropped Files (`inbox/` & `projects/<project>/refs/`)**
   - Always extract a concise **Reference Digest** into `notes/01_background.md` (or `notes/00_ref_<slug>.md`) listing the paper's exact sign conventions, normalizations, assumptions, and equation numbers (e.g. `Eq. (14)`). Never rely on vague paraphrases of dense equations.
   - **Math PDF extraction warning**: Plain-text PDF extraction (`rpipe inspect-ref`) can drop subscripts, superscripts, Greek letters, or minus signs in complex equations. Whenever an equation looks garbled or critical:
     1. Inspect the PDF page visually with a multimodal viewer if available; OR
     2. If the paper is from arXiv and `.tex` source is available/provided, prefer reading the `.tex` file directly for 100% lossless LaTeX; OR
     3. Explicitly flag any uncertain symbols to the researcher at the Stage 1 checkpoint before coding.
   - Never modify original reference files inside `refs/`; treat `refs/` as read-only source material.

6. **Artifact Hygiene**
   - Keep `notes/` ordered sequentially (`01_background.md`, `02_perturbation_derivation.md`, etc.).
   - Use standard LaTeX math (`$...$` inline, `$$...$$` display).
   - Separate *established facts*, *heuristic arguments*, and *open conjectures* visually so future turns never confuse a guess for a proved lemma.
