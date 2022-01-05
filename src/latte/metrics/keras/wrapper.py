try:
    import tensorflow as tf
    from tensorflow.keras import metrics as tfm
except ImportError as e:
    import warnings

    warnings.warn("Make sure you have TensorFlow installed.", ImportWarning)
    raise e

import typing as t

import numpy as np

from ...metrics.base import LatteMetric


def safe_numpy(t: tf.Tensor) -> np.ndarray:
    if hasattr(t, "numpy"):
        return t.numpy()
    else:
        raise RuntimeError(
            "This metric requires an EagerTensor. Please make sure you are in an eager execution mode. If you are using Keras API, compile the model with the flag `run_eagerly=True`."
        )


def tf_to_numpy(args, kwargs):
    args = [safe_numpy(a) for a in args]
    kwargs = {k: safe_numpy(kwargs[k]) for k in kwargs}

    return args, kwargs


def numpy_to_tf(val):
    if isinstance(val, np.ndarray):
        return tf.convert_to_tensor(val)
    elif isinstance(val, list):
        return [tf.convert_to_tensor(v) for v in val]
    elif isinstance(val, dict):
        return {k: tf.convert_to_tensor(val[k]) for k in val}
    else:
        raise TypeError


class KerasMetricWrapper(tfm.Metric):
    def __init__(
        self,
        metric: t.Callable[..., LatteMetric],
        name: t.Optional[str] = None,
        **kwargs
    ) -> None:
        if name is None:
            name = metric.__name__

        super().__init__(name=name)

        self.metric = metric(**kwargs)

    @tf.autograph.experimental.do_not_convert
    def update_state(self, *args, **kwargs):
        args, kwargs = tf_to_numpy(args, kwargs)
        self.metric.update_state(*args, **kwargs)

    @tf.autograph.experimental.do_not_convert
    def result(self):
        return numpy_to_tf(self.metric.compute())

    def reset_state(self):
        return self.metric.reset_state()

    def __getattr__(self, name: str):
        metric_dict = self.__getattribute__("metric")._buffers

        if name in metric_dict:
            return metric_dict[name]

        return self.__getattribute__(name)
