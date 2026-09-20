from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.intents import (
    RULES,
    IntentRule,
    asks_for_count,
    detect_intent,
    extract_person_name,
    normalize,
)
from app.models import Action, Intent


@dataclass(frozen=True)
class QuestionPlan:
    question: str
    action: Action
    person_names: list[str] = field(default_factory=list)
    rule: IntentRule | None = None
    confidence: float = 1.0


AGE_PATTERNS = (
    r"\bquel age\b",
    r"\bquelle age\b",
    r"\bage de\b",
    r"\bage avait\b",
    r"\bage aurait\b",
)
LIFESPAN_PATTERNS = (r"combien de temps.{0,80}vecu", r"duree de vie", r"vecu combien")
DURATION_PATTERNS = (r"\bcombien de temps\b", r"\bpendant combien")
COMPARE_PATTERNS = (
    r"\bentre\b",
    r"\bplus age\b",
    r"\bplus jeune\b",
    r"\bplus de\b",
    r"\bmeme\b",
    r"\bcompare",
)
VERIFY_PATTERNS = (
    r"\best-il\b",
    r"\best-elle\b",
    r"\betait-il\b",
    r"\betait-elle\b",
    r"\ba-t-il\b",
    r"\ba-t-elle\b",
)
DEMONYMS = (
    "algerien",
    "allemand",
    "americain",
    "australien",
    "britannique",
    "canadien",
    "espagnol",
    "francais",
    "italien",
    "polonais",
)


def extract_person_names(question: str) -> list[str]:
    if re.match(r"^\s*(?:et|sinon|aussi|donc|alors)\b", normalize(question)):
        return []
    candidates = re.findall(
        r"\b[A-ZÀ-ÖØ-Þ][\wÀ-ÿ'-]*(?:\s+(?:(?:de|du|des|da|van|von|le|la)\s+)?"
        r"[A-ZÀ-ÖØ-Þ][\wÀ-ÿ'-]*)*",
        question,
    )
    ignored = {
        "avec",
        "combien",
        "compare",
        "dans",
        "entre",
        "elle",
        "elles",
        "il",
        "ils",
        "lui",
        "eux",
        "leur",
        "leurs",
        "ou",
        "quand",
        "quel",
        "quelle",
        "quelles",
        "quels",
        "qui",
    }
    names: list[str] = []
    for item in candidates:
        words = item.split()
        if normalize(words[0]) in ignored:
            words = words[1:]
        if words:
            names.append(" ".join(words))
    unique = list(dict.fromkeys(names))
    if unique:
        return unique
    normalized = normalize(question)
    refers_to_context = re.search(
        r"\b(?:il|elle|ils|elles|eux|lui|leur|leurs|son|sa|ses)\b|"
        r"\b(?:est|etait|a)(?:-t)?-(?:il|elle)\b",
        normalized,
    )
    if refers_to_context:
        return []
    try:
        return [extract_person_name(question)]
    except ValueError:
        return []


def analyze_question(question: str, has_context: bool = False) -> QuestionPlan:
    normalized = normalize(question)
    names = extract_person_names(question)
    if not names and has_context:
        names = ["__context__"]

    if any(re.search(pattern, normalized) for pattern in LIFESPAN_PATTERNS):
        return QuestionPlan(question, Action.DURATION, names, confidence=0.98)
    if any(re.search(pattern, normalized) for pattern in AGE_PATTERNS):
        action = (
            Action.COMPARE
            if len(names) >= 2 or any(re.search(p, normalized) for p in COMPARE_PATTERNS)
            else Action.AGE
        )
        return QuestionPlan(question, action, names, confidence=0.98)

    try:
        rule = detect_intent(question)
    except ValueError:
        rule = None

    if rule is None and any(word in normalized for word in DEMONYMS):
        rule = next(item for item in RULES if item.property_id == "P27")

    if "plus age" in normalized or "plus jeune" in normalized:
        rule = next(item for item in RULES if item.property_id == "P569")

    if any(re.search(pattern, normalized) for pattern in DURATION_PATTERNS):
        return QuestionPlan(question, Action.DURATION, names, rule, 0.9)

    if len(names) >= 2 and any(re.search(p, normalized) for p in COMPARE_PATTERNS):
        return QuestionPlan(question, Action.COMPARE, names, rule, 0.92)
    if rule and rule.intent is Intent.SUMMARY:
        return QuestionPlan(question, Action.SUMMARY, names, rule, 0.99)
    if asks_for_count(question):
        return QuestionPlan(question, Action.COUNT, names, rule, 0.97)
    if any(re.search(pattern, normalized) for pattern in VERIFY_PATTERNS):
        return QuestionPlan(question, Action.VERIFY, names, rule, 0.82)
    return QuestionPlan(question, Action.LOOKUP, names, rule, 0.9 if rule else 0.72)
