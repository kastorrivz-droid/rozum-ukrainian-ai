"""Draft 2020-12 validation with format assertions enabled."""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .errors import ErrorCode, ProtocolViolation


def load_packaged_schema() -> dict[str, Any]:
    schema_resource = resources.files("rozum").joinpath(
        "resources/ROZUM_AI_v2.1.schema.json"
    )
    return json.loads(schema_resource.read_text(encoding="utf-8"))


class SchemaValidator:
    def __init__(self, schema: dict[str, Any] | None = None) -> None:
        self.schema = schema or load_packaged_schema()
        Draft202012Validator.check_schema(self.schema)
        self._validator = Draft202012Validator(
            self.schema,
            format_checker=FormatChecker(),
        )

    def validate(self, envelope: Any) -> None:
        errors = sorted(
            self._validator.iter_errors(envelope),
            key=lambda error: tuple(str(part) for part in error.absolute_path),
        )
        if not errors:
            return
        compact_errors = []
        for error in errors[:10]:
            path = "$"
            if error.absolute_path:
                path += "." + ".".join(str(part) for part in error.absolute_path)
            compact_errors.append({"path": path, "message": error.message})
        raise ProtocolViolation(
            ErrorCode.SCHEMA_INVALID,
            1,
            "Envelope does not satisfy the ROZUM_AI_v2.1 JSON Schema",
            details={"errors": compact_errors, "error_count": len(errors)},
        )
