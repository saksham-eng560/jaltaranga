import json
import subprocess
import sys
from pathlib import Path

from jt_alerts import metrics, notify, polly
from jt_shared import io
from jt_shared.models import DispatchCard


def test_subject_ascii_under_100():
    s = notify.subject("URGENT_EVACUATION_DISPATCH", "यमुना Pushta Sector C " + "x" * 200)
    assert s.isascii() and len(s) < 100 and "\n" not in s


def test_ssml_and_cache_key():
    ssml = polly.build_ssml("पानी <आ> रहा है & तुरंत जाएं", "दरियागंज राहत शिविर")
    assert ssml.startswith("<speak>") and "&lt;आ&gt;" in ssml and "&amp;" in ssml and "1077" in ssml
    assert polly.audio_key(ssml) == polly.audio_key(ssml) and polly.audio_key(ssml).startswith("audio/")
    assert polly.key_from_url("https://b.s3.amazonaws.com/audio/abc.mp3?X-Amz=1") == "audio/abc.mp3"


def test_polly_disabled_offline(world):
    assert polly.enabled() is False and polly.synthesize("<speak>x</speak>") is None


def test_emf_metric_shape():
    import io as _io

    buf = _io.StringIO()
    doc = metrics.emit({"DraftLatencyMs": 120, "FallbackUsed": 1}, {"alert_type": "PREPARE"},
                       unit={"DraftLatencyMs": "Milliseconds"}, stream=buf)
    assert json.loads(buf.getvalue())["_aws"]["CloudWatchMetrics"][0]["Namespace"] == "jt"
    assert doc["DraftLatencyMs"] == 120


def test_predraft_cards_valid(world):
    assert world["predraft"]["cards"] > 0 and world["predraft"]["validation_failed"] == 0
    root = Path(io.local_root()) / "scenarios" / "yamuna-2023-07" / "dispatch_cache"
    cards = list(root.glob("*/*.json"))
    assert cards
    for p in cards[:200]:
        c = json.loads(p.read_text("utf-8"))
        DispatchCard.model_validate(c)
        assert c["validation"]["passed"] and "1077" in c["sms_hi"] and len(c["sms_hi"]) <= 160


def test_halluc_eval_replay_has_zero_untraceable_tokens(world):
    script = Path(__file__).resolve().parents[1] / "scripts" / "halluc_eval.py"
    root = Path(__file__).resolve().parents[2]
    env = {"JT_LOCAL_DATA": str(io.local_root()), "PATH": "/usr/bin:/bin",
           "PYTHONPATH": ":".join(str(root / p) for p in ("shared/py", "routing", "alerts"))}
    out = subprocess.run([sys.executable, str(script), "-n", "20"], capture_output=True, text=True, env=env)
    assert out.returncode == 0, out.stderr
    rep = json.loads(out.stdout)
    assert rep["drafts"] > 0 and rep["untraceable_tokens_in_final_cards"] == 0
    assert rep["skipped_recorded"] == 0
    used = [len(r["fields_from_llm"]) for r in rep["rows"]]
    assert used == [3, 0, 0]  # the good sample is used as-is; both failing samples fall back entirely
