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
        Intent.SUMMARY,
        "DESCRIPTION",
        "présentation",
        (r"\bqui est\b", r"presente(?:-moi)?", r"biographie", r"parle-moi de"),
    ),
    IntentRule(
        Intent.BIRTH_PLACE,
        "P19",
        "lieu de naissance",
        (
            r"\bou (?:est|etait).{0,25}\bne[e]?\b",
            r"lieu de naissance",
            r"\bne[e]?\s+a\b",
        ),
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
            r"\b(?:ils|elles)\s+sont\s+mort(?:s|es)?\b",
            r"\bsont-(?:ils|elles)\s+mort(?:s|es)?\b",
            r"\b(?:mort|decede)s?\s+quand\b",
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
        (
            r"\bconjoints?\b",
            r"\bconjointes?\b",
            r"\bepoux\b",
            r"\bepouses?\b",
            r"\bmaris?\b",
            r"combien de temps.*(?:ete|est|etait)\s+mariee?\b",
            r"avec qui",
        ),
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
    IntentRule(Intent.FAMILY, "P22", "père", (r"\bpere\b", r"\bpapa\b")),
    IntentRule(Intent.FAMILY, "P25", "mère", (r"\bmere\b", r"\bmaman\b")),
    IntentRule(Intent.FAMILY, "P3373", "frères et sœurs", (r"frere", r"soeur", r"fratrie")),
    IntentRule(
        Intent.EMPLOYER,
        "P108",
        "employeur",
        (r"employeur", r"travaille pour", r"entreprise"),
    ),
    IntentRule(
        Intent.RESIDENCE,
        "P551",
        "lieu de résidence",
        (r"habite", r"residence", r"vit actuellement"),
    ),
    IntentRule(Intent.RELIGION, "P140", "religion", (r"religion", r"religieux")),
    IntentRule(Intent.POLITICAL_PARTY, "P102", "parti politique", (r"parti politique", r"parti")),
    IntentRule(Intent.LANGUAGES, "P1412", "langues parlées", (r"langue", r"parle quelles")),
    IntentRule(
        Intent.NOTABLE_WORK,
        "P800",
        "œuvres principales",
        (r"oeuvre", r"livre", r"film connu"),
    ),
    IntentRule(
        Intent.FIELD,
        "P101",
        "domaine d'activité",
        (r"domaine", r"specialite", r"discipline"),
    ),
    IntentRule(Intent.GENRE, "P136", "genre artistique", (r"genre musical", r"genre artistique")),
    IntentRule(Intent.INSTRUMENT, "P1303", "instrument", (r"instrument",)),
    IntentRule(
        Intent.HEIGHT,
        "P2048",
        "taille",
        (r"combien mesure", r"quelle taille", r"\btaille\b"),
    ),
    IntentRule(
        Intent.CAUSE_OF_DEATH,
        "P509",
        "cause du décès",
        (r"cause de.{0,10}mort", r"mort de quoi"),
    ),
    IntentRule(Intent.BURIAL_PLACE, "P119", "lieu d'inhumation", (r"enterre", r"inhume", r"tombe")),
    IntentRule(Intent.WEBSITE, "P856", "site officiel", (r"site officiel", r"site web")),
)


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def detect_intent(question: str) -> IntentRule:
    normalized = normalize(question)
    ordered_rules = sorted(RULES, key=lambda rule: rule.intent is Intent.SUMMARY)
    for rule in ordered_rules:
        if any(re.search(pattern, normalized) for pattern in rule.patterns):
            return rule
    raise ValueError(
        "Question non reconnue. Consultez /intents pour voir les dix types de questions acceptés."
    )


QUESTION_WORDS = {
    "a",
    "au",
    "aux",
    "avec",
    "cette",
    "ce",
    "cet",
    "dans",
    "de",
    "des",
    "du",
    "elle",
    "en",
    "est",
    "etait",
    "il",
    "la",
    "le",
    "les",
    "lui",
    "ou",
    "par",
    "pour",
    "quand",
    "que",
    "quel",
    "quelle",
    "quelles",
    "quels",
    "qui",
    "sa",
    "ses",
    "son",
    "sont",
    "sur",
    "un",
    "une",
    "combien",
    "avoir",
    "avait",
    "age",
    "eu",
    "annee",
    "date",
    "naissance",
    "ne",
    "nee",
    "mort",
    "morte",
    "decede",
    "decedee",
    "lieu",
    "nationalite",
    "pays",
    "origine",
    "metier",
    "profession",
    "faisait",
    "travaillait",
    "etudes",
    "universite",
    "ecole",
    "etudie",
    "etudiee",
    "conjoint",
    "conjointe",
    "conjoints",
    "conjointes",
    "epoux",
    "epouse",
    "epouses",
    "mari",
    "maris",
    "marie",
    "mariee",
    "enfant",
    "enfants",
    "fils",
    "fille",
    "filles",
    "prix",
    "distinction",
    "distinctions",
    "recompense",
    "recompenses",
    "nobel",
    "fonction",
    "fonctions",
    "poste",
    "postes",
    "mandat",
    "president",
    "ministre",
    "recu",
    "recue",
    "recus",
    "recues",
    "occupe",
    "occupee",
    "occupes",
    "occupees",
    "presente-moi",
    "biographie",
    "parle-moi",
    "pere",
    "papa",
    "mere",
    "maman",
    "frere",
    "freres",
    "soeur",
    "soeurs",
    "fratrie",
    "employeur",
    "entreprise",
    "travaille",
    "habite",
    "residence",
    "vit",
    "actuellement",
    "religion",
    "religieux",
    "parti",
    "politique",
    "langue",
    "langues",
    "parle",
    "oeuvre",
    "oeuvres",
    "livre",
    "livres",
    "film",
    "films",
    "connu",
    "connue",
    "domaine",
    "specialite",
    "discipline",
    "genre",
    "musical",
    "artistique",
    "instrument",
    "instruments",
    "mesure",
    "taille",
    "cause",
    "quoi",
    "enterre",
    "enterree",
    "inhume",
    "inhumee",
    "tombe",
    "site",
    "web",
    "officiel",
    "officielle",
}


def extract_person_name(question: str) -> str:
    """Retire le vocabulaire de la question pour conserver le nom de la personne."""
    capitalized = re.findall(
        r"\b[A-ZÀ-ÖØ-Þ][\wÀ-ÿ'-]*(?:\s+(?:(?:de|du|des|da|van|von|le|la)\s+)?"
        r"[A-ZÀ-ÖØ-Þ][\wÀ-ÿ'-]*)*",
        question,
    )
    capitalized = [item for item in capitalized if normalize(item.split()[0]) not in QUESTION_WORDS]
    if capitalized:
        return max(capitalized, key=lambda item: (len(item.split()), len(item)))
    words = re.findall(r"[\wÀ-ÿ'-]+", question, flags=re.UNICODE)
    name_words = [
        word for word in words if normalize(word) not in QUESTION_WORDS or word == "Marie"
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


def extract_property_query(question: str, person_name: str) -> str:
    without_name = re.sub(re.escape(person_name), " ", question, flags=re.IGNORECASE)
    words = re.findall(r"[\wÀ-ÿ'-]+", without_name, flags=re.UNICODE)
    useful = [word for word in words if normalize(word) not in QUESTION_WORDS]
    query = " ".join(useful).strip(" '-")
    if not query:
        raise ValueError("La propriété recherchée n'est pas identifiable dans la question.")
    return query
