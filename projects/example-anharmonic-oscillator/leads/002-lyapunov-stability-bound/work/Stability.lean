/-
  Formal Lean 4 counterpart for Lead 002 (Quartic Anharmonic Oscillator).
  Uses core Lean 4 Int/Nat arithmetic (zero Mathlib dependency required) to prove
  the scaled integer-form energy positivity & phase-space bound:
      4 * H(q, p) = 2 * p^2 + 2 * w^2 * q^2 + lam * q^4
  Zero `sorry`, zero custom `axiom`, zero `native_decide`.
-/

namespace AnharmonicOscillator

/-- Scaled Hamiltonian 4 * H(q, p) = 2*p^2 + 2*w^2*q^2 + lam*q^4. -/
def scaledH (w lam q p : Int) : Int :=
  2 * (p * p) + 2 * (w * w) * (q * q) + lam * (q * q) * (q * q)

private theorem sq_nonneg (x : Int) : 0 ≤ x * x := by
  exact Int.mul_self_nonneg x

theorem scaledH_nonneg (w lam q p : Int) (hlam : 0 ≤ lam) :
    0 ≤ scaledH w lam q p := by
  unfold scaledH
  have hp : 0 ≤ 2 * (p * p) := Int.mul_nonneg (by decide) (sq_nonneg p)
  have hq : 0 ≤ 2 * (w * w) * (q * q) :=
    Int.mul_nonneg (Int.mul_nonneg (by decide) (sq_nonneg w)) (sq_nonneg q)
  have hq4 : 0 ≤ lam * (q * q) * (q * q) :=
    Int.mul_nonneg (Int.mul_nonneg hlam (sq_nonneg q)) (sq_nonneg q)
  exact Int.add_nonneg (Int.add_nonneg hp hq) hq4

theorem momentum_bound (w lam q p E4 : Int) (hlam : 0 ≤ lam)
    (hE : scaledH w lam q p ≤ E4) :
    2 * (p * p) ≤ E4 := by
  unfold scaledH at hE
  have hq : 0 ≤ 2 * (w * w) * (q * q) :=
    Int.mul_nonneg (Int.mul_nonneg (by decide) (sq_nonneg w)) (sq_nonneg q)
  have hq4 : 0 ≤ lam * (q * q) * (q * q) :=
    Int.mul_nonneg (Int.mul_nonneg hlam (sq_nonneg q)) (sq_nonneg q)
  have hrest : 0 ≤ 2 * (w * w) * (q * q) + lam * (q * q) * (q * q) :=
    Int.add_nonneg hq hq4
  omega

#print axioms scaledH_nonneg
#print axioms momentum_bound

end AnharmonicOscillator
