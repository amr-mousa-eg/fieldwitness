"""NeuralFAO56 — a physics-informed neural network (PINN) idea for root-zone water. STUB.

Status: post-hackathon work; not implemented, not trained, not validated. Nothing in the pipeline,
the field packs or the app calls this module.

Planned idea (to be written up and pre-registered before any code):
- A small network maps (day, depth, field covariates) to soil water content theta.
- Loss = L_data + lambda * L_physics.
  - L_data: misfit to SMAP L4 root-zone soil moisture (coarse, 9 km; context only under the
    scale contract) and to ECOSTRESS evapotranspiration (70 m) on the field's interior pixels.
  - L_physics: residual of the 1-D Richards equation, d(theta)/dt = d/dz [K(theta) (dh/dz + 1)] - S,
    with the root-water-uptake sink S tied to the FAO-56 crop ET of the existing water balance.
  - lambda: a weight to be chosen on data before the cut-off only; no value is fixed here.
- Soil hydraulic functions K(theta), h(theta) would need a cited parameterisation (not chosen).

Why it is not built:
- It needs training time, a GPU-free plan for the 16 GB CPU machine, and a new dependency
  (for example torch), which must be approved first (CLAUDE.md rule 11).
- It needs its own validation against the FAO-56 bucket model on held-out spatial blocks and
  years, and SMAP's 9 km scale cannot support field-level claims on its own.
"""

NOT_IMPLEMENTED = "Post-hackathon work; not implemented"


class NeuralFAO56:
    """Placeholder for the PINN water-balance idea. Every method raises NotImplementedError."""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(NOT_IMPLEMENTED)

    def fit(self, *args, **kwargs):
        raise NotImplementedError(NOT_IMPLEMENTED)

    def predict(self, *args, **kwargs):
        raise NotImplementedError(NOT_IMPLEMENTED)

    @staticmethod
    def _require_torch():
        """Optional import kept inside a function so the normal test suite never needs torch."""
        import torch  # noqa: F401  (not installed; post-hackathon)

        raise NotImplementedError(NOT_IMPLEMENTED)
