# test_gpu_queue.py
import time
import uuid
from selfai_ui.utils.gpu_queue import _fits_in_window
from selfai_ui.models.benchmark_config import BenchmarkConfig


def test_fits_unknown_benchmark(db_session):
    # No config row → unknown benchmark → always allow
    assert _fits_in_window("unknown-bench", "lm-eval", remaining_minutes=60, min_remaining_minutes=0) is True


def test_fits_when_duration_fits(db_session):
    # 30-min benchmark, 60 remaining, 5 min buffer → 30 <= (60 - 5) → fits
    db_session.add(BenchmarkConfig(
        id=str(uuid.uuid4()),
        benchmark="hellaswag",
        eval_type="lm-eval",
        max_duration_minutes=30,
        created_at=int(time.time()),
        updated_at=int(time.time()),
    ))
    db_session.commit()
    assert _fits_in_window("hellaswag", "lm-eval", remaining_minutes=60, min_remaining_minutes=5) is True


def test_does_not_fit_when_window_too_short(db_session):
    # 60-min benchmark, 30 remaining → 60 <= 30 is False → doesn't fit
    db_session.add(BenchmarkConfig(
        id=str(uuid.uuid4()),
        benchmark="humaneval",
        eval_type="bigcode",
        max_duration_minutes=60,
        created_at=int(time.time()),
        updated_at=int(time.time()),
    ))
    db_session.commit()
    assert _fits_in_window("humaneval", "bigcode", remaining_minutes=30, min_remaining_minutes=0) is False
