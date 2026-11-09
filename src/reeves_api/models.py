"""Public request and response models for the Reeves API prototype."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Language = Literal["auto", "uk", "ru"]
ResolvedLanguage = Literal["uk", "ru"]


class ChatTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4_000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4_000)
    language: Language = "auto"
    history: list[ChatTurn] = Field(default_factory=list, max_length=12)


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    url: str
    status: Literal["PROPOSED", "VALIDATED", "ACCEPTED"]


class GuardReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["argos"] = "argos"
    status: Literal["PASS"] = "PASS"
    checks: list[str]


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    reply: str
    language: ResolvedLanguage
    role: Literal["reeves"] = "reeves"
    provider: str
    validation_state: Literal["PROPOSED"] = "PROPOSED"
    memory_persisted: Literal[False] = False
    citations: list[Citation]
    guard: GuardReport
