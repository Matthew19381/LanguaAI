"""A6: speech recognition measured on the learner's own recordings."""
import pytest

from backend.services import asr_benchmark as bench


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(bench, "STORE", tmp_path / "asr_pomiar")
    return tmp_path / "asr_pomiar"


def test_word_error_rate():
    assert bench.word_errors("Ich muss noch Brötchen kaufen.", "ich muss noch brötchen kaufen") == (0, 5)
    assert bench.word_errors("Ich muss noch Brötchen kaufen.", "Ich muss Brötchen laufen") == (2, 5)
    assert bench.word_errors("Vielen Dank.", "") == (2, 2)
    assert len(bench.SENTENCES) == 20


def test_session_id_and_index_are_checked():
    with pytest.raises(ValueError):
        bench.save_recording("../../etc", 0, b"x", "webm", None)
    with pytest.raises(ValueError):
        bench.save_recording("sesja-123", 20, b"x", "webm", None)
    with pytest.raises(ValueError):
        bench.save_recording("sesja-123", 0, b"x", "exe", None)


def test_evaluate_browser_and_models_and_recommend(store):
    sid = "sesja-1234"
    bench.save_recording(sid, 0, b"a0", "webm", "ich stehe jeden morgen um halb sieben auf")
    bench.save_recording(sid, 1, b"old", "webm", "x")
    bench.save_recording(sid, 1, b"a1", "webm", None)  # re-recorded; browser heard nothing
    heard = {"tiny": {b"a0": "ich stehe morgen um sieben auf", b"a1": "am wochenende habe ich großeltern"},
             "base": {b"a0": "ich stehe jeden morgen um halb sieben auf",
                      b"a1": "am wochenende habe ich meine großeltern besucht"},
             "small": {b"a0": "ich stehe jeden morgen um halb sieben auf",
                       b"a1": "am wochenende habe ich meine großeltern besucht"}}

    def transcribe(audio, fmt, language, size):
        if size == "small":
            raise ImportError("faster-whisper is not installed")
        return heard[size][audio]

    released = []
    out = bench.evaluate(sid, ["tiny", "base", "small", "large-v3"], transcribe, lambda: released.append(1))
    r = out["results"]
    assert released == [1]
    assert out["recordings"] == 2
    assert r["browser"]["wer"] == 0.0 and r["browser"]["sentences"] == 1   # only sentence 0 had a result
    assert r["tiny"]["wer"] == round(100 * (2 + 2) / (8 + 7), 1)
    assert r["base"]["wer"] == 0.0
    assert r["small"]["wer"] is None and "not installed" in r["small"]["error"]
    assert "large-v3" not in r                                         # not an allowed size
    assert out["recommended_whisper"] == "base"
    assert (store / sid / "wyniki.json").exists()
    assert bench.latest()["session_id"] == sid


def test_recommend_prefers_smaller_model_within_margin():
    res = {"tiny": {"wer": 12.0, "avg_seconds": 0.5}, "base": {"wer": 8.5, "avg_seconds": 1.0},
           "small": {"wer": 7.0, "avg_seconds": 2.5}, "medium": {"wer": 6.0, "avg_seconds": 9.0}}
    assert bench.recommend(res) == "small"   # base is 2.5 above the best (6.0); medium too slow
    assert bench.recommend({"browser": {"wer": 5.0}}) is None


def test_api_flow(client, store, monkeypatch):
    assert len(client.get("/api/asr-benchmark/sentences").json()["sentences"]) == 20
    r = client.post("/api/asr-benchmark/recording",
                    data={"session_id": "sesja-api-1", "index": "2", "browser_text": "Können wir uns treffen"},
                    files={"audio": ("rec.webm", b"audio", "audio/webm")})
    assert r.status_code == 200 and r.json()["recordings"] == 1
    assert client.post("/api/asr-benchmark/recording", data={"session_id": "zle/../id", "index": "0"},
                       files={"audio": ("rec.webm", b"a", "audio/webm")}).status_code == 400
    from backend.routers import asr_benchmark as router_mod
    monkeypatch.setattr(router_mod, "_transcribe", lambda a, f, l, s: "Können wir uns am Freitag vor dem Kino treffen")
    monkeypatch.setattr(router_mod, "_release", lambda: None)
    out = client.post("/api/asr-benchmark/sesja-api-1/evaluate", json={"models": ["tiny"]}).json()
    assert out["results"]["tiny"]["wer"] == 0.0 and out["recommended_whisper"] == "tiny"
    assert client.get("/api/asr-benchmark/latest").json()["result"]["session_id"] == "sesja-api-1"
    assert client.post("/api/asr-benchmark/brak-nagran/evaluate", json={}).status_code == 400


def test_first_call_untimed_and_release_keeps_configured(monkeypatch):
    sid = "sesja-czas-1"
    bench.save_recording(sid, 0, b"a0", "webm", None)
    calls = []
    bench.evaluate(sid, ["tiny"], lambda a, f, l, s: calls.append(s) or "x")
    assert calls == ["tiny", "tiny"]  # warm-up + the one sentence

    from backend.services import pronunciation_service as ps
    monkeypatch.setattr(ps, "_whisper_models", {"tiny": "T", "base": "B", "small": "S"})
    monkeypatch.setattr(ps, "_configured_size", lambda: "base")
    ps.release_models()
    assert ps._whisper_models == {"base": "B"}
