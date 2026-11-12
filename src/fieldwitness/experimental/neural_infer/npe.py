"""Amortised neural posterior estimation (NPE) with the `sbi` library. STUB.

Status: post-hackathon research direction, NOT a decision; not implemented, not validated.
Nothing in the pipeline, the field packs or the app calls this module. The calibration in use
is ABC rejection (`fieldwitness.infer.abc`).

Idea:
- Train one conditional density estimator q(theta | summary statistics) on simulations of
  `infer.forward.simulate` (prior draws x past weather), then reuse it for every field without
  re-simulating: "amortised" calibration for regional scale (thousands of fields), where ABC
  rejection needs a fresh reference table per weather year.
- Density estimator: a masked autoregressive flow (MAF), as offered by `sbi`.
- Active learning loop: sequential rounds that propose new simulations where the current
  posterior is uncertain, stopping on a pre-registered budget.
- Acceptance before any use: simulation-based calibration and posterior coverage on synthetic
  fields (as in T4.4), and a hindcast with the 2021-12-31 cut-off compared against ABC.

Why it is not built: `sbi` (and torch) are new dependencies that need approval first
(CLAUDE.md rule 11), and the validation above has not been designed or run.
"""

NOT_IMPLEMENTED = "Post-hackathon work; not implemented"


class AmortisedNPE:
    """Placeholder for amortised NPE. Every method raises NotImplementedError."""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(NOT_IMPLEMENTED)

    def train(self, *args, **kwargs):
        raise NotImplementedError(NOT_IMPLEMENTED)

    def posterior(self, *args, **kwargs):
        raise NotImplementedError(NOT_IMPLEMENTED)

    @staticmethod
    def _require_sbi():
        """Optional import kept inside a function so the normal test suite never needs sbi."""
        import sbi  # noqa: F401  (not installed; post-hackathon)

        raise NotImplementedError(NOT_IMPLEMENTED)
