"""Server-side allowlist of supported simulated remediation actions.

The allowlist is the security boundary of the remediation flow. The LLM may
only propose actions from this list, and only an explicit approval can cause an
action to be dispatched. There is no path from model output to execution
without a human decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.errors import InvalidParametersError, UnsupportedActionError


@dataclass(frozen=True)
class ActionSpec:
    """Definition of one allowlisted simulated action."""

    action: str
    risk_level: str
    description: str
    required_parameters: dict[str, str] = field(default_factory=dict)
    optional_parameters: dict[str, str] = field(default_factory=dict)

    def validate_parameters(self, parameters: dict[str, Any] | None) -> dict[str, Any]:
        """Validate and normalise the parameters for this action."""
        values = dict(parameters or {})

        allowed = set(self.required_parameters) | set(self.optional_parameters)
        unknown = sorted(set(values) - allowed)
        if unknown:
            raise InvalidParametersError(
                f"Unsupported parameter(s) for action '{self.action}': {', '.join(unknown)}",
                details={"action": self.action, "unsupported_parameters": unknown},
            )

        missing = sorted(set(self.required_parameters) - set(values))
        if missing:
            raise InvalidParametersError(
                f"Missing required parameter(s) for action '{self.action}': {', '.join(missing)}",
                details={"action": self.action, "missing_parameters": missing},
            )

        normalised: dict[str, Any] = {}
        for name, expected_type in {**self.required_parameters, **self.optional_parameters}.items():
            if name not in values:
                continue
            normalised[name] = self._coerce(name, values[name], expected_type)
        return normalised

    def _coerce(self, name: str, value: Any, expected_type: str) -> Any:
        if expected_type == "string":
            if not isinstance(value, str) or not value.strip():
                raise InvalidParametersError(
                    f"Parameter '{name}' of action '{self.action}' must be a non-empty string",
                    details={"action": self.action, "parameter": name},
                )
            return value.strip()
        if expected_type == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise InvalidParametersError(
                    f"Parameter '{name}' of action '{self.action}' must be an integer",
                    details={"action": self.action, "parameter": name},
                )
            if not 1 <= value <= 10:
                raise InvalidParametersError(
                    f"Parameter '{name}' of action '{self.action}' must be between 1 and 10",
                    details={"action": self.action, "parameter": name},
                )
            return value
        raise InvalidParametersError(
            f"Parameter '{name}' of action '{self.action}' has an unsupported type",
            details={"action": self.action, "parameter": name},
        )


ALLOWLIST: dict[str, ActionSpec] = {
    spec.action: spec
    for spec in (
        ActionSpec(
            action="rollback_demo_deployment",
            risk_level="medium",
            description="Roll the demo service back to its previous release.",
            optional_parameters={"version": "string"},
        ),
        ActionSpec(
            action="restart_demo_service",
            risk_level="medium",
            description="Restart the demo payment service.",
        ),
        ActionSpec(
            action="scale_demo_instances",
            risk_level="low",
            description="Change the number of demo service instances.",
            required_parameters={"instances": "integer"},
        ),
        ActionSpec(
            action="clear_demo_cache",
            risk_level="low",
            description="Clear cached entries in the demo service.",
        ),
    )
}

ALLOWED_ACTIONS: frozenset[str] = frozenset(ALLOWLIST)


def get_spec(action: str) -> ActionSpec:
    """Return the allowlist entry for an action or raise an error."""
    spec = ALLOWLIST.get(action)
    if spec is None:
        raise UnsupportedActionError(
            f"Action '{action}' is not on the remediation allowlist",
            details={"action": action, "allowed_actions": sorted(ALLOWED_ACTIONS)},
        )
    return spec


def is_allowed(action: str) -> bool:
    """Return True when the action is on the allowlist."""
    return action in ALLOWLIST
