from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


ROLES = Literal["Backend", "Frontend", "Full-Stack", "Data", "DevOps", "QA"]


class RepoContext(BaseModel):
    repo_url: str
    default_branch: str | None = None
    languages: list[str] = Field(default_factory=list)
    file_count: int = Field(default=0, ge=0)


class Evidence(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    start: int = Field(ge=1)
    end: int = Field(ge=1)
    note: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def valid_range(self):
        if self.end < self.start:
            raise ValueError("evidence end must be >= start")
        return self


class AgentFinding(BaseModel):
    agent: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=10000)
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class TourStep(BaseModel):
    step: int = Field(ge=1, le=8)
    title: str = Field(min_length=1, max_length=200)
    path: str = Field(min_length=1, max_length=500)
    start: int = Field(ge=1)
    end: int = Field(ge=1)
    narration: str = Field(min_length=1, max_length=3000)

    @model_validator(mode="after")
    def valid_range(self):
        if self.end < self.start:
            raise ValueError("tour step end must be >= start")
        return self


class ArchitectureSummary(BaseModel):
    overview: str
    modules: list[str] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    data_flow: str = ""


class OnboardingPlan(BaseModel):
    role: str
    tour_steps: list[TourStep] = Field(min_length=8, max_length=8)
    architecture_summary: ArchitectureSummary | str
    key_concepts: list[str] = Field(default_factory=list)
    repo_context: RepoContext | None = None
    generated_at: str | None = None

    @field_validator("tour_steps")
    @classmethod
    def ordered_eight(cls, value: list[TourStep]) -> list[TourStep]:
        expected = list(range(1, 9))
        actual = [step.step for step in value]
        if actual != expected:
            raise ValueError("tour_steps must contain steps 1 through 8 in order")
        return value


class RepoCreateRequest(BaseModel):
    repo_url: str = Field(min_length=1, max_length=500)
    role: ROLES = "Full-Stack"


class RepoCreateResponse(BaseModel):
    job_id: str
    status: str


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class Citation(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    start: int = Field(ge=1)
    end: int = Field(ge=1)

    @model_validator(mode="after")
    def valid_range(self):
        if self.end < self.start:
            raise ValueError("citation end must be >= start")
        return self


class QAResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)


class SourceResponse(BaseModel):
    path: str
    start: int
    end: int
    content: str


class JobState(BaseModel):
    job_id: str
    repo_url: str
    role: str
    status: str = "queued"
    progress: int = Field(default=0, ge=0, le=100)
    node: str | None = None
    latest_message: str = "Queued"
    agents: dict[str, dict[str, Any]] = Field(default_factory=dict)
    repo_context: RepoContext | None = None
    plan: OnboardingPlan | None = None
    repo_path: str | None = None
    error: str | None = None
