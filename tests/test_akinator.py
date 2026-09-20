import pytest

from app.akinator import AkinatorEngine


def test_game_starts_with_a_question() -> None:
    engine = AkinatorEngine()
    state = engine.start()
    assert state["finished"] is False
    assert state["question"]
    assert state["progress"] == 1


def test_game_accepts_answers_and_eventually_guesses() -> None:
    engine = AkinatorEngine()
    state = engine.start()
    answers = ["yes", "yes", "yes", "yes", "no", "no", "yes", "no", "no", "yes", "no", "yes"]
    for answer in answers:
        state = engine.answer(str(state["session_id"]), answer)
        if state["finished"]:
            break
    assert state["finished"] is True
    assert state["guesses"]


def test_unknown_session_is_rejected() -> None:
    engine = AkinatorEngine()
    with pytest.raises(LookupError):
        engine.answer("00000000-0000-0000-0000-000000000000", "yes")


def test_invalid_answer_is_rejected() -> None:
    engine = AkinatorEngine()
    state = engine.start()
    with pytest.raises(ValueError):
        engine.answer(str(state["session_id"]), "maybe")
