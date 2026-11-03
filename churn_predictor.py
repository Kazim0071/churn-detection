import pandas as pd

class ChurnPredictor:
    """Preprocess + model + threshold ko ek saath rakhta hai."""

    def __init__(self, pipeline, threshold, feature_names, metadata=None):
        self.pipeline = pipeline
        self.threshold = float(threshold)
        self.feature_names = list(feature_names)
        self.metadata = metadata or {}

    def _prepare(self, X):
        if not isinstance(X, pd.DataFrame):
            raise TypeError("X ek pandas DataFrame hona chahiye")

        missing = set(self.feature_names) - set(X.columns)
        if missing:
            raise ValueError(f"Ye columns missing hain: {sorted(missing)}")

        return X[self.feature_names]

    def predict_proba(self, X):
        return self.pipeline.predict_proba(self._prepare(X))[:, 1]

    def predict(self, X):
        return (self.predict_proba(X) >= self.threshold).astype(int)
