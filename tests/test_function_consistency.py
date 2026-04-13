"""Verify function definitions and implementations stay in sync."""

from saga.definitions import SAGA_FUNCTION_DEFINITIONS
from saga.functions import SAGA_FUNCTION_MAP, agent_filler
from common.agent_functions import HOTWORD_FUNCTION_MAP

# Functions handled specially in client.py (need websocket access)
WEBSOCKET_FUNCTIONS = {"agent_filler"}


def test_every_definition_has_implementation():
    """Every function defined in definitions.py must have an entry in SAGA_FUNCTION_MAP or be a websocket function."""
    definition_names = {d["name"] for d in SAGA_FUNCTION_DEFINITIONS}
    map_names = set(SAGA_FUNCTION_MAP.keys()) | WEBSOCKET_FUNCTIONS
    missing = definition_names - map_names
    assert not missing, f"Definitions without implementations: {missing}"


def test_websocket_functions_are_callable():
    """Websocket-handled functions must actually exist as importable callables."""
    assert callable(agent_filler)


def test_every_implementation_has_definition():
    """Every function in SAGA_FUNCTION_MAP should have a matching definition."""
    definition_names = {d["name"] for d in SAGA_FUNCTION_DEFINITIONS}
    map_names = set(SAGA_FUNCTION_MAP.keys())
    extra = map_names - definition_names
    assert not extra, f"Implementations without definitions: {extra}"


def test_hotword_functions_not_in_saga_map():
    """Hotword functions are separate and should not collide with SAGA functions."""
    overlap = set(HOTWORD_FUNCTION_MAP.keys()) & set(SAGA_FUNCTION_MAP.keys())
    assert not overlap, f"Hotword/SAGA function name collision: {overlap}"


def test_definition_names_are_unique():
    """No duplicate function names in definitions."""
    names = [d["name"] for d in SAGA_FUNCTION_DEFINITIONS]
    assert len(names) == len(set(names)), f"Duplicate names: {[n for n in names if names.count(n) > 1]}"
