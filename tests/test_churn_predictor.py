import numpy as np
import pandas as pd
import pytest

from churn_predictor import ChurnPredictor


class FakePipeline:
    """Instead of the actual model: Returns the provided probabilities"""

    def __init__(self, probs):
        self.probs = np.array(probs)
        self.last_X = None

    def predict_proba(self, X):
        self.last_X = X
        return np.column_stack([1 - self.probs, self.probs])


def test_non_dataframe_input_raises_type_error():
    predictor = ChurnPredictor(
        pipeline=FakePipeline([0.5]), threshold=0.5, feature_names=["age"]
    )
    with pytest.raises(TypeError):
        predictor.predict([[30]])


def test_missing_column_raises_value_error():
    predictor = ChurnPredictor(
        pipeline=FakePipeline([0.5]), threshold=0.5, feature_names=["age", "tenure"]
    )
    # DataFrame has 'age' but is missing 'tenure'
    df = pd.DataFrame({"age": [30]})
    with pytest.raises(ValueError):
        predictor.predict(df)


def test_extra_and_reordered_columns_handled_correctly():
    pipeline = FakePipeline([0.8])
    predictor = ChurnPredictor(
        pipeline=pipeline, threshold=0.5, feature_names=["age", "tenure"]
    )
    # Extra 'city' column and shuffled order
    df = pd.DataFrame({"tenure": [5], "city": ["Lahore"], "age": [30]})
    result = predictor.predict(df)

    assert np.array_equal(result, [1])
    # Pipeline must receive only feature columns, in the right order
    assert list(pipeline.last_X.columns) == ["age", "tenure"]


def test_threshold_boundary_equals_one():
    predictor = ChurnPredictor(
        pipeline=FakePipeline([0.5]), threshold=0.5, feature_names=["age"]
    )
    # Edge case: probability exactly equals threshold (>= operator results in 1)
    df = pd.DataFrame({"age": [30]})
    result = predictor.predict(df)
    assert np.array_equal(result, [1])


def test_below_threshold_returns_zero():
    predictor = ChurnPredictor(
        pipeline=FakePipeline([0.49]), threshold=0.5, feature_names=["age"]
    )
    df = pd.DataFrame({"age": [30]})
    result = predictor.predict(df)
    assert np.array_equal(result, [0])


def test_predict_handles_multiple_rows():
    predictor = ChurnPredictor(
        pipeline=FakePipeline([0.2, 0.5, 0.9]),
        threshold=0.5,
        feature_names=["age"],
    )
    # 3 rows matching the 3 pipeline probabilities; 0.5 boundary yields 1
    df = pd.DataFrame({"age": [25, 35, 45]})
    result = predictor.predict(df)
    assert np.array_equal(result, [0, 1, 1])
