"""SAGA function implementations. All return scripted mock data."""

import json

from saga.mock_data import CITY_STATE, MANAGEMENT_STAKEHOLDERS_CSV, log_action


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

REVENUE_HISTORY = {
    "last month": {"revenue_usd": 1_840_000_000, "formatted": "$1.84 billion", "tenant_density": 12_400},
    "previous month": {"revenue_usd": 1_710_000_000, "formatted": "$1.71 billion", "tenant_density": 12_100},
    "two months ago": {"revenue_usd": 1_580_000_000, "formatted": "$1.58 billion", "tenant_density": 11_800},
    "three months ago": {"revenue_usd": 1_520_000_000, "formatted": "$1.52 billion", "tenant_density": 11_500},
    "q1 2026": {"revenue_usd": 5_130_000_000, "formatted": "$5.13 billion", "tenant_density": 12_100},
    "ytd": {"revenue_usd": 5_130_000_000, "formatted": "$5.13 billion", "tenant_density": 12_100},
}


async def analyze_revenue(params):
    """Analyze revenue from a city source."""
    source = params.get("source", "Smart Grid")
    period = params.get("period", "last month").lower()

    # Match period to historical data
    data = REVENUE_HISTORY.get(period, REVENUE_HISTORY["last month"])

    log_action(f"Revenue analysis: {source}, {period}")
    return {
        "source": source,
        "period": period,
        "revenue_usd": data["revenue_usd"],
        "formatted": data["formatted"],
        "tenant_density": data["tenant_density"],
        "yoy_growth_pct": 14.2,
        "mom_growth_pct": 7.6,
        "note": "Month-over-month growth driven by BPO sector expansion and Convention Center energy arbitrage",
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
        "link": "https://eve.city/decks/board-review-2036",
    }


async def send_notification(params):
    """Send a notification to a recipient."""
    recipient = params.get("recipient", "Donny")
    content = params.get("content", "Board review deck ready")
    priority = params.get("priority", "high")

    log_action(f"Notification sent to {recipient}: {content} (priority: {priority})")
    return {
        "recipient": recipient,
        "method": "Eve wearable + email",
        "content": content,
        "priority": priority,
        "status": "delivered",
    }


# ---------------------------------------------------------------------------
# Scenario 5: Board Prep (Executive Assistant)
# ---------------------------------------------------------------------------

async def draft_narrative(params):
    """Draft speaker notes / narrative for a presentation."""
    topic = params.get("topic", "Q1 financial results")
    audience = params.get("audience", "Board of Directors")

    talking_points = [
        "Open with the 7.6% month-over-month lift on Smart Grid revenue to $1.84B, framed as the BPO expansion dividend.",
        "Connect the 15% load spike in Smart BPO to the solar arbitrage save from Convention Center — margin held at +8%.",
        "Use the 14.2% YoY growth to anchor the ask: accelerate Phase 2 tidal capacity to protect 2035 target.",
        "Close on net-zero progress at 87% and the Harbour Bridge toll pilot extension through Q3 2026.",
        "Leave 5 minutes for Donny's capex ask — $220M for the tidal expansion, payback under 6 years.",
    ]

    log_action(f"Narrative drafted: {topic} for {audience}")
    return {
        "topic": topic,
        "audience": audience,
        "opening_hook": talking_points[0],
        "key_driver": talking_points[1],
        "growth_anchor": talking_points[2],
        "closing": talking_points[3],
        "ask_cue": talking_points[4],
        "tone": "confident, data-led, 12 minutes including Q&A",
    }


async def request_stakeholder_input(params):
    """Email stakeholders requesting inputs on a deliverable."""
    deliverable = params.get("deliverable", "Q1 board deck")
    recipients = params.get("recipients", MANAGEMENT_STAKEHOLDERS_CSV)
    deadline = params.get("deadline", "3:00 PM today")

    recipient_list = [r.strip() for r in recipients.split(",") if r.strip()]

    log_action(f"Stakeholder input requested from {len(recipient_list)} people: {deliverable}")
    return {
        "deliverable": deliverable,
        "recipients": recipient_list,
        "recipient_count": len(recipient_list),
        "deadline": deadline,
        "channel": "Email + Eve wearable nudge",
        "status": "sent",
    }


async def book_meeting_room(params):
    """Book a meeting room and send calendar invites."""
    room = params.get("room", "Tower A Boardroom")
    time = params.get("time", "4:00 PM today")
    attendees = params.get("attendees", "Board of Directors")
    purpose = params.get("purpose", "Q1 Board Review")

    log_action(f"Meeting room booked: {room} at {time}, invites sent to {attendees}")
    return {
        "room": room,
        "floor": "Tower A, Level 16",
        "capacity": 20,
        "time": time,
        "attendees": attendees,
        "attendee_count": 9,
        "purpose": purpose,
        "calendar_invites": "sent",
        "av_confirmed": "4K wall, Eve cast link ready",
        "status": "confirmed",
    }


async def order_catering(params):
    """Order catering for a group meeting, paid via Face-ID."""
    items = params.get("items", "espresso bar and pastries")
    headcount = params.get("headcount", 8)
    location = params.get("location", "Tower A Boardroom")

    per_head = 30
    total = round(headcount * per_head, 2)

    log_action(f"Catering ordered: {items} for {headcount} at {location}, ${total}")
    return {
        "items": items,
        "headcount": headcount,
        "location": location,
        "vendor": "Lobby Cafe + Phase 1 Patisserie",
        "total_usd": total,
        "formatted_total_usd": f"${total:.2f}",
        "payment_method": "Face-ID (charged to Tower A Unit 4201)",
        "ready_by": "15 minutes before meeting start",
        "status": "confirmed",
    }


async def render_chart(params):
    """Render a chart widget. LLM provides the chart type and data."""
    title = params.get("title", "Chart")
    chart_type = params.get("chart_type", "bar")
    labels = params.get("labels", []) or []
    values = params.get("values", []) or []
    unit = params.get("unit", "")
    color = params.get("color", "blue")

    if not isinstance(labels, list):
        labels = [str(labels)]
    if not isinstance(values, list):
        values = [values]

    log_action(f"Chart rendered: {title} ({chart_type}, {len(values)} points)")
    return {
        "title": title,
        "chart_type": chart_type,
        "labels": labels,
        "values": values,
        "unit": unit,
        "color": color,
    }


async def generate_slide_preview(params):
    """Return a 5-slide preview grid for a deck. LLM provides the slide content."""
    topic = params.get("topic", "Board Review")
    slides = params.get("slides", []) or []

    if not slides:
        slides = [
            {"title": "Q1 2026 Board Review", "hero_stat": "$5.13B", "caption": "Smart Grid revenue, +14.2% YoY"},
            {"title": "The BPO Dividend", "hero_stat": "+15%", "caption": "Load spike mitigated via Convention Center solar arbitrage"},
            {"title": "Energy Arbitrage", "hero_stat": "+8%", "caption": "Margin held through storage redistribution"},
            {"title": "Net-Zero Progress", "hero_stat": "87%", "caption": "On track for the 2040 target"},
            {"title": "Phase 2 Ask", "hero_stat": "$220M", "caption": "Tidal capex, 6-year payback, unlocks $22.4B by 2035"},
        ]

    log_action(f"Slide preview generated: {topic} ({len(slides)} slides)")
    return {
        "topic": topic,
        "slide_count": len(slides),
        "slides": slides,
    }


# ---------------------------------------------------------------------------
# Scenario 6: Tourist / Visitor Concierge
# ---------------------------------------------------------------------------

async def plan_day_itinerary(params):
    """Plan a weather-aware day itinerary for a Harbour City visitor."""
    guest_name = params.get("guest_name", "").strip()
    interests = params.get("interests", "food, walking, wellness, culture").strip()

    weather = CITY_STATE["weather"]["current"]
    weather_note = (
        f"{weather['condition']}, {weather['temp_c']}C, "
        f"winds {weather['wind_kph']} kph — good for outdoor stretches through mid-afternoon"
    )

    itinerary = {
        "08:00 - Breakfast": (
            "Sogo Harbour Hotel — 50% off guest rate on the Filipino breakfast; "
            "their longganisa (sweet garlic sausage) is the best on the island"
        ),
        "09:30 - Harbour walk": (
            "2.1 km seawall promenade from Sogo to the Marina District — walks off breakfast, ~2,800 steps"
        ),
        "11:00 - Wellness event": (
            "Convention Center is hosting ASEAN Wellness Expo today — breathwork workshop at 11:15, free entry on Super App"
        ),
        "13:00 - Lunch": (
            "Skyline 47 rooftop, Harbour City Tower — Manila Bay views, kare-kare set menu, ~PHP 1,450"
        ),
        "14:30 - Transfer": (
            "Classic jeepney ride from Marina Plaza to Harbour City Beach Club — 12 minutes, PHP 50, local color"
        ),
        "15:00 - Beach Club": (
            "Harbour City Beach Club — swim, cabana, lagoon pool, day pass covered by visitor Super App wristband"
        ),
        "18:30 - Sunset drinks": (
            "Jollibee Sky Deck, Phase 1 Core — yes, the Jollibee has a sunset rooftop bar; chickenjoy sliders + calamansi spritz"
        ),
        "20:00 - Dinner": (
            "Stay at Jollibee Sky Deck for the Filipino-fusion tasting menu; sunset hits Manila Bay at 19:47 tonight"
        ),
    }

    log_action(f"Day itinerary planned{' for ' + guest_name if guest_name else ''}")
    return {
        "guest": guest_name or "visitor",
        "weather_today": weather_note,
        "interests": interests,
        "total_stops": len(itinerary),
        "est_steps": "6,400",
        "est_cost_php": "4,200",
        **itinerary,
        "next_action": "Say 'book it' and I will confirm reservations, the jeepney pass, and the beach club wristband",
    }


async def book_itinerary(params):
    """Confirm bookings for all items in the most recent itinerary."""
    itinerary_id = params.get("itinerary_id", "current")

    log_action(f"Itinerary bookings confirmed ({itinerary_id})")
    return {
        "itinerary_id": itinerary_id,
        "bookings": {
            "Sogo Harbour Hotel breakfast": "confirmed, 50% rate applied",
            "Convention Center wellness pass": "reserved, QR on Super App",
            "Skyline 47 lunch (2 pax)": "13:00 window seat, bay view",
            "Jeepney pass": "loaded on visitor wristband",
            "Harbour City Beach Club day pass": "cabana 7 reserved 15:00-18:00",
            "Jollibee Sky Deck sunset + dinner": "18:30, terrace 2-top",
        },
        "total_charged_php": 4_200,
        "payment_method": "Face-ID on visitor wristband",
        "confirmation_sent_to": "guest Super App + email",
        "status": "all confirmed",
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
# Filler phrases (used by client.py server-side injection, not LLM-driven)
# ---------------------------------------------------------------------------

import random

FILLER_PHRASES = [
    "One moment.",
    "One moment, sir.",
    "Pulling that up now.",
    "Accessing city systems.",
    "Running the query.",
    "Querying the grid.",
    "Scanning the network.",
    "Retrieving that data.",
    "On it.",
    "Accessing records.",
    "Analyzing now.",
    "Right away.",
    "Stand by.",
    "One second.",
    "Pulling city data.",
    "Querying Eve systems.",
    "Running diagnostics.",
    "Accessing the network.",
    "Scanning city data.",
    "Processing.",
]


def get_random_filler() -> str:
    """Return a random filler phrase for server-side injection."""
    return random.choice(FILLER_PHRASES)


# ---------------------------------------------------------------------------
# Generic dashboard widget
# ---------------------------------------------------------------------------

async def update_dashboard(params):
    """Generic widget: LLM controls title, data, and color."""
    title = params.get("title", "Widget")
    raw = params.get("data", "{}")
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        data = {"info": str(raw)}
    if not data:
        data = {"status": "No data available"}
    log_action(f"Dashboard: {title}")
    return data


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
    # Scenario 5
    "draft_narrative": draft_narrative,
    "request_stakeholder_input": request_stakeholder_input,
    "book_meeting_room": book_meeting_room,
    "order_catering": order_catering,
    "render_chart": render_chart,
    "generate_slide_preview": generate_slide_preview,
    # Scenario 6
    "plan_day_itinerary": plan_day_itinerary,
    "book_itinerary": book_itinerary,
    # Scenario 4
    "get_weather_alert": get_weather_alert,
    "activate_flood_gates": activate_flood_gates,
    "send_mass_alert": send_mass_alert,
    "check_backup_power": check_backup_power,
    "book_emergency_accommodation": book_emergency_accommodation,
    # Generic
    "update_dashboard": update_dashboard,
}
