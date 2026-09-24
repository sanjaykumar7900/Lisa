from app.core.oracle.api_oracle import APIOracle

def test_assert_status():
    class FakeR: status_code = 200
    orch = APIOracle()
    ev = orch.assert_status(FakeR(), 200)
    assert ev.passed and ev.confidence > 0.9

def test_assert_status_fail():
    orch = APIOracle()
    ev = orch.assert_status({"status": 500}, 200)
    assert not ev.passed
