"""
Independent Component Analysis (ICA) Remote Photoplethysmography Algorithm.

Based on:
Poh, M. Z., McDuff, D. J., & Picard, R. W. (2010).
"Non-contact, automated cardiac pulse measurements using video imaging and blind source separation".
IEEE Transactions on Biomedical Engineering, 57(5), 1059-1066.
doi: 10.1109/TBME.2009.2039237
"""

from typing import Dict, Any, Tuple
import numpy as np
from scipy import signal
from app.rppg.pos_algorithm import temporal_butterworth_bandpass


def fast_ica_decomposition(
    X: np.ndarray,
    n_components: int = 3,
    max_iter: int = 200,
    tol: float = 1e-5,
    random_seed: int = 42,
) -> np.ndarray:
    """
    Fixed-point FastICA algorithm for blind source separation using pure NumPy.

    Args:
        X: 2D array of shape (n_features, n_samples).
        n_components: Number of independent components to extract.
        max_iter: Maximum iterations for convergence.
        tol: Convergence tolerance.
        random_seed: Seed for reproducible unmixing matrix initialization.

    Returns:
        S: Separated source signals of shape (n_components, n_samples).
    """
    n_features, n_samples = X.shape
    if n_samples < n_features:
        return X[:n_components, :]

    # 1. Centering
    mean_x = np.mean(X, axis=1, keepdims=True)
    X_centered = X - mean_x

    # 2. Whitening (decorrelation & unit variance)
    cov = np.dot(X_centered, X_centered.T) / (n_samples - 1)
    d, E = np.linalg.eigh(cov)

    # Sort eigenvalues in descending order
    idx = np.argsort(d)[::-1]
    d = d[idx]
    E = E[:, idx]

    # Guard against zero/negative eigenvalues
    d = np.maximum(d, 1e-12)
    D_inv_sqrt = np.diag(1.0 / np.sqrt(d[:n_components]))
    E_sub = E[:, :n_components]

    # Whitening matrix V: shape (n_components, n_features)
    V = np.dot(D_inv_sqrt, E_sub.T)
    Z = np.dot(V, X_centered)  # shape: (n_components, n_samples)

    # 3. Fixed-Point Iteration (Hyvärinen tanh contrast function)
    rng = np.random.RandomState(random_seed)
    W = rng.normal(size=(n_components, n_components))

    # Symmetric orthogonalization: W = (W * W.T)^(-1/2) * W
    def sym_decorrelation(matrix: np.ndarray) -> np.ndarray:
        s, u = np.linalg.eigh(np.dot(matrix, matrix.T))
        s = np.maximum(s, 1e-12)
        return np.dot(np.dot(u * (1.0 / np.sqrt(s)), u.T), matrix)

    W = sym_decorrelation(W)

    for _ in range(max_iter):
        W_prev = W.copy()

        # u = W * Z: shape (n_components, n_samples)
        u = np.dot(W, Z)
        g_u = np.tanh(u)
        g_prime_u = 1.0 - g_u ** 2

        # FastICA update rule
        # W_new = (g(u) * Z.T) / n_samples - diag(mean(g'(u))) * W
        term1 = np.dot(g_u, Z.T) / n_samples
        term2 = np.diag(np.mean(g_prime_u, axis=1))
        W = term1 - np.dot(term2, W)

        W = sym_decorrelation(W)

        # Convergence test
        lim = np.max(np.abs(np.abs(np.diag(np.dot(W, W_prev.T))) - 1.0))
        if lim < tol:
            break

    # Recover source signals
    S = np.dot(W, Z)
    return S


def compute_ica_rppg(
    rgb_signals: np.ndarray,
    fps: float = 30.0,
    lowcut: float = 0.7,
    highcut: float = 3.5,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Extracts rPPG pulse signal using Independent Component Analysis (Poh et al. 2010).

    Mathematical steps:
    1. Standardize RGB traces X = [R(t), G(t), B(t)]^T to zero mean and unit variance.
    2. Decompose X into 3 independent source components S using FastICA.
    3. Filter all source components in cardiac frequency band [0.7, 3.5] Hz.
    4. Automatically identify the cardiac pulse component by evaluating spectral
       prominence / peak SNR within the physiological range.

    Args:
        rgb_signals: 2D numpy array of shape (N, 3), spatially averaged R, G, B.
        fps: Video frame rate in frames per second (Hz).
        lowcut: Bandpass filter lower bound (Hz).
        highcut: Bandpass filter upper bound (Hz).

    Returns:
        filtered_rppg: 1D numpy array of selected cardiac pulse component.
        raw_rppg: 1D numpy array of reconstructed source component before bandpass.
        metadata: Dictionary containing processing statistics and component index.
    """
    rgb = np.asarray(rgb_signals, dtype=np.float64)
    n_frames, n_channels = rgb.shape

    if n_channels != 3:
        raise ValueError(f"Expected rgb_signals shape (N, 3), got {rgb.shape}")
    if n_frames < 15:
        raise ValueError(f"Insufficient frames ({n_frames}) for ICA decomposition")

    # Transpose to (3, N)
    X = rgb.T

    # Decompose into 3 independent components
    sources = fast_ica_decomposition(X, n_components=3, max_iter=250)

    # Evaluate each source in cardiac frequency band to select the arterial pulse
    best_component_idx = 0
    highest_snr = -999.0
    filtered_sources = []

    for i in range(sources.shape[0]):
        src = sources[i, :]
        filtered = temporal_butterworth_bandpass(src, lowcut=lowcut, highcut=highcut, fs=fps, order=3)
        filtered_sources.append(filtered)

        # Compute power spectrum
        nfft = max(256, 2 ** int(np.ceil(np.log2(len(filtered) * 2))))
        freqs, psd = signal.welch(filtered, fs=fps, nperseg=min(len(filtered), int(fps * 6)), nfft=nfft)

        cardiac_mask = (freqs >= lowcut) & (freqs <= highcut)
        if np.any(cardiac_mask):
            peak_power = np.max(psd[cardiac_mask])
            total_power = np.sum(psd)
            noise_power = max(total_power - peak_power, 1e-12)
            snr = 10.0 * np.log10(peak_power / noise_power)
        else:
            snr = -100.0

        if snr > highest_snr:
            highest_snr = snr
            best_component_idx = i

    selected_filtered = filtered_sources[best_component_idx]
    selected_raw = sources[best_component_idx, :]

    metadata = {
        "algorithm": "ICA (Independent Component Analysis)",
        "reference": "Poh et al., IEEE TBME 2010",
        "fps": float(fps),
        "total_frames": int(n_frames),
        "duration_sec": float(n_frames / fps) if fps > 0 else 0.0,
        "selected_component_index": int(best_component_idx),
        "component_snr_db": float(highest_snr),
        "bandpass_lowcut_hz": float(lowcut),
        "bandpass_highcut_hz": float(highcut),
    }

    return selected_filtered, selected_raw, metadata
