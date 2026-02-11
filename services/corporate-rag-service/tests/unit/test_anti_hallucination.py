from app.services.anti_hallucination import verify_answer


def test_anti_hallucination_passes_supported_sentence():
    valid, payload = verify_answer("Security training is required.", ["Security training is required for all employees."], 0.1, 0.2)
    assert valid is True
    assert payload["refusal_triggered"] is False


def test_anti_hallucination_rejects_unsupported_sentence():
    valid, payload = verify_answer("Mars colony is approved.", ["Security training is required for all employees."], 0.9, 0.9)
    assert valid is False
    assert payload["refusal_triggered"] is True
