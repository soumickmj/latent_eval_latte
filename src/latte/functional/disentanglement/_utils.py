from typing import List, Optional, Tuple

import numpy as np


def _validate_za_shape(
    z: np.ndarray,
    a: np.ndarray,
    reg_dim: Optional[List[int]] = None,
    fill_reg_dim: bool = False,
) -> Tuple[np.ndarray, np.ndarray, Optional[List[int]]]:

    assert a.ndim <= 2

    if a.ndim == 1:
        a = a[:, None]

    assert z.ndim == 2
    assert z.shape[0] == a.shape[0]
    assert z.shape[1] >= a.shape[1]

    _, n_attr = a.shape
    _, n_features = z.shape

    if reg_dim is not None:
        assert len(reg_dim) == n_attr
        assert min(reg_dim) >= 0
        assert max(reg_dim) < n_features
    elif fill_reg_dim:
        reg_dim = list(range(n_attr))

    return z, a, reg_dim


def _top2gap(
    score: np.ndarray, zi: Optional[int] = None
) -> Tuple[np.ndarray, Optional[int]]:
    """
    Calculate the difference between the top two scores, or the difference between `score[zi]` and the top score if `zi` is provided and the top score is not `score[zi]`.

    Parameters
    ----------
    score : np.ndarray, (n_features,)
        A vector of scores.
    zi : Optional[int], optional
        Index of the feature to be used as the minuend, by default None

    Returns
    -------
    Tuple[np.ndarray, Optional[int]]
        A tuple of
        - the top two scores or the difference between `score[zi]` and the top score if `zi` is provided and the top score is not `score[zi]`
        - the index of the subtrahend. If `zi` is not provided, the index of the subtrahend is None.
    """

    sc_sort = np.sort(score)
    if zi is None:
        return (sc_sort[-1] - sc_sort[-2]), None
    sc_argsort = np.argsort(score)
    return (
        (sc_sort[-1] - sc_sort[-2], sc_argsort[-2])
        if sc_argsort[-1] == zi
        else (score[zi] - sc_sort[-1], sc_argsort[-1])
    )
