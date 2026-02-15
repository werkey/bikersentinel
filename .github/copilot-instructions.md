<!-- Copilot instructions for working on the BikerSentinel Home Assistant integration -->
# BikerSentinel — AI Coding Assistant Guide

Purpose: help AI agents quickly become productive in this repository by summarizing architecture, conventions, and common developer workflows.

1) Big picture
- This is a Home Assistant `custom_component` named `bikersentinel` (see `manifest.json`).
- Core runtime: Home Assistant loads the integration via `__init__.py` which forwards to the `sensor` platform.
- Primary outputs: two sensors — a numeric `score` sensor and an enumerated `status` sensor (see `bikersentinel/sensor.py`).

2) Key files & responsibilities
- `bikersentinel/__init__.py` — integration bootstrap; declares `PLATFORMS = [Platform.SENSOR]` and forwards config entries.
- `bikersentinel/config_flow.py` — UI-driven configuration using Home Assistant selectors and `voluptuous` schema. The created config entry stores sensor entity IDs and user options.
- `bikersentinel/sensor.py` — main logic: reads configured sensor entity ids from the config entry (`entry.data[...]`), computes the Biker Score algorithm, and exposes the status entity.
- `bikersentinel/const.py` — all configuration keys, defaults, and coefficient tables. NOTE: config keys are in French (e.g. `CONF_HEIGHT = "taille"`).
- `translations/` — localizations for entity names/strings. Update these when adding new translation keys.

3) Data flow & integration points (how components talk)
- During setup, `async_setup_entry` reads `entry.data` values: temperature/wind/rain entity ids, optional weather entity, and user options (height, weight, bike type, equipment).
- `BikerSentinelScore.native_value` uses `hass.states.get(entity_id)` to read sensor values live and compute the score. It logs errors with `_LOGGER`.
- `BikerSentinelStatus` looks up the score entity in the entity registry with `hass.helpers.entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)` and maps numeric score to categories.

4) Important implementation patterns & conventions
- Config keys use French identifiers (see `const.py`) — read/write using those keys when manipulating `entry.data`.
- Defaults: `async_setup_entry` intentionally falls back to `DEFAULT_*` when `entry.data` values are None/empty.
- Unique IDs: sensors use `f"{entry.entry_id}_score"` and `..._status"`. Use this pattern when adding entities.
- Error handling: sensor calculations catch Exception and log with `_LOGGER.error(...)` and return `None` to keep HA stable.
- Translation keys: sensors set `_attr_translation_key = "score"` / `"status"` — add matching keys in `translations/*.json`.

5) Developer workflows (how to build, run and debug)
- Install locally for Home Assistant: copy the `bikersentinel` folder into `/config/custom_components/bikersentinel` and restart HA (as described in `README.md`).
- Add the integration via the Home Assistant UI (config flow uses selectors for sensor entity selection).
- Debugging: enable logging for the integration name (`bikersentinel`) in Home Assistant logger to surface `_LOGGER` messages from `sensor.py` and `config_flow.py`.

6) What to change and where (examples)
- To add a new coefficient or bike type: update `MACHINE_TYPES` and `PROTECTION_COEFS` in `bikersentinel/const.py`, then update `config_flow.py` defaults and `translations` if needed.
- To change the safety veto list or scoring formula: modify the checks and math in `BikerSentinelScore.native_value` in `bikersentinel/sensor.py` — preserve the early-return veto style (immediate 0.0 on severe conditions).

7) Tests & CI
- This repository does not include automated tests. Before adding CI, follow the local dev workflow (install to `custom_components`, test inside HA instance) and keep changes minimal and well-logged.

8) Minimal rules for AI edits
- Preserve config keys in `const.py` (French keys) and translation keys in `translations/*` when renaming fields.
- Keep `async` functions and Home Assistant patterns (`async_setup_entry`, `async_forward_entry_setups`) intact.
- When adding entities keep unique_id naming consistent (`{entry.entry_id}_score` / `_status`).

If any section is unclear or you want the file to include additional examples (unit test harness, logger config snippet, or more translation guidance), say which area to expand.
