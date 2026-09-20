from enum import StrEnum

from pydantic import BaseModel, Field


class Intent(StrEnum):
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


class Person(BaseModel):
    qid: str
    name: str
    description: str


class QuestionRequest(BaseModel):
    person_qid: str = Field(pattern=r"^Q\d+$", examples=["Q7186"])
    question: str = Field(min_length=3, max_length=300)


class Evidence(BaseModel):
    property_id: str
    property_label: str
    values: list[str]
    source_url: str


class AnswerResponse(BaseModel):
    person: Person
    question: str
    intent: Intent
    answer: str
    evidence: Evidence


class ErrorResponse(BaseModel):
    detail: str
