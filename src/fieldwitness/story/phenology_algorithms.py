"""Advanced Algorithms for Crop Phenology Extraction and Mapping (Phase 1).

Implements and benchmarks:
1. Savitzky-Golay + Threshold Baseline (from seasons.py)
2. Standard Dynamic Time Warping (DTW) - unconstrained dynamic programming
3. Time-Weighted Dynamic Time Warping (TWDTW) with Modified Logistic Weight Function (MLWF)
4. Weighted Derivative Dynamic Time Warping (WDDTW) using central difference slopes
5. Vector Dynamic Time Warping (VDTW) using spectral angle / cosine distance on [NDVI, EVI]
6. CropFormer - Attention-based deep learning architecture (pure NumPy self-attention with
   sinusoidal temporal positional encodings and temporal attention pooling)

References:
- Maus et al. (2016), "A Time-Weighted Dynamic Time Warping Method for Land-Use and
  Land-Cover Mapping", IEEE JSTARS 9(8):3729-3739.
- Jeong et al. (2011), "Weighted dynamic time warping for time series classification",
  Pattern Recognition 44(9):2231-2240.
- Guan et al. (2018), "Mapping crop types with Vector Dynamic Time Warping",
  Remote Sensing of Environment 215:102-114.
- Yuan et al. (2024), "CropFormer: A foundation model for irregular satellite image time series",
  IEEE TGRS / CVPR Remote Sensing.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np

CROPS = ["winter_wheat", "maize", "sorghum", "fallow", "soybean"]
GRID_DAYS = 5.0
DEFAULT_ALPHA = 0.10  # MLWF steepness parameter (days^-1)
DEFAULT_BETA = 45.0  # MLWF midpoint parameter (days)


@dataclass
class PhenologyResult:
    predicted_crop: str
    detected_count: int
    scores: dict[str, float]
    algorithm: str


def compute_mlwf(
    t_query: np.ndarray,
    t_template: np.ndarray,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
) -> np.ndarray:
    """Modified Logistic Weight Function (MLWF) penalty matrix (Maus et al. 2016).

    Normalized so that identical observation timestamps (zero lag) incur zero penalty:
    w(t_q, t_t) = max(0, 1 / (1 + exp(-alpha * (|t_q - t_t| - beta))) - w_0)
    where w_0 = 1 / (1 + exp(alpha * beta)).
    """
    dt = np.abs(t_query[:, None] - t_template[None, :])
    raw_w = 1.0 / (1.0 + np.exp(-alpha * (dt - beta)))
    w0 = 1.0 / (1.0 + np.exp(alpha * beta))
    return np.maximum(0.0, (raw_w - w0) / (1.0 - w0))


def standard_dtw_distance(query: np.ndarray, template: np.ndarray) -> float:
    """Unconstrained standard Dynamic Time Warping (DTW) with Euclidean distance.

    Cost matrix computed via dynamic programming without temporal penalty.
    """
    n, m = len(query), len(template)
    if n == 0 or m == 0:
        return float("inf")
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        diff = np.abs(query[i - 1] - template)
        for j in range(1, m + 1):
            D[i, j] = diff[j - 1] + min(D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])
    return float(D[n, m] / (n + m))


def twdtw_distance(
    query: np.ndarray,
    t_query: np.ndarray,
    template: np.ndarray,
    t_template: np.ndarray,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
    gamma: float = 0.8,
) -> float:
    """Time-Weighted Dynamic Time Warping (TWDTW) using Modified Logistic Weight Function."""
    n, m = len(query), len(template)
    if n == 0 or m == 0:
        return float("inf")
    w = compute_mlwf(t_query, t_template, alpha, beta)
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        diff = np.abs(query[i - 1] - template) + gamma * w[i - 1]
        for j in range(1, m + 1):
            D[i, j] = diff[j - 1] + min(D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])
    return float(D[n, m] / (n + m))


def wddtw_distance(
    q_deriv: np.ndarray,
    t_query: np.ndarray,
    tmpl_deriv: np.ndarray,
    t_template: np.ndarray,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
    gamma: float = 0.8,
    slope_weight: float = 5.0,
) -> float:
    """Weighted Derivative Dynamic Time Warping (WDDTW) using slope differences."""
    n, m = len(q_deriv), len(tmpl_deriv)
    if n == 0 or m == 0:
        return float("inf")
    w = compute_mlwf(t_query, t_template, alpha, beta)
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        diff = slope_weight * np.abs(q_deriv[i - 1] - tmpl_deriv) + gamma * w[i - 1]
        for j in range(1, m + 1):
            D[i, j] = diff[j - 1] + min(D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])
    return float(D[n, m] / (n + m))


def vdtw_distance(
    q_vecs: np.ndarray,
    t_query: np.ndarray,
    tmpl_vecs: np.ndarray,
    t_template: np.ndarray,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
    gamma: float = 0.8,
) -> float:
    """Vector Dynamic Time Warping (VDTW) using spectral angle / cosine distance."""
    n, m = len(q_vecs), len(tmpl_vecs)
    if n == 0 or m == 0:
        return float("inf")
    w = compute_mlwf(t_query, t_template, alpha, beta)

    # Cosine distance: 1 - (u . v) / (||u|| * ||v||)
    q_norms = np.linalg.norm(q_vecs, axis=1, keepdims=True) + 1e-7
    tmpl_norms = np.linalg.norm(tmpl_vecs, axis=1, keepdims=True) + 1e-7
    q_normed = q_vecs / q_norms
    tmpl_normed = tmpl_vecs / tmpl_norms
    cos_sim = q_normed @ tmpl_normed.T
    cos_dist = 1.0 - np.clip(cos_sim, -1.0, 1.0)

    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        diff = cos_dist[i - 1] + gamma * w[i - 1]
        for j in range(1, m + 1):
            D[i, j] = diff[j - 1] + min(D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])
    return float(D[n, m] / (n + m))


class CropFormerNumPy:
    """CropFormer: Self-attention foundation architecture for irregular SITS.

    Pure-NumPy implementation featuring:
    - Input projection of multispectral time series (default [NDVI, EVI, clear_frac], or
      extended with Sentinel-2 Red-Edge / SWIR indices [NDRE1, NDRE2, NDMI, NBR2])
    - Sinusoidal temporal positional encodings (Day-of-Year aware)
    - Multi-Head Self-Attention (MHSA) capturing seasonal dependencies (e.g. wheat dormancy)
    - GELU Feed-Forward Network
    - Masked Autoencoder (MAE) self-supervised pretraining on unlabeled SITS (random timestep
      masking + reconstruction decoder)
    - End-to-end analytical backpropagation fine-tuning with Adam + Temporal Attention Pooling
    """

    def __init__(
        self,
        d_in: int = 3,
        d_model: int = 32,
        n_heads: int = 4,
        n_classes: int = len(CROPS),
        seed: int = 20261114,
        classes: list[str] | tuple[str, ...] | None = None,
    ):
        self.d_in = d_in
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads
        self.seed = seed
        self.classes = list(classes) if classes is not None else list(CROPS[:n_classes])
        n_cls = len(self.classes)

        rng = np.random.default_rng(seed)
        # Core transformer weights (keep RNG draw order intact for reproducibility)
        self.W_in = rng.normal(0, 0.15, (d_in, d_model))
        self.b_in = np.zeros(d_model)

        self.W_q = rng.normal(0, 0.15, (d_model, d_model))
        self.W_k = rng.normal(0, 0.15, (d_model, d_model))
        self.W_v = rng.normal(0, 0.15, (d_model, d_model))
        self.W_o = rng.normal(0, 0.15, (d_model, d_model))

        self.W_ff1 = rng.normal(0, 0.15, (d_model, d_model * 2))
        self.b_ff1 = np.zeros(d_model * 2)
        self.W_ff2 = rng.normal(0, 0.15, (d_model * 2, d_model))
        self.b_ff2 = np.zeros(d_model)

        self.w_pool = rng.normal(0, 0.15, (d_model, 1))

        self.W_cls = rng.normal(0, 0.15, (d_model, n_cls))
        self.b_cls = np.zeros(n_cls)

        # MAE decoder & learnable mask embedding (drawn after core weights)
        self.mask_token = rng.normal(0, 0.10, d_model)
        self.W_dec = rng.normal(0, 0.15, (d_model, d_in))
        self.b_dec = np.zeros(d_in)

        self.feat_mean: np.ndarray | None = None
        self.feat_std: np.ndarray | None = None
        self.mae_history: list[float] = []
        self.ft_history: list[float] = []

    def _temporal_pe(self, doy: np.ndarray) -> np.ndarray:
        pe = np.zeros((len(doy), self.d_model))
        div = np.exp(np.arange(0, self.d_model, 2) * -(np.log(10000.0) / self.d_model))
        pe[:, 0::2] = np.sin(doy[:, None] * div)
        pe[:, 1::2] = np.cos(doy[:, None] * div)
        return pe

    def _scale_inputs(self, x: np.ndarray) -> np.ndarray:
        arr = np.asarray(x, float)
        if self.feat_mean is not None and self.feat_std is not None:
            return (arr - self.feat_mean) / self.feat_std
        return arr

    def fit_scaler(self, samples: list[dict[str, Any]] | list[np.ndarray]) -> None:
        mats = [
            np.asarray(s["x"] if isinstance(s, dict) else s, float)
            for s in samples
            if len(s["x"] if isinstance(s, dict) else s) > 0
        ]
        if not mats:
            return
        cat = np.vstack(mats)
        self.feat_mean = np.nanmean(cat, axis=0)
        std = np.nanstd(cat, axis=0)
        self.feat_std = np.where(std > 1e-4, std, 1.0)

    @staticmethod
    def _ln_fwd(u: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        xc = u - u.mean(axis=-1, keepdims=True)
        sd = u.std(axis=-1, keepdims=True)
        denom = sd + 1e-6
        return xc / denom, xc, sd, denom

    @staticmethod
    def _ln_bwd(dy: np.ndarray, xc: np.ndarray, sd: np.ndarray, denom: np.ndarray) -> np.ndarray:
        D = dy.shape[-1]
        dsd = -np.sum(dy * xc, axis=-1, keepdims=True) / (denom * denom)
        dxc = dy / denom + np.where(sd > 1e-12, (dsd / (D * np.maximum(sd, 1e-12))) * xc, 0.0)
        return dxc - dxc.mean(axis=-1, keepdims=True)

    def _forward_encoder(self, h0: np.ndarray) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        T = len(h0)
        q_proj = h0 @ self.W_q
        k_proj = h0 @ self.W_k
        v_proj = h0 @ self.W_v
        Q = q_proj.reshape(T, self.n_heads, self.d_k).transpose(1, 0, 2)
        K = k_proj.reshape(T, self.n_heads, self.d_k).transpose(1, 0, 2)
        V = v_proj.reshape(T, self.n_heads, self.d_k).transpose(1, 0, 2)

        scores = (Q @ K.transpose(0, 2, 1)) / np.sqrt(self.d_k)
        exp_s = np.exp(scores - scores.max(axis=-1, keepdims=True))
        attn = exp_s / (exp_s.sum(axis=-1, keepdims=True) + 1e-9)

        head_out = (attn @ V).transpose(1, 0, 2).reshape(T, self.d_model)
        u1 = h0 + head_out @ self.W_o
        h1, xc1, sd1, den1 = self._ln_fwd(u1)

        ff_z = h1 @ self.W_ff1 + self.b_ff1
        c_gelu = np.sqrt(2.0 / np.pi)
        t_arg = c_gelu * (ff_z + 0.044715 * ff_z**3)
        th = np.tanh(t_arg)
        ff = 0.5 * ff_z * (1.0 + th)
        u2 = h1 + ff @ self.W_ff2 + self.b_ff2
        h2, xc2, sd2, den2 = self._ln_fwd(u2)

        cache = {
            "h0": h0,
            "Q": Q,
            "K": K,
            "V": V,
            "attn": attn,
            "head_out": head_out,
            "xc1": xc1,
            "sd1": sd1,
            "den1": den1,
            "h1": h1,
            "ff_z": ff_z,
            "th": th,
            "ff": ff,
            "xc2": xc2,
            "sd2": sd2,
            "den2": den2,
            "h2": h2,
        }
        return h2, cache

    def _backward_encoder(
        self, dh2: np.ndarray, cache: dict[str, np.ndarray]
    ) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        T = len(cache["h0"])
        du2 = self._ln_bwd(dh2, cache["xc2"], cache["sd2"], cache["den2"])
        dW_ff2 = cache["ff"].T @ du2
        db_ff2 = du2.sum(axis=0)
        dff = du2 @ self.W_ff2.T

        ff_z = cache["ff_z"]
        th = cache["th"]
        c_gelu = np.sqrt(2.0 / np.pi)
        dgelu = 0.5 * (1.0 + th) + 0.5 * ff_z * (1.0 - th * th) * c_gelu * (
            1.0 + 3.0 * 0.044715 * ff_z * ff_z
        )
        dff_z = dff * dgelu
        dW_ff1 = cache["h1"].T @ dff_z
        db_ff1 = dff_z.sum(axis=0)
        dh1 = du2 + dff_z @ self.W_ff1.T

        du1 = self._ln_bwd(dh1, cache["xc1"], cache["sd1"], cache["den1"])
        dW_o = cache["head_out"].T @ du1
        dhead = (du1 @ self.W_o.T).reshape(T, self.n_heads, self.d_k).transpose(1, 0, 2)

        attn = cache["attn"]
        Q, K, V = cache["Q"], cache["K"], cache["V"]
        dattn = dhead @ V.transpose(0, 2, 1)
        dV = attn.transpose(0, 2, 1) @ dhead

        # Softmax Jacobian per row
        dot_a = np.sum(dattn * attn, axis=-1, keepdims=True)
        dscores = attn * (dattn - dot_a) / np.sqrt(self.d_k)
        dQ = dscores @ K
        dK = dscores.transpose(0, 2, 1) @ Q

        h0 = cache["h0"]
        dQ_2d = dQ.transpose(1, 0, 2).reshape(T, self.d_model)
        dK_2d = dK.transpose(1, 0, 2).reshape(T, self.d_model)
        dV_2d = dV.transpose(1, 0, 2).reshape(T, self.d_model)

        dW_q = h0.T @ dQ_2d
        dW_k = h0.T @ dK_2d
        dW_v = h0.T @ dV_2d
        dh0 = du1 + dQ_2d @ self.W_q.T + dK_2d @ self.W_k.T + dV_2d @ self.W_v.T

        grads = {
            "W_q": dW_q,
            "W_k": dW_k,
            "W_v": dW_v,
            "W_o": dW_o,
            "W_ff1": dW_ff1,
            "b_ff1": db_ff1,
            "W_ff2": dW_ff2,
            "b_ff2": db_ff2,
        }
        return dh0, grads

    def extract_features(self, x: np.ndarray, doy: np.ndarray) -> np.ndarray:
        """Process irregular time series through self-attention and return pooled embedding."""
        T = len(x)
        if T == 0:
            return np.zeros(self.d_model)

        xs = self._scale_inputs(x)
        h0 = xs @ self.W_in + self.b_in + self._temporal_pe(doy)
        h2, _ = self._forward_encoder(h0)

        pool_weights = h2 @ self.w_pool
        pool_attn = np.exp(pool_weights - pool_weights.max())
        pool_attn = pool_attn / (pool_attn.sum() + 1e-9)
        return (pool_attn * h2).sum(axis=0)

    def fit_head(self, X_emb: np.ndarray, y: list[str], alpha: float = 1.0) -> None:
        """Calibrate classification head using L2-regularized multinomial ridge projection."""
        n_samples = len(y)
        y_idx = np.array([self.classes.index(c) for c in y])
        Y_onehot = np.zeros((n_samples, len(self.classes)))
        Y_onehot[np.arange(n_samples), y_idx] = 1.0

        reg = alpha * np.eye(self.d_model)
        self.W_cls = np.linalg.solve(X_emb.T @ X_emb + reg, X_emb.T @ (Y_onehot - 0.25))
        self.b_cls = np.mean(Y_onehot - X_emb @ self.W_cls, axis=0)

    def _adam_step(
        self,
        grads: dict[str, np.ndarray],
        m: dict[str, np.ndarray],
        v: dict[str, np.ndarray],
        step: int,
        lr: float,
        l2: float = 1e-4,
        beta1: float = 0.9,
        beta2: float = 0.999,
    ) -> None:
        b1_corr = 1.0 - beta1**step
        b2_corr = 1.0 - beta2**step
        for name, g in grads.items():
            param = getattr(self, name)
            reg = l2 * param if name.startswith("W_") else 0.0
            gn = np.clip(g + reg, -5.0, 5.0)
            if name not in m:
                m[name] = np.zeros_like(param)
                v[name] = np.zeros_like(param)
            m[name] = beta1 * m[name] + (1.0 - beta1) * gn
            v[name] = beta2 * v[name] + (1.0 - beta2) * (gn * gn)
            m_hat = m[name] / b1_corr
            v_hat = v[name] / b2_corr
            setattr(self, name, param - lr * m_hat / (np.sqrt(v_hat) + 1e-8))

    def _mae_loss_and_grads(
        self, xs: np.ndarray, doy: np.ndarray, mask: np.ndarray
    ) -> tuple[float, dict[str, np.ndarray]]:
        pe = self._temporal_pe(doy)
        tok = xs @ self.W_in + self.b_in
        tok_masked = np.where(mask[:, None], self.mask_token[None, :], tok)
        h0 = tok_masked + pe
        h2, cache = self._forward_encoder(h0)

        h2_m = h2[mask]
        x_m = xs[mask]
        pred = h2_m @ self.W_dec + self.b_dec
        diff = pred - x_m
        n_elem = max(diff.size, 1)
        loss = float(np.mean(diff * diff))
        dpred = (2.0 / n_elem) * diff

        dW_dec = h2_m.T @ dpred
        db_dec = dpred.sum(axis=0)
        dh2 = np.zeros_like(h2)
        dh2[mask] = dpred @ self.W_dec.T

        dh0, grads = self._backward_encoder(dh2, cache)
        grads["W_dec"] = dW_dec
        grads["b_dec"] = db_dec
        grads["mask_token"] = dh0[mask].sum(axis=0)
        unmasked = ~mask
        grads["W_in"] = xs[unmasked].T @ dh0[unmasked]
        grads["b_in"] = dh0[unmasked].sum(axis=0)
        return loss, grads

    def pretrain_mae(
        self,
        samples: list[dict[str, Any]],
        mask_ratio: float = 0.30,
        epochs: int = 20,
        lr: float = 0.012,
        l2: float = 1e-4,
        batch_size: int = 16,
        seed: int | None = None,
    ) -> list[float]:
        """Self-supervised Masked Autoencoder (MAE) pretraining over unlabeled SITS."""
        valid = [s for s in samples if len(s["x"]) >= 4]
        if not valid:
            return []
        self.fit_scaler(valid)
        rng = np.random.default_rng(self.seed + 1 if seed is None else seed)
        m_adam: dict[str, np.ndarray] = {}
        v_adam: dict[str, np.ndarray] = {}
        step = 0
        losses: list[float] = []

        for ep in range(epochs):
            order = rng.permutation(len(valid))
            ep_lr = lr * (0.1 + 0.9 * 0.5 * (1.0 + np.cos(np.pi * ep / max(1, epochs))))
            ep_loss = 0.0
            for start in range(0, len(order), batch_size):
                b_idx = order[start : start + batch_size]
                acc: dict[str, np.ndarray] = {}
                for i in b_idx:
                    item = valid[int(i)]
                    xs = self._scale_inputs(item["x"])
                    T = len(xs)
                    n_mask = max(1, min(T - 1, int(round(mask_ratio * T))))
                    mask = np.zeros(T, dtype=bool)
                    mask[rng.choice(T, n_mask, replace=False)] = True
                    loss_i, g_i = self._mae_loss_and_grads(xs, item["doy"], mask)
                    ep_loss += loss_i
                    for k, gv in g_i.items():
                        acc[k] = gv if k not in acc else acc[k] + gv
                inv_b = 1.0 / len(b_idx)
                for k in acc:
                    acc[k] *= inv_b
                step += 1
                self._adam_step(acc, m_adam, v_adam, step, ep_lr, l2=l2)
            losses.append(round(ep_loss / len(valid), 6))
        self.mae_history = losses
        return losses

    def _cls_loss_and_grads(
        self, xs: np.ndarray, doy: np.ndarray, y_idx: int, sample_weight: float = 1.0
    ) -> tuple[float, dict[str, np.ndarray]]:
        h0 = xs @ self.W_in + self.b_in + self._temporal_pe(doy)
        h2, cache = self._forward_encoder(h0)

        pw = h2 @ self.w_pool
        ex_p = np.exp(pw - pw.max())
        pa = ex_p / (ex_p.sum() + 1e-9)
        emb = (pa * h2).sum(axis=0)

        logits = emb @ self.W_cls + self.b_cls
        ex_l = np.exp(logits - logits.max())
        probs = ex_l / ex_l.sum()
        loss = float(-sample_weight * np.log(max(probs[y_idx], 1e-12)))

        dlogits = probs.copy()
        dlogits[y_idx] -= 1.0
        dlogits *= sample_weight

        dW_cls = np.outer(emb, dlogits)
        db_cls = dlogits
        demb = self.W_cls @ dlogits

        dpa = h2 @ demb[:, None]
        dot_p = float(np.sum(dpa * pa))
        dpw = pa * (dpa - dot_p)
        dw_pool = h2.T @ dpw
        dh2 = np.outer(pa[:, 0], demb) + dpw @ self.w_pool.T

        dh0, grads = self._backward_encoder(dh2, cache)
        grads["W_in"] = xs.T @ dh0
        grads["b_in"] = dh0.sum(axis=0)
        grads["w_pool"] = dw_pool
        grads["W_cls"] = dW_cls
        grads["b_cls"] = db_cls
        return loss, grads

    def fine_tune(
        self,
        samples: list[dict[str, Any]],
        epochs: int = 35,
        lr: float = 0.01,
        l2: float = 1e-3,
        batch_size: int = 16,
        class_weighted: bool = True,
        seed: int | None = None,
    ) -> list[float]:
        """End-to-end supervised fine-tuning of attention encoder, pooling, and classifier head."""
        valid = [s for s in samples if len(s["x"]) >= 4 and s.get("crop") in self.classes]
        if not valid:
            return []
        if self.feat_mean is None or self.feat_std is None:
            self.fit_scaler(valid)

        y_indices = np.array([self.classes.index(s["crop"]) for s in valid], dtype=int)
        if class_weighted:
            counts = np.bincount(y_indices, minlength=len(self.classes)).astype(float)
            denom = max(1, (counts > 0).sum()) * np.maximum(counts, 1.0)
            inv = np.where(counts > 0, len(valid) / denom, 0.0)
            weights = np.clip(inv[y_indices], 0.3, 4.0)
        else:
            weights = np.ones(len(valid), dtype=float)

        # Warm-start head with ridge regression
        embs = np.array([self.extract_features(s["x"], s["doy"]) for s in valid])
        self.fit_head(embs, [s["crop"] for s in valid], alpha=1.0)

        rng = np.random.default_rng(self.seed + 2 if seed is None else seed)
        m_adam: dict[str, np.ndarray] = {}
        v_adam: dict[str, np.ndarray] = {}
        step = 0
        losses: list[float] = []

        for ep in range(epochs):
            order = rng.permutation(len(valid))
            ep_lr = lr * (0.1 + 0.9 * 0.5 * (1.0 + np.cos(np.pi * ep / max(1, epochs))))
            ep_loss = 0.0
            for start in range(0, len(order), batch_size):
                b_idx = order[start : start + batch_size]
                acc: dict[str, np.ndarray] = {}
                for i in b_idx:
                    idx = int(i)
                    item = valid[idx]
                    xs = self._scale_inputs(item["x"])
                    loss_i, g_i = self._cls_loss_and_grads(
                        xs, item["doy"], int(y_indices[idx]), float(weights[idx])
                    )
                    ep_loss += loss_i
                    for k, gv in g_i.items():
                        acc[k] = gv if k not in acc else acc[k] + gv
                inv_b = 1.0 / len(b_idx)
                for k in acc:
                    acc[k] *= inv_b
                step += 1
                self._adam_step(acc, m_adam, v_adam, step, ep_lr, l2=l2)
            losses.append(round(ep_loss / len(valid), 6))
        self.ft_history = losses
        return losses

    def predict(self, x: np.ndarray, doy: np.ndarray) -> tuple[str, dict[str, float]]:
        emb = self.extract_features(x, doy)
        logits = emb @ self.W_cls + self.b_cls
        exp = np.exp(logits - logits.max())
        probs = exp / exp.sum()
        pred_class = self.classes[int(np.argmax(probs))]
        return pred_class, {c: float(probs[i]) for i, c in enumerate(self.classes)}


class PhenologySuite:
    """Suite managing reference templates and running comparative phenology benchmarks."""

    def __init__(self, grid_range: tuple[float, float] = (-100.0, 305.0), grid_step: float = 10.0):
        self.grid = np.arange(grid_range[0], grid_range[1] + grid_step, grid_step, dtype=float)
        self.ref_curves: dict[str, np.ndarray] = {}
        self.ref_derivs: dict[str, np.ndarray] = {}
        self.ref_vecs: dict[str, np.ndarray] = {}
        self.cropformer = CropFormerNumPy()

    def build_templates(self, dev_samples: list[dict[str, Any]]) -> None:
        """Extract empirical median reference curves from development set fields."""
        curves: dict[str, list[np.ndarray]] = {c: [] for c in CROPS}
        evi_curves: dict[str, list[np.ndarray]] = {c: [] for c in CROPS}

        for item in dev_samples:
            crop = item["crop"]
            if crop not in curves:
                continue
            doy = item["doy"]
            ndvi = item["ndvi"]
            evi = item["evi"]
            if len(doy) > 5:
                curves[crop].append(np.interp(self.grid, doy, ndvi))
                evi_curves[crop].append(np.interp(self.grid, doy, evi))

        for c in CROPS:
            if curves[c]:
                self.ref_curves[c] = np.median(curves[c], axis=0)
                evi_med = np.median(evi_curves[c], axis=0)
            else:
                self.ref_curves[c] = np.full(len(self.grid), 0.20)
                evi_med = np.full(len(self.grid), 0.15)

            # Central difference derivatives
            self.ref_derivs[c] = np.gradient(self.ref_curves[c], GRID_DAYS)
            self.ref_vecs[c] = np.stack([self.ref_curves[c], evi_med, self.ref_derivs[c]], axis=1)

    def fit_cropformer(
        self,
        dev_samples: list[dict[str, Any]],
        unlabeled_samples: list[dict[str, Any]] | None = None,
        mae_epochs: int = 20,
        ft_epochs: int = 40,
    ) -> None:
        mae_inputs = [
            {
                "x": np.stack([item["ndvi"], item["evi"], item["clear_frac"]], axis=1),
                "doy": item["doy"],
            }
            for item in (unlabeled_samples if unlabeled_samples is not None else dev_samples)
            if len(item["doy"]) >= 4
        ]
        if mae_epochs > 0 and mae_inputs:
            self.cropformer.pretrain_mae(mae_inputs, epochs=mae_epochs)

        ft_inputs = [
            {
                "x": np.stack([item["ndvi"], item["evi"], item["clear_frac"]], axis=1),
                "doy": item["doy"],
                "crop": item["crop"],
            }
            for item in dev_samples
            if len(item["doy"]) >= 4 and item.get("crop") in self.cropformer.classes
        ]
        if ft_epochs > 0 and ft_inputs:
            self.cropformer.fine_tune(ft_inputs, epochs=ft_epochs)
        else:
            X_embs = np.array(
                [self.cropformer.extract_features(s["x"], s["doy"]) for s in ft_inputs]
            )
            self.cropformer.fit_head(X_embs, [s["crop"] for s in ft_inputs])

    def classify_standard_dtw(self, ndvi: np.ndarray, doy: np.ndarray) -> PhenologyResult:
        q_interp = np.interp(self.grid, doy, ndvi)
        scores = {}
        for c, ref in self.ref_curves.items():
            scores[c] = standard_dtw_distance(q_interp, ref)
        pred = min(scores, key=scores.get)  # type: ignore
        return PhenologyResult(
            predicted_crop=pred,
            detected_count=0 if pred == "fallow" else 1,
            scores=scores,
            algorithm="Standard DTW",
        )

    def classify_twdtw(self, ndvi: np.ndarray, doy: np.ndarray) -> PhenologyResult:
        q_interp = np.interp(self.grid, doy, ndvi)
        scores = {}
        for c, ref in self.ref_curves.items():
            scores[c] = twdtw_distance(q_interp, self.grid, ref, self.grid)
        pred = min(scores, key=scores.get)  # type: ignore
        return PhenologyResult(
            predicted_crop=pred,
            detected_count=0 if pred == "fallow" else 1,
            scores=scores,
            algorithm="TWDTW",
        )

    def classify_wddtw(self, ndvi: np.ndarray, doy: np.ndarray) -> PhenologyResult:
        q_interp = np.interp(self.grid, doy, ndvi)
        q_deriv = np.gradient(q_interp, GRID_DAYS)
        scores = {}
        for c, tmpl_deriv in self.ref_derivs.items():
            scores[c] = wddtw_distance(q_deriv, self.grid, tmpl_deriv, self.grid)
        pred = min(scores, key=scores.get)  # type: ignore
        return PhenologyResult(
            predicted_crop=pred,
            detected_count=0 if pred == "fallow" else 1,
            scores=scores,
            algorithm="WDDTW",
        )

    def classify_vdtw(self, ndvi: np.ndarray, evi: np.ndarray, doy: np.ndarray) -> PhenologyResult:
        q_ndvi = np.interp(self.grid, doy, ndvi)
        q_evi = np.interp(self.grid, doy, evi)
        q_deriv = np.gradient(q_ndvi, GRID_DAYS)
        q_vecs = np.stack([q_ndvi, q_evi, q_deriv], axis=1)

        scores = {}
        for c, tmpl_vecs in self.ref_vecs.items():
            scores[c] = vdtw_distance(q_vecs, self.grid, tmpl_vecs, self.grid)
        pred = min(scores, key=scores.get)  # type: ignore
        return PhenologyResult(
            predicted_crop=pred,
            detected_count=0 if pred == "fallow" else 1,
            scores=scores,
            algorithm="VDTW",
        )

    def classify_cropformer(
        self, ndvi: np.ndarray, evi: np.ndarray, clear_frac: np.ndarray, doy: np.ndarray
    ) -> PhenologyResult:
        x = np.stack([ndvi, evi, clear_frac], axis=1)
        pred, scores = self.cropformer.predict(x, doy)
        return PhenologyResult(
            predicted_crop=pred,
            detected_count=0 if pred == "fallow" else 1,
            scores=scores,
            algorithm="CropFormer",
        )
