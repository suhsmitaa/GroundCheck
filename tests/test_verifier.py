from src.agents.verifier import verify


CONTEXT = "Refunds are issued within 14 days of purchase if unused."


def test_fully_grounded_answer_passes():
    answer = "Refunds are issued within 14 days of purchase if unused."
    result = verify(answer, CONTEXT, threshold=0.55)
    assert result.passed
    assert result.groundedness_score == 1.0
    assert result.unsupported_sentences == []


def test_hallucinated_sentence_is_flagged():
    answer = (
        "Refunds are issued within 14 days of purchase if unused. "
        "Refunds are also available for gift cards purchased in-store."
    )
    result = verify(answer, CONTEXT, threshold=0.55)
    assert not result.passed
    assert len(result.unsupported_sentences) == 1
    assert "gift cards" in result.unsupported_sentences[0]


def test_empty_answer_fails_closed():
    result = verify("", CONTEXT)
    assert not result.passed
    assert result.groundedness_score == 0.0
