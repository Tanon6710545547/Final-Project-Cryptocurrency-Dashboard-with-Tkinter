import numpy as np


def sma(values, window):
    """Simple Moving Average."""
    if len(values) < window:
        return np.array(values, dtype=float)
    arr = np.array(values, dtype=float)
    weights = np.ones(window) / window
    sma_values = np.convolve(arr, weights, mode="valid")
    # pad front so length matches
    pad = [np.nan] * (len(arr) - len(sma_values))
    return np.concatenate([pad, sma_values])
