"""Shared error codes for structured tool responses."""

from __future__ import annotations

APP_ERROR_CODES = {
    "operation_failed": "Generic failure for an application/window operation.",
    "not_found": "Target application or window could not be found.",
    "capability_missing": "The requested capability is not implemented or supported.",
    "verification_timeout": "The operation was sent, but verification did not succeed in time.",
}

APP_ERROR_OPERATION_FAILED = "operation_failed"
APP_ERROR_NOT_FOUND = "not_found"
APP_ERROR_CAPABILITY_MISSING = "capability_missing"
APP_ERROR_VERIFICATION_TIMEOUT = "verification_timeout"
