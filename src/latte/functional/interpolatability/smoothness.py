from typing import List, Optional, Tuple, Union, cast

import numpy as np

from . import _utils


def _validate_smoothness_args(
    liad_mode: str,
    max_mode: str,
    ptp_mode: Union[float, str],
    reduce_mode: str,
    p: float,
):
    assert liad_mode in _utils.__VALID_LIAD_MODE__
    assert max_mode in _utils.__VALID_MAX_MODE__
    assert reduce_mode in _utils.__VALID_REDUCE_MODE__
    if isinstance(ptp_mode, str):
        assert ptp_mode in _utils.__VALID_PTP_MODE__
    elif isinstance(ptp_mode, float):
        if not (0.0 < ptp_mode <= 1.0):
            raise ValueError("`ptp_mode` must be in (0.0, 1.0].")
    else:
        raise TypeError("`ptp_mode` must be either a string or a float.")

    if p <= 1.0:
        raise ValueError("`p` must be greater than 1.0.")


def _get_2nd_order_liad(
    z: np.ndarray, a: np.ndarray, liad_mode: str
) -> List[Tuple[np.ndarray, np.ndarray]]:
    return cast(
        List[Tuple[np.ndarray, np.ndarray]],
        _utils._liad(z, a, order=2, mode=liad_mode, return_list=True),
    )


def _get_smoothness_from_liads(
    liad1: np.ndarray,
    liad2: np.ndarray,
    z_interval: np.ndarray,
    max_mode: str = "lehmer",
    ptp_mode: Union[float, str] = "naive",
    reduce_mode: str = "attribute",
    clamp: bool = False,
    p: float = 2.0,
) -> np.ndarray:
    liad2abs = np.abs(liad2)

    if max_mode == "lehmer":
        num = _utils._lehmer_mean(liad2abs, p=p)
    elif max_mode == "naive":
        num = np.max(liad2abs, axis=-1)
    else:
        raise NotImplementedError

    if ptp_mode == "naive":
        den = np.ptp(liad1, axis=-1)
    elif isinstance(ptp_mode, float):
        den = np.quantile(liad1, q=0.5 + 0.5 * ptp_mode, axis=-1) - np.quantile(
            liad1, q=0.5 - 0.5 * ptp_mode, axis=-1
        )
    else:
        raise NotImplementedError

    den = den / z_interval
    with np.errstate(divide="ignore", invalid="ignore"):
        smth = 1.0 - num / den
    smth[:, np.all(num == 0, axis=0)] = 1.0

    if clamp:
        smth = np.clip(smth, 0.0, 1.0)

    if reduce_mode == "attribute":
        return np.mean(smth, axis=0)
    elif reduce_mode == "sample":
        return np.mean(smth, axis=-1)
    elif reduce_mode == "all":
        return np.mean(smth)
    else:
        return smth


def smoothness(
    z: np.ndarray,
    a: np.ndarray,
    reg_dim: Optional[List[int]] = None,
    liad_mode: str = "forward",
    max_mode: str = "lehmer",
    ptp_mode: Union[float, str] = "naive",
    reduce_mode: str = "attribute",
    clamp: bool = False,
    p: float = 2.0,
) -> np.ndarray:
    """
    Calculate latent smoothness.

    Smoothness is a measure of how smoothly an attribute changes with respect to a change in the regularizing latent dimension. Smoothness of a latent vector :math:`\mathbf{z}` is based on the concept of second-order derivative, and is given by

    .. math:: \operatorname{Smoothness}_{i,d}(\mathbf{z};\delta) = 1-\dfrac{\mathcal{C}_{k\in\mathfrak{K}}[\mathcal{D}_{i,d}^{(2)}(\mathbf{z} + k\delta\mathbf{e}_d;\delta )]}{\delta^{-1}\mathcal{R}_{k\in\mathfrak{K}}[\mathcal{D}_{i,d}^{(1)}(\mathbf{z} + k\delta\mathbf{e}_d;\delta )]},

    where :math:`\mathcal{D}_{i,d}^{(n)}(z; \delta)` is the :math:`n` th order latent-induced attribute difference (LIAD) as defined below, :math:`\mathbf{e}_d` is the :math:`d` th elementary vector, :math:`\mathcal{C}_{k\in\mathfrak{K}}[\cdot]` is the Lehmer mean (with `p=2` by default) of its arguments over values of :math:`k\in\mathfrak{K}`, and :math:`\mathcal{R}_{k\in\mathfrak{K}}[\cdot]` is the range of its arguments over values of :math:`k\in\mathfrak{K}` (controlled by `ptp_mode`), and :math:`\mathfrak{K}` is the set of interpolating points (controlled by `z`) used during evaluation.
    
    The first-order LIAD is defined by
    
    .. math:: \mathcal{D}_{i, d}(\mathbf{z}; \delta) = \dfrac{\mathcal{A}_i(\mathbf{z}+\delta \mathbf{e}_d) - \mathcal{A}_i(\mathbf{z})}{\delta}
    
    where :math:`\mathcal{A}_i(\cdot)` is the measurement of attribute :math:`a_i` from a sample generated from its latent vector argument, :math:`d` is the latent dimension regularizing :math:`a_i`, :math:`\delta>0` is the latent step size.
    
    Higher-order LIADs are defined by
    
    .. math:: \mathcal{D}^{(n)}_{i, d}(\mathbf{z}; \delta) =\dfrac{{\mathcal{D}^{(n-1)}_i(\mathbf{z}+\delta \mathbf{e}_d) - \mathcal{D}^{(n-1)}_i(\mathbf{z})}}{\delta}.

    Parameters
    ----------
    z : np.ndarray, (n_samples, n_interp) or (n_samples, n_features or n_attributes, n_interp)
        a batch of latent vectors
    a : np.ndarray, (n_samples, n_interp) or (n_samples, n_attributes, n_interp)
        a batch of attribute(s)
    reg_dim : Optional[List], optional
        regularized dimensions, by default None
        Attribute `a[:, i]` is regularized by `z[:, reg_dim[i]]`. If `None`, `a[:, i]` is assumed to be regularized by `z[:, i]`.
    liad_mode : str, optional
        options for calculating LIAD, by default "forward". Only "forward" is currently supported.
    max_mode : str, optional
        options for calculating array maximum of 2nd order LIAD, by default "lehmer". Must be one of {"lehmer", "naive"}. If "lehmer", the maximum is calculated using the Lehmer mean with power `p`. If "naive", the maximum is calculated using the naive array maximum.
    ptp_mode : str, optional
        options for calculating range of 1st order LIAD for normalization, by default "naive". Must be either "naive" or a float value in (0.0, 1.0]. If "naive", the range is calculated using the naive peak-to-peak range. If float, the range is taken to be the range between quantile `0.5-0.5*ptp_mode` and quantile `0.5+0.5*ptp_mode`.
    reduce_mode : str, optional
        options for reduction of the return array, by default "attribute". Must be one of {"attribute", "samples", "all", "none"}. If "all", returns a scalar. If "attribute", an average is taken along the sample axis and the return array is of shape `(n_attributes,)`. If "samples", an average is taken along the attribute axis and the return array is of shape `(n_samples,)`. If "none", returns a smoothness matrix of shape `(n_samples, n_attributes,)`.
    clamp : bool, optional
        Whether to clamp smoothness to [0, 1], by default False
    p : float, optional
        Lehmer mean power, by default 2.0 (i.e., contraharmonic mean). Only used if `max_mode == "lehmer"`. Must be greater than 1.0. 

    Returns
    -------
    np.ndarray
        smoothness array. See `reduce mode` for return shape.

    References
    ----------
    .. [1] K. N. Watcharasupat, “Controllable Music: Supervised Learning of Disentangled Representations for Music Generation”, 2021.
    """

    _validate_smoothness_args(
        liad_mode=liad_mode,
        max_mode=max_mode,
        ptp_mode=ptp_mode,
        reduce_mode=reduce_mode,
        p=p,
    )

    z, a = _utils._validate_za_shape(z, a, reg_dim=reg_dim, min_size=3)
    _utils._validate_non_constant_interp(z)
    _utils._validate_equal_interp_deltas(z)

    liads = _get_2nd_order_liad(z, a, liad_mode=liad_mode)

    liad1, _ = liads[0]
    liad2, _ = liads[1]
    z_interval = z[..., 1] - z[..., 0]

    return _get_smoothness_from_liads(
        liad1=liad1,
        liad2=liad2,
        z_interval=z_interval,
        max_mode=max_mode,
        ptp_mode=ptp_mode,
        reduce_mode=reduce_mode,
        clamp=clamp,
        p=p,
    )
