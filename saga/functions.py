"""SAGA function implementations. All return scripted mock data."""

from saga.mock_data import CITY_STATE, log_action


# ---------------------------------------------------------------------------
# Scenario 1: Command & Control
# ---------------------------------------------------------------------------

async def get_grid_status(params):
    """Return power grid status for a zone or all zones."""
    zone = params.get("zone", "").strip()
    zones = CITY_STATE["power_grid"]["zones"]

    if zone and zone in zones:
        z = zones[zone]
        log_action(f"Grid status queried: {zone}")
        return {
            "zone": zone,
            "load_mw": z["load_mw"],
            "capacity_mw": z["capacity_mw"],
            "utilization_pct": round(z["load_mw"] / z["capacity_mw"] * 100, 1),
            "status": z["status"],
        }

    # Return summary of all zones
    log_action("Full grid status overlay requested")
    summary = []
    for name, z in zones.items():
        summary.append({
            "zone": name,
            "load_mw": z["load_mw"],
            "capacity_mw": z["capacity_mw"],
            "utilization_pct": round(z["load_mw"] / z["capacity_mw"] * 100, 1),
            "status": z["status"],
        })
    return {
        "total_capacity_mw": CITY_STATE["power_grid"]["total_capacity_mw"],
        "current_load_mw": CITY_STATE["power_grid"]["current_load_mw"],
        "renewable_pct": CITY_STATE["power_grid"]["renewable_pct"],
        "zones": summary,
    }


async def analyze_energy_spike(params):
    """Analyze a spike in a specific zone and report autonomous mitigation."""
    zone = params.get("zone", "Smart BPO Sector")
    z = CITY_STATE["power_grid"]["zones"].get(zone, {})
    spike_pct = z.get("spike_pct", 0)
    cause = z.get("spike_cause", "Unknown demand increase")

    # Simulate autonomous mitigation
    solar_source = "Convention Center"
    diverted_mw = CITY_STATE["power_grid"]["zones"].get(solar_source, {}).get("solar_excess_mw", 5)

    log_action(f"Energy spike analyzed in {zone}: +{spike_pct}%, {diverted_mw}MW diverted from {solar_source}")
    z["status"] = "mitigated"

    return {
        "zone": zone,
        "spike_pct": spike_pct,
        "cause": cause,
        "mitigation": f"Diverted {diverted_mw}MW of excess solar storage from {solar_source} to stabilize load",
        "energy_arbitrage_margin": "+8%",
        "status": "stabilized",
    }


async def get_zone_overview(params):
    """General overview of a named zone."""
    zone = params.get("zone", "Phase 1 Core")
    z = CITY_STATE["power_grid"]["zones"].get(zone, {})
    log_action(f"Zone overview: {zone}")
    return {
        "zone": zone,
        "power_load_mw": z.get("load_mw", 0),
        "power_capacity_mw": z.get("capacity_mw", 0),
        "status": z.get("status", "normal"),
        "transit_pods_nearby": 24,
        "active_residents": 3_200,
        "air_quality_index": 42,
    }


# ---------------------------------------------------------------------------
# Scenario 2: Frictionless Resident
# ---------------------------------------------------------------------------

async def book_pod(params):
    """Book an autonomous pod to a destination."""
    destination = params.get("destination", "Office 800 Hub")
    pods = CITY_STATE["transit"]["autonomous_pods"]

    pod_number = 402
    pods["available"] -= 1
    pods["in_use"] += 1

    log_action(f"Pod #{pod_number} booked to {destination}")
    return {
        "pod_number": pod_number,
        "destination": destination,
        "eta_minutes": 1.5,
        "pickup": "Outside your door now",
        "status": "en_route",
    }


async def order_coffee(params):
    """Order a coffee and pay via Face-ID."""
    drink = params.get("drink", "flat white")
    location = params.get("location", "lobby cafe")

    log_action(f"Coffee ordered: {drink} at {location}, paid via Face-ID")
    return {
        "drink": drink,
        "location": location,
        "payment_method": "Face-ID",
        "ready_in_minutes": 4,
        "status": "confirmed",
    }


async def set_climate(params):
    """Set HVAC temperature for a location."""
    temperature = params.get("temperature", 22)
    location = params.get("location", "office")

    resident = CITY_STATE["resident"]
    old_temp = resident["climate"]["target_temp_c"]
    resident["climate"]["target_temp_c"] = temperature

    # Calculate energy cost offset
    log_action(f"Climate set: {location} to {temperature}C (was {old_temp}C)")
    return {
        "location": location,
        "target_temp_c": temperature,
        "eta_minutes": 3,
        "energy_cost_offset": f"Being offset by smart-shading credit (${resident['smart_shading_credit']:.2f})",
        "status": "HVAC active",
    }


async def check_energy_credits(params):
    """Check the resident's energy credit balance."""
    resident = CITY_STATE["resident"]
    log_action("Energy credits checked")
    return {
        "total_credits_usd": resident["energy_credits"],
        "smart_shading_credit_usd": resident["smart_shading_credit"],
        "solar_contribution_kwh": 342,
        "net_zero_progress_pct": 87,
    }


# ---------------------------------------------------------------------------
# Scenario 3: Power User / Smart Work
# ---------------------------------------------------------------------------

async def analyze_revenue(params):
    """Analyze revenue from a city source."""
    source = params.get("source", "Smart Grid")
    period = params.get("period", "last month")

    rev = CITY_STATE["revenue"]
    log_action(f"Revenue analysis: {source}, {period}")
    return {
        "source": source,
        "period": period,
        "revenue_usd": rev["smart_grid_monthly_usd"],
        "formatted": "$1.84 billion",
        "yoy_growth_pct": rev["yoy_growth_pct"],
        "tenant_density": rev["tenant_density"],
    }


async def create_projection(params):
    """Create a financial projection."""
    years = params.get("years", 10)
    tenant_increase_pct = params.get("tenant_increase_pct", 20)

    target_year = 2026 + years
    rev = CITY_STATE["revenue"]
    rev["projected_2035_usd"] = 22_400_000_000

    log_action(f"{years}-year projection created: +{tenant_increase_pct}% tenant density")
    return {
        "projection_years": years,
        "target_year": target_year,
        "tenant_density_increase_pct": tenant_increase_pct,
        "projected_revenue_usd": 22_400_000_000,
        "formatted": "$22.4 billion",
        "model": "compound growth with density adjustment",
    }


async def generate_deck(params):
    """Generate a presentation deck."""
    format_for = params.get("format", "Board review")
    brand_kit = params.get("brand_kit", "Harbour City")

    log_action(f"Presentation deck generated: {format_for}, {brand_kit} brand kit")
    return {
        "status": "generated",
        "format": format_for,
        "brand_kit": brand_kit,
        "slides": 14,
        "platform": "Canva",
        "link": "https://saga.city/decks/board-review-2036",
    }


async def send_notification(params):
    """Send a notification to a recipient."""
    recipient = params.get("recipient", "Donny")
    content = params.get("content", "Board review deck ready")
    priority = params.get("priority", "high")

    log_action(f"Notification sent to {recipient}: {content} (priority: {priority})")
    return {
        "recipient": recipient,
        "method": "SAGA wearable + email",
        "content": content,
        "priority": priority,
        "status": "delivered",
    }


# ---------------------------------------------------------------------------
# Scenario 4: Proactive Guardian
# ---------------------------------------------------------------------------

async def get_weather_alert(params):
    """Get current weather alerts."""
    alerts = CITY_STATE["weather"]["alerts"]
    log_action("Weather alerts checked")
    if alerts:
        return {
            "alert_count": len(alerts),
            "alerts": alerts,
        }
    return {"alert_count": 0, "message": "No active weather alerts"}


async def activate_flood_gates(params):
    """Activate the smart flood gates."""
    close_time = params.get("close_time", "9:00 PM")
    CITY_STATE["flood_gates"]["status"] = "scheduled"
    CITY_STATE["flood_gates"]["scheduled_close"] = close_time

    log_action(f"Flood gates scheduled to close at {close_time}")
    return {
        "status": "scheduled",
        "close_time": close_time,
        "gates_affected": 12,
        "bay_coverage": "Full Manila Bay seawall",
    }


async def send_mass_alert(params):
    """Send a mass alert to all residents."""
    message = params.get("message", "Storm surge advisory")
    zones = params.get("zones", "all low-level zones")
    residents_count = 800_000

    CITY_STATE["emergency"]["resident_alert_count"] = residents_count
    log_action(f"Mass alert sent to {residents_count:,} residents: {message}")
    return {
        "status": "sent",
        "recipients": residents_count,
        "formatted_recipients": "800,000",
        "method": "Super App push notification",
        "message": message,
        "zones": zones,
        "alert_type": "Safe-Home Advisory",
    }


async def check_backup_power(params):
    """Check emergency backup power status."""
    facility = params.get("facility", "Data Center")
    emergency = CITY_STATE["emergency"]

    log_action(f"Backup power checked: {facility}")
    return {
        "facility": facility,
        "backup_power_pct": emergency["backup_power_pct"],
        "status": emergency["data_center_status"],
        "fuel_reserves_hours": 72,
        "auto_switch_ready": True,
    }


async def book_emergency_accommodation(params):
    """Book discounted emergency accommodation for affected residents."""
    zone = params.get("zone", "low-level zones")
    discount_pct = params.get("discount_pct", 10)

    log_action(f"Emergency accommodation: {discount_pct}% discount for {zone}")
    return {
        "status": "confirmed",
        "partner": "Convention Center Hotels",
        "zone": zone,
        "discount_pct": discount_pct,
        "rooms_available": 2_400,
        "booking_method": "Auto-booked via Super App for residents in affected zones",
    }


# ---------------------------------------------------------------------------
# Agent filler (requires websocket, handled specially in client.py)
# ---------------------------------------------------------------------------

FILLER_MESSAGES = {
    "lookup": "One moment, sir.",
    "processing": "Processing.",
    "analyzing": "Analyzing now.",
    "general": "One moment.",
}


async def agent_filler(websocket, params):
    """Immediately speak a filler phrase via InjectAgentMessage while LLM thinks."""
    message_type = params.get("message_type", "general")
    filler_text = FILLER_MESSAGES.get(message_type, FILLER_MESSAGES["general"])

    inject_message = {
        "type": "InjectAgentMessage",
        "message": filler_text,
    }

    return {
        "inject_message": inject_message,
        "function_response": {"status": "queued", "message_type": message_type},
    }


# ---------------------------------------------------------------------------
# Function map
# ---------------------------------------------------------------------------

SAGA_FUNCTION_MAP = {
    # Scenario 1
    "get_grid_status": get_grid_status,
    "analyze_energy_spike": analyze_energy_spike,
    "get_zone_overview": get_zone_overview,
    # Scenario 2
    "book_pod": book_pod,
    "order_coffee": order_coffee,
    "set_climate": set_climate,
    "check_energy_credits": check_energy_credits,
    # Scenario 3
    "analyze_revenue": analyze_revenue,
    "create_projection": create_projection,
    "generate_deck": generate_deck,
    "send_notification": send_notification,
    # Scenario 4
    "get_weather_alert": get_weather_alert,
    "activate_flood_gates": activate_flood_gates,
    "send_mass_alert": send_mass_alert,
    "check_backup_power": check_backup_power,
    "book_emergency_accommodation": book_emergency_accommodation,
}
