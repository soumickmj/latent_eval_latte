from latte.metrics.common import LatteMetric
import tensorflow as tf
from tensorflow.keras import metrics as tfm
import typing as t
import numpy as np


def tf_to_numpy(args, kwargs):
    args = [a.numpy() for a in args]
    kwargs = {k: kwargs[k].numpy() for k in kwargs}

    return args, kwargs


def numpy_to_tf(val):
    if isinstance(val, np.ndarray):
        return tf.convert_to_tensor(val)
    elif isinstance(val, list):
        return [tf.convert_to_tensor(v) for v in val]
    elif isinstance(val, dict):
        return [{k: tf.convert_to_tensor(val[k])} for k in val]
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

    def update_state(self, *args, **kwargs):
        args, kwargs = tf_to_numpy(args, kwargs)
        self.metric.update_state(*args, **kwargs)

    def result(self):
        return numpy_to_tf(self.metric.compute())

    def reset_state(self):
        return self.metric.reset_state()