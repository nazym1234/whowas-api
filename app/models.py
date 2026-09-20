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


class Person(BaseModel):
    qid: str
    name: str
    description: str


class QuestionRequest(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=300,
        examples=["Où est née Marie Curie ?"],
    )


class Evidence(BaseModel):
    property_id: str
    property_label: str
    values: list[str]
    source_url: str
    resolution: str = "rule"


class AnswerResponse(BaseModel):
    person: Person
    question: str
    intent: Intent
    answer: str
    evidence: Evidence


class ErrorResponse(BaseModel):
    detail: str
