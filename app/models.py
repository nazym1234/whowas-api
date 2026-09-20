from enum import StrEnum

from pydantic import BaseModel, Field


class Intent(StrEnum):
    SUMMARY = "summary"
    BIRTH_DATE = "birth_date"
    BIRTH_PLACE = "birth_place"
    DEATH_DATE = "death_date"
    NATIONALITY = "nationality"
    OCCUPATION = "occupation"
    EDUCATION = "education"
    SPOUSE = "spouse"
    CHILDREN = "children"
    AWARDS = "awards"
    POSITION = "position"
    FAMILY = "family"
    EMPLOYER = "employer"
    RESIDENCE = "residence"
    RELIGION = "religion"
    POLITICAL_PARTY = "political_party"
    LANGUAGES = "languages"
    NOTABLE_WORK = "notable_work"
    FIELD = "field"
    GENRE = "genre"
    INSTRUMENT = "instrument"
    HEIGHT = "height"
    CAUSE_OF_DEATH = "cause_of_death"
    BURIAL_PLACE = "burial_place"
    WEBSITE = "website"
    GENERIC = "generic"
    AGE = "age"
    LIFESPAN = "lifespan"
    COMPARISON = "comparison"
    VERIFICATION = "verification"


class Action(StrEnum):
    LOOKUP = "lookup"
    COUNT = "count"
    SUMMARY = "summary"
    AGE = "age"
    DURATION = "duration"
    COMPARE = "compare"
    VERIFY = "verify"


class Person(BaseModel):
    qid: str
    name: str
    description: str
    image_url: str | None = None


class PersonCandidate(BaseModel):
    qid: str
    name: str
    description: str = ""
    score: float = 0.0


class QuestionRequest(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=300,
        examples=["Où est née Marie Curie ?"],
    )
    person_qid: str | None = Field(default=None, pattern=r"^Q\d+$")
    context_qid: str | None = Field(default=None, pattern=r"^Q\d+$")


class Evidence(BaseModel):
    property_id: str
    property_label: str
    values: list[str]
    source_url: str
    resolution: str = "rule"
    confidence: float = 1.0
    retrieved_at: str | None = None
    details: list["EvidenceDetail"] = Field(default_factory=list)


class EvidenceDetail(BaseModel):
    value: str
    statement_id: str | None = None
    rank: str = "normal"
    start_date: str | None = None
    end_date: str | None = None


class AnswerResponse(BaseModel):
    person: Person
    question: str
    intent: Intent
    answer: str
    evidence: Evidence
    action: Action = Action.LOOKUP
    related_people: list[Person] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    detail: str


class AkinatorAnswerRequest(BaseModel):
    session_id: str = Field(min_length=36, max_length=36)
    answer: str = Field(pattern=r"^(yes|no|unknown)$")
