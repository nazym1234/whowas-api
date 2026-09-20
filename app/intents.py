import re
import unicodedata
from dataclasses import dataclass

from app.models import Intent


@dataclass(frozen=True)
class IntentRule:
    intent: Intent
    property_id: str
    property_label: str
    patterns: tuple[str, ...]


RULES: tuple[IntentRule, ...] = (
    IntentRule(
        Intent.BIRTH_PLACE,
        "P19",
        "lieu de naissance",
        (r"\bou (?:est|etait).{0,25}\bne[e]?\b", r"lieu de naissance"),
    ),
    IntentRule(
        Intent.BIRTH_DATE,
        "P569",
        "date de naissance",
        (
            r"\bquand (?:est|etait).{0,25}\bne[e]?\b",
            r"date de naissance",
            r"en quelle annee.{0,20}\bne[e]?",
        ),
    ),
    IntentRule(
        Intent.DEATH_DATE,
        "P570",
        "date de décès",
        (
            r"\bquand (?:est|etait).{0,20}(?:mort|decede[e]?)",
            r"date de deces",
            r"en quelle annee.{0,20}(?:mort|decede[e]?)",
        ),
    ),
    IntentRule(
        Intent.NATIONALITY,
        "P27",
        "nationalité",
        (r"nationalite", r"de quel pays", r"pays d'origine"),
    ),
    IntentRule(
        Intent.OCCUPATION,
        "P106",
        "profession",
        (r"metier", r"profession", r"que faisait", r"travaillait"),
    ),
    IntentRule(
        Intent.EDUCATION,
        "P69",
        "établissement fréquenté",
        (r"etudes", r"universite", r"ecole", r"etudie"),
    ),
    IntentRule(
        Intent.SPOUSE,
        "P26",
        "conjoint ou conjointe",
        (r"conjoints?", r"conjointes?", r"epoux", r"epouses?", r"maris?", r"mariee?"),
    ),
    IntentRule(Intent.CHILDREN, "P40", "enfants", (r"enfant", r"fils", r"fille")),
    IntentRule(
        Intent.AWARDS, "P166", "distinctions", (r"prix", r"distinction", r"recompense", r"nobel")
    ),
    IntentRule(
        Intent.POSITION,
        "P39",
        "fonctions occupées",
        (r"fonction", r"poste", r"mandat", r"president", r"ministre"),
    ),
)


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def detect_intent(question: str) -> IntentRule:
    normalized = normalize(question)
    for rule in RULES:
        if any(re.search(pattern, normalized) for pattern in rule.patterns):
            return rule
    raise ValueError(
        "Question non reconnue. Consultez /intents pour voir les dix types de questions acceptés."
    )


QUESTION_WORDS = {
    "a", "au", "aux", "avec", "cette", "ce", "cet", "dans", "de", "des", "du",
    "elle", "en", "est", "etait", "il", "la", "le", "les", "lui", "ou", "par", "pour",
    "quand", "que", "quel", "quelle", "quelles", "quels", "qui", "sa", "ses", "son",
    "sont", "sur", "un", "une", "combien", "avoir", "avait", "eu",
    "annee", "date", "naissance", "ne", "nee", "mort", "morte", "decede", "decedee",
    "lieu", "nationalite", "pays", "origine", "metier", "profession", "faisait",
    "travaillait", "etudes", "universite", "ecole", "etudie", "etudiee", "conjoint",
    "conjointe", "conjoints", "conjointes", "epoux", "epouse", "epouses", "mari", "maris",
    "marie", "mariee", "enfant", "enfants", "fils",
    "fille", "filles", "prix", "distinction", "distinctions", "recompense", "recompenses",
    "nobel", "fonction", "fonctions", "poste", "postes", "mandat", "president", "ministre",
    "recu", "recue", "recus", "recues", "occupe", "occupee", "occupes", "occupees",
}


def extract_person_name(question: str) -> str:
    """Retire le vocabulaire de la question pour conserver le nom de la personne."""
    words = re.findall(r"[\wÀ-ÿ'-]+", question, flags=re.UNICODE)
    name_words = [
        word
        for word in words
        if normalize(word) not in QUESTION_WORDS or word == "Marie"
    ]
    candidate = " ".join(name_words).strip(" '-")
    candidate = re.sub(r"^[dDlL]['’]", "", candidate)
    if len(candidate) < 2:
        raise ValueError(
            "Indiquez le nom de la personne dans la question, par exemple : "
            "« Où est née Marie Curie ? »"
        )
    return candidate


def asks_for_count(question: str) -> bool:
    return bool(re.search(r"\bcombien\b", normalize(question)))
