"""Tests for causal input extraction and time filtering."""

import pandas as pd
from datetime import datetime, timezone, timedelta
from jt_ml.data.causal import build_causal_series_at, extract_lag_features_at
from jt_ml.data.load import load_drb_anchors

IST = timezone(timedelta(hours=5, minutes=30))


def test_no_future_anchors_leaked():
    anchors = load_drb_anchors()
    issued_at = datetime(2023, 7, 12, 12, 0, tzinfo=IST)
    hourly, age_h = build_causal_series_at(anchors, issued_at)
    
    assert hourly.index[-1] <= pd.to_datetime(issued_at)
    # Ensure all timestamps in hourly are <= issued_at
    assert (hourly.index <= pd.to_datetime(issued_at)).all()
    assert age_h >= 0.0


def test_lag_features_shape():
    anchors = load_drb_anchors()
    issued_at = datetime(2023, 7, 13, 0, 0, tzinfo=IST)
    hourly, _ = build_causal_series_at(anchors, issued_at)
    feats = extract_lag_features_at(hourly, None, issued_at)
    
    # 8 lags + 2 diffs + 4 hk + 2 sin/cos = 16 features
    assert len(feats) == 16
    assert not pd.isna(feats).any()
