"""Provider boundary for the Reeves dialogue service.

The deterministic mock remains the default. An optional OpenAI Responses
adapter runs only on the server and preserves the public request contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import ChatRequest, Citation, ResolvedLanguage


REPOSITORY_SOURCE = (
    "https://github.com/kastorrivz-droid/rozum-ukrainian-ai/blob/main/"
)


@dataclass(frozen=True, slots=True)
class ProviderReply:
    text: str
    citations: tuple[Citation, ...]


class ProviderUnavailable(RuntimeError):
    """Raised when an external dialogue provider cannot return a valid answer."""


class ChatProvider(Protocol):
    name: str

    async def generate(
        self,
        request: ChatRequest,
        language: ResolvedLanguage,
    ) -> ProviderReply: ...


def detect_language(request: ChatRequest) -> ResolvedLanguage:
    if request.language in {"uk", "ru"}:
        return request.language

    lowered = request.message.lower()
    if any(letter in lowered for letter in "іїєґ"):
        return "uk"
    if any(letter in lowered for letter in "ыэъё"):
        return "ru"
    return "uk"


class MockProvider:
    """Safe local provider used to validate the transport and UI integration."""

    name = "mock"

    async def generate(
        self,
        request: ChatRequest,
        language: ResolvedLanguage,
    ) -> ProviderReply:
        lowered = request.message.lower()

        if "argos" in lowered or "аргос" in lowered:
            source = Citation(
                title="05_ARGOS.md",
                url=f"{REPOSITORY_SOURCE}05_ARGOS.md",
                status="VALIDATED",
            )
            text = {
                "uk": (
                    "Argos — шар перевірки та оркестрації ROZUM. Він контролює "
                    "обов’язкові стадії, фіксує походження результату й не дозволяє "
                    "неперевіреній гіпотезі непомітно стати рішенням."
                ),
                "ru": (
                    "Argos — слой проверки и оркестрации ROZUM. Он контролирует "
                    "обязательные стадии, фиксирует происхождение результата и не "
                    "позволяет непроверенной гипотезе незаметно стать решением."
                ),
            }[language]
        elif "andromeda" in lowered or "андромед" in lowered:
            source = Citation(
                title="07_ANDROMEDA.md",
                url=f"{REPOSITORY_SOURCE}07_ANDROMEDA.md",
                status="PROPOSED",
            )
            text = {
                "uk": (
                    "Andromeda — запропонована архітектурна роль: вона показує "
                    "залежності, припущення, ризики та варіанти. Вона не затверджує "
                    "зміни й не підмінює рішення Human Architect."
                ),
                "ru": (
                    "Andromeda — предлагаемая архитектурная роль: она показывает "
                    "зависимости, допущения, риски и варианты. Она не утверждает "
                    "изменения и не подменяет решение Human Architect."
                ),
            }[language]
        elif "reeves" in lowered or "ривз" in lowered or "рівз" in lowered:
            source = Citation(
                title="06_REEVES.md",
                url=f"{REPOSITORY_SOURCE}06_REEVES.md",
                status="PROPOSED",
            )
            text = {
                "uk": (
                    "Ривз — діалоговий інтерфейс ROZUM: він допомагає перетворити "
                    "вільну думку на ясний запит, пояснює результат і відокремлює "
                    "факт від припущення. Його впевнений тон не є доказом."
                ),
                "ru": (
                    "Ривз — диалоговый интерфейс ROZUM: он помогает превратить "
                    "свободную мысль в ясный запрос, объясняет результат и отделяет "
                    "факт от предположения. Его уверенный тон не является доказательством."
                ),
            }[language]
        else:
            source = Citation(
                title="01_ROZUM_VISION.md",
                url=f"{REPOSITORY_SOURCE}01_ROZUM_VISION.md",
                status="ACCEPTED",
            )
            text = {
                "uk": (
                    "Серверний маршрут працює в безпечному mock-режимі: запит пройшов "
                    "контракт, ліміти й Argos-перевірку, але зовнішня мовна модель ще "
                    "не викликалась. Наступний крок — підключити дозволений провайдер "
                    "за цим самим серверним контрактом."
                ),
                "ru": (
                    "Серверный маршрут работает в безопасном mock-режиме: запрос прошёл "
                    "контракт, лимиты и Argos-проверку, но внешняя языковая модель ещё "
                    "не вызывалась. Следующий шаг — подключить разрешённого провайдера "
                    "через этот же серверный контракт."
                ),
            }[language]

        return ProviderReply(text=text, citations=(source,))


def load_provider(name: str) -> ChatProvider:
    normalized = name.strip().lower()
    if normalized == "mock":
        return MockProvider()
    if normalized == "openai":
        from .openai_provider import OpenAIResponsesProvider

        return OpenAIResponsesProvider.from_environment()
    raise RuntimeError(
        f"Unsupported REEVES_PROVIDER={name!r}; this prototype fails closed."
    )
