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


# Test 1: Missing column -> ValueError aana chahiye
def test_missing_column_raises_value_error():
    predictor = ChurnPredictor(
        pipeline=FakePipeline([0.5]), threshold=0.5, feature_names=["age", "tenure"]
    )
    # DataFrame mein sirf 'age' hai, 'tenure' missing hai
    df = pd.DataFrame({"age": [30]})
    with pytest.raises(ValueError):
        predictor.predict(df)


# Test 2: Extra aur ulti tarteeb wale columns -> _prepare theek kare aur predict sahi chale
def test_extra_and_reordered_columns_handled_correctly():
    pipeline = FakePipeline([0.8])
    predictor = ChurnPredictor(
        pipeline=pipeline, threshold=0.5, feature_names=["age", "tenure"]
    )
    # Extra column 'city' hai aur order ['tenure', 'city', 'age'] ulti/mixed hai
    df = pd.DataFrame({"tenure": [5], "city": ["Lahore"], "age": [30]})
    result = predictor.predict(df)

    assert np.array_equal(result, [1])
    # Tasalli karein ke pipeline ko columns sahi order me aur bina extra column ke mile
    assert list(pipeline.last_X.columns) == ["age", "tenure"]


# Test 3: Threshold ki boundary (Edge case: 0.5 == 0.5) -> Result 1 aana chahiye
def test_threshold_boundary_equals_one():
    predictor = ChurnPredictor(
        pipeline=FakePipeline([0.5]), threshold=0.5, feature_names=["age"]
    )
    df = pd.DataFrame({"age": [30]})
    result = predictor.predict(df)
    assert np.array_equal(result, [1])


# Test 4: Threshold se neeche (0.49 < 0.5) -> Result 0 aana chahiye
def test_below_threshold_returns_zero():
    predictor = ChurnPredictor(
        pipeline=FakePipeline([0.49]), threshold=0.5, feature_names=["age"]
    )
    df = pd.DataFrame({"age": [30]})
    result = predictor.predict(df)
    assert np.array_equal(result, [0])
