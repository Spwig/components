# Bug: Incorrect `timezone.utc` Usage

## Issue
Both `provider.py` and `subscription_provider.py` use `timezone.utc` where `timezone` is imported from `django.utils`. `django.utils.timezone` does NOT have a `.utc` attribute — this will raise an `AttributeError` at runtime when those code paths are hit.

## Affected Files

### `subscription_provider.py`
- **Import (line 8):** `from django.utils import timezone`
- **Buggy lines:** 218, 222, 226, 230, 270 — all use `tz=timezone.utc`

### `provider.py`
- **Import (line 15):** `from django.utils import timezone as django_timezone`
- **Buggy lines:** 2026, 2030, 2091, 2095 — all use `tz=django_timezone.utc`

## Fix
Add `from datetime import timezone as dt_timezone` and replace all `timezone.utc` / `django_timezone.utc` references with `dt_timezone.utc`.
