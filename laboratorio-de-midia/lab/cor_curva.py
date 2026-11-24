"""Interpoladores de curva (numpy puro — o venv do app não tem scipy), para achar qual o Color Correction do MC usa."""
from __future__ import annotations

import numpy as np


def _segmento(P, t):
    i = np.clip(np.searchsorted(P[:, 0], t, side="right") - 1, 0, len(P) - 2)
    return i


def linear(P):
    P = np.asarray(P, float)
    return lambda t: np.interp(t, P[:, 0], P[:, 1])


def natural(P):
    """Spline cúbica natural (segunda derivada 0 nas pontas)."""
    P = np.asarray(P, float)
    x, y = P[:, 0], P[:, 1]
    n = len(x)
    if n == 2:
        return linear(P)
    h = np.diff(x)
    A = np.zeros((n, n)); r = np.zeros(n)
    A[0, 0] = A[-1, -1] = 1
    for i in range(1, n - 1):
        A[i, i - 1], A[i, i], A[i, i + 1] = h[i - 1], 2 * (h[i - 1] + h[i]), h[i]
        r[i] = 6 * ((y[i + 1] - y[i]) / h[i] - (y[i] - y[i - 1]) / h[i - 1])
    M = np.linalg.solve(A, r)

    def f(t):
        t = np.clip(np.asarray(t, float), x[0], x[-1])
        i = _segmento(P, t)
        a, b = x[i + 1] - t, t - x[i]
        hi = h[i]
        return (M[i] * a ** 3 + M[i + 1] * b ** 3) / (6 * hi) + (y[i] / hi - M[i] * hi / 6) * a + (y[i + 1] / hi - M[i + 1] * hi / 6) * b
    return f


def _hermite(P, m):
    x, y = P[:, 0], P[:, 1]

    def f(t):
        t = np.clip(np.asarray(t, float), x[0], x[-1])
        i = _segmento(P, t)
        h = x[i + 1] - x[i]
        u = (t - x[i]) / h
        h00, h10, h01, h11 = 2 * u**3 - 3 * u**2 + 1, u**3 - 2 * u**2 + u, -2 * u**3 + 3 * u**2, u**3 - u**2
        return h00 * y[i] + h10 * h * m[i] + h01 * y[i + 1] + h11 * h * m[i + 1]
    return f


def catmull(P):
    """Hermite com a tangente de Catmull-Rom (secante dos vizinhos); nas pontas, a secante do segmento."""
    P = np.asarray(P, float)
    x, y = P[:, 0], P[:, 1]
    n = len(x)
    m = np.empty(n)
    m[0] = (y[1] - y[0]) / (x[1] - x[0])
    m[-1] = (y[-1] - y[-2]) / (x[-1] - x[-2])
    for i in range(1, n - 1):
        m[i] = (y[i + 1] - y[i - 1]) / (x[i + 1] - x[i - 1])
    return _hermite(P, m)


def pchip(P):
    """Fritsch-Carlson (monótona: nunca passa do ponto)."""
    P = np.asarray(P, float)
    x, y = P[:, 0], P[:, 1]
    d = np.diff(y) / np.diff(x)
    n = len(x)
    m = np.empty(n)
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        m[i] = 0.0 if d[i - 1] * d[i] <= 0 else 2 / (1 / d[i - 1] + 1 / d[i])
    return _hermite(P, m)


METODOS = {"linear": linear, "natural": natural, "catmull": catmull, "pchip": pchip}
