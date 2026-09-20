from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

QUESTIONS = (
    ("living", "Cette personne est-elle encore en vie ?"),
    ("woman", "Est-ce une femme ?"),
    ("artist", "Est-elle principalement connue comme artiste ?"),
    ("musician", "Est-elle connue pour la musique ?"),
    ("actor", "Est-elle connue pour le cinéma ou les séries ?"),
    ("scientist", "Est-elle scientifique ou inventrice ?"),
    ("politician", "Est-elle connue pour la politique ?"),
    ("athlete", "Est-elle sportive de haut niveau ?"),
    ("writer", "Est-elle connue comme écrivaine ou écrivain ?"),
    ("born_after_1980", "Est-elle née après 1980 ?"),
    ("american", "Est-elle américaine ?"),
    ("european", "Est-elle européenne ?"),
    ("football", "Est-elle liée au football ?"),
    ("nobel", "A-t-elle reçu un prix Nobel ?"),
)


PEOPLE = (
    ("Q7186", "Marie Curie", {"woman", "scientist", "european", "nobel"}),
    ("Q937", "Albert Einstein", {"scientist", "european", "nobel"}),
    ("Q7259", "Ada Lovelace", {"woman", "scientist", "european"}),
    (
        "Q5284",
        "Billie Eilish",
        {"living", "woman", "artist", "musician", "born_after_1980", "american"},
    ),
    ("Q2831", "Michael Jackson", {"artist", "musician", "american"}),
    ("Q36153", "Beyoncé", {"living", "woman", "artist", "musician", "born_after_1980", "american"}),
    ("Q392", "Bob Dylan", {"living", "artist", "musician", "writer", "american", "nobel"}),
    ("Q33999", "Leonardo DiCaprio", {"living", "artist", "actor", "american"}),
    ("Q34436", "Margot Robbie", {"living", "woman", "artist", "actor", "born_after_1980"}),
    ("Q38111", "Leonardo da Vinci", {"artist", "scientist", "european"}),
    ("Q76", "Barack Obama", {"living", "politician", "american"}),
    ("Q22686", "Donald Trump", {"living", "politician", "american"}),
    ("Q317521", "Emmanuel Macron", {"living", "politician", "european"}),
    ("Q8023", "Nelson Mandela", {"politician", "nobel"}),
    ("Q1426", "Roger Federer", {"living", "athlete", "european"}),
    (
        "Q11571",
        "Cristiano Ronaldo",
        {"living", "athlete", "football", "born_after_1980", "european"},
    ),
    ("Q615", "Lionel Messi", {"living", "athlete", "football", "born_after_1980"}),
    ("Q41421", "Michael Jordan", {"living", "athlete", "american"}),
    ("Q47478", "Serena Williams", {"living", "woman", "athlete", "american"}),
    ("Q692", "William Shakespeare", {"artist", "writer", "european"}),
    ("Q49757", "Victor Hugo", {"artist", "writer", "politician", "european"}),
    ("Q5879", "J. K. Rowling", {"living", "woman", "artist", "writer", "european"}),
    ("Q935", "Isaac Newton", {"scientist", "european"}),
    ("Q16158566", "Greta Thunberg", {"living", "woman", "born_after_1980", "european"}),
)


@dataclass
class GameSession:
    asked: list[str] = field(default_factory=list)
    answers: dict[str, bool] = field(default_factory=dict)


class AkinatorEngine:
    def __init__(self) -> None:
        self.sessions: dict[str, GameSession] = {}

    def start(self) -> dict[str, object]:
        session_id = str(uuid4())
        self.sessions[session_id] = GameSession()
        return self._state(session_id)

    def answer(self, session_id: str, answer: str) -> dict[str, object]:
        session = self.sessions.get(session_id)
        if session is None:
            raise LookupError("Cette partie n'existe plus. Recommencez une partie.")
        if not session.asked:
            raise ValueError("Aucune question n'est active pour cette partie.")
        if answer not in {"yes", "no", "unknown"}:
            raise ValueError("Réponse invalide.")
        if answer != "unknown":
            session.answers[session.asked[-1]] = answer == "yes"
        return self._state(session_id)

    def _ranked(self, session: GameSession) -> list[tuple[int, str, str, set[str]]]:
        ranked = []
        for qid, name, traits in PEOPLE:
            score = sum(
                (trait in traits) == expected for trait, expected in session.answers.items()
            )
            ranked.append((score, qid, name, traits))
        return sorted(ranked, key=lambda item: (-item[0], item[2]))

    def _state(self, session_id: str) -> dict[str, object]:
        session = self.sessions[session_id]
        ranked = self._ranked(session)
        best_score = ranked[0][0]
        compatible = [item for item in ranked if item[0] == best_score]
        remaining_questions = [item for item in QUESTIONS if item[0] not in session.asked]
        finished = len(compatible) == 1 and len(session.answers) >= 3
        finished = finished or not remaining_questions or len(session.asked) >= 12
        if finished:
            guesses = [
                {"qid": qid, "name": name, "score": score, "max_score": len(session.answers)}
                for score, qid, name, _traits in compatible[:3]
            ]
            return {
                "session_id": session_id,
                "finished": True,
                "question": None,
                "progress": len(session.asked),
                "guesses": guesses,
            }

        trait, wording = remaining_questions[0]
        session.asked.append(trait)
        return {
            "session_id": session_id,
            "finished": False,
            "question": wording,
            "progress": len(session.asked),
            "guesses": [],
        }
