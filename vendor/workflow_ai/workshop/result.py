"""Result-типы: явные возвраты вместо исключений в бизнес-логике.

Исключения допустимы только на границе с внешним миром (IO, сеть, docker)
и немедленно конвертируются в Err (см. <technology> в DevelopmentPlan.xml).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Ok[T]:
    value: T


@dataclass(frozen=True)
class Err:
    code: str
    details: str = ""


type Result[T] = Ok[T] | Err
