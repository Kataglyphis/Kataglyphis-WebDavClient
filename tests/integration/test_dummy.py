"""Integration test for the dummy ML preprocessing pipeline."""

import numpy as np
import pytest

from kataglyphis_webdavclient.dummy import SimpleMLPreprocessor


def test_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify pipeline output structure and deterministic labels."""

    def _mock_random_normal(*_args: object, **_kwargs: object) -> np.ndarray:
        return np.array(
            [
                [5.5, 5.5, 5.5],
                [1.0, 1.0, 1.0],
                [7.0, 5.0, 4.0],
                [6.0, 4.0, 6.0],
            ]
        )

    monkeypatch.setattr(
        "numpy.random.normal",
        _mock_random_normal,
    )

    ml = SimpleMLPreprocessor(4)
    result = ml.run_pipeline()

    assert result["features"].shape == (4, 3)
    assert result["labels"].tolist() == [1, 0, 1, 1]
    assert "mean" in result
    assert "std" in result
    assert result["joke_labels"].tolist() == [
        "Definitely ML",
        "Possibly Not",
        "Definitely ML",
        "Definitely ML",
    ]
