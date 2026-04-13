"""Mock city state for the SAGA Smart City demo.

The state is a mutable singleton dict that functions update as they're called.
The frontend polls /api/city-state to render the sidebar dashboard.
"""

import copy
from datetime import datetime

_INITIAL_STATE = {
    "power_grid": {
        "total_capacity_mw": 850,
        "current_load_mw": 612,
        "renewable_pct": 78,
        "zones": {
            "Phase 1 Core": {
                "load_mw": 180,
                "capacity_mw": 250,
                "status": "normal",
            },
            "Smart BPO Sector": {
                "load_mw": 145,
                "capacity_mw": 150,
                "status": "elevated",
                "spike_pct": 15,
                "spike_cause": "Three new AI firms onboarded 5,000 agents",
            },
            "Convention Center": {
                "load_mw": 92,
                "capacity_mw": 200,
                "status": "normal",
                "solar_excess_mw": 5,
            },
            "Residential North": {
                "load_mw": 105,
                "capacity_mw": 150,
                "status": "normal",
            },
            "Marina District": {
                "load_mw": 90,
                "capacity_mw": 100,
                "status": "normal",
            },
        },
    },
    "transit": {
        "autonomous_pods": {
            "available": 342,
            "in_use": 158,
            "avg_wait_min": 2.3,
        },
        "metro": {
            "status": "on_time",
            "next_arrival_min": 4,
        },
    },
    "weather": {
        "current": {
            "temp_c": 31,
            "humidity_pct": 72,
            "condition": "Partly Cloudy",
            "wind_kph": 18,
        },
        "alerts": [
            {
                "id": "WX-2026-0413",
                "type": "Storm Surge",
                "severity": "high",
                "eta_hours": 8,
                "surge_meters": 2.0,
                "location": "Manila Bay",
                "predicted_time": "11:00 PM tonight",
            }
        ],
    },
    "resident": {
        "name": "Mr. Donovan",
        "unit": "Tower A, Unit 4201",
        "climate": {"current_temp_c": 24, "target_temp_c": 24},
        "energy_credits": 847.50,
        "smart_shading_credit": 12.30,
        "face_id_payment": True,
    },
    "revenue": {
        "smart_grid_monthly_usd": 1_840_000_000,
        "tenant_density": 12_400,
        "yoy_growth_pct": 14.2,
        "projected_2035_usd": 18_700_000_000,
    },
    "flood_gates": {
        "status": "open",
        "scheduled_close": None,
    },
    "emergency": {
        "backup_power_pct": 100,
        "data_center_status": "nominal",
        "resident_alert_count": 0,
    },
    "recent_actions": [],
}


CITY_STATE: dict = copy.deepcopy(_INITIAL_STATE)


def reset_city_state() -> dict:
    """Reset to initial state. Returns the fresh state."""
    global CITY_STATE
    CITY_STATE = copy.deepcopy(_INITIAL_STATE)
    return CITY_STATE


def log_action(action: str) -> None:
    """Append a timestamped action to the recent_actions list (max 20)."""
    CITY_STATE["recent_actions"].insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "action": action,
    })
    CITY_STATE["recent_actions"] = CITY_STATE["recent_actions"][:20]


def get_city_state() -> dict:
    """Return a copy of current city state for the API."""
    return copy.deepcopy(CITY_STATE)
