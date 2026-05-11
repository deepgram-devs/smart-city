"""Function definitions sent to the Deepgram Voice Agent API."""

from saga.mock_data import MANAGEMENT_STAKEHOLDERS_WITH_ROLES

SAGA_FUNCTION_DEFINITIONS = [
    # ----- Scenario 1: Command & Control -----
    {
        "name": "get_grid_status",
        "description": "Get the power grid status overlay for a specific zone or all zones. Use when the user asks about power, energy, grid status, or load.",
        "parameters": {
            "type": "object",
            "properties": {
                "zone": {
                    "type": "string",
                    "description": "Zone name (e.g. 'Phase 1 Core', 'Smart BPO Sector', 'Convention Center', 'Residential North', 'Marina District'). Leave empty for all zones.",
                }
            },
        },
    },
    {
        "name": "analyze_energy_spike",
        "description": "Analyze an energy spike in a zone, identify the cause, and report what autonomous mitigation was taken. Use when the user asks about spikes, surges, or unusual load.",
        "parameters": {
            "type": "object",
            "properties": {
                "zone": {
                    "type": "string",
                    "description": "The zone experiencing the spike (default: Smart BPO Sector)",
                }
            },
        },
    },
    {
        "name": "get_zone_overview",
        "description": "Get a general overview of a named zone including power, transit, residents, and air quality.",
        "parameters": {
            "type": "object",
            "properties": {
                "zone": {
                    "type": "string",
                    "description": "Zone name",
                }
            },
            "required": ["zone"],
        },
    },
    # ----- Scenario 2: Frictionless Resident -----
    {
        "name": "book_pod",
        "description": "Book an autonomous transport pod to a destination. Use when the user wants to go somewhere, book a ride, or get a pod.",
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Where the pod should go (e.g. 'Office 800 Hub', 'Convention Center', 'Marina District')",
                }
            },
            "required": ["destination"],
        },
    },
    {
        "name": "order_coffee",
        "description": "Order a coffee or drink and pay via Face-ID. Use when the user mentions coffee, drinks, or ordering at a cafe.",
        "parameters": {
            "type": "object",
            "properties": {
                "drink": {
                    "type": "string",
                    "description": "The drink to order (e.g. 'flat white', 'espresso', 'matcha latte')",
                },
                "location": {
                    "type": "string",
                    "description": "Where to order from (default: lobby cafe)",
                },
            },
            "required": ["drink"],
        },
    },
    {
        "name": "set_climate",
        "description": "Set the HVAC temperature for the user's office or home. Use when the user mentions temperature, cooling, heating, or climate.",
        "parameters": {
            "type": "object",
            "properties": {
                "temperature": {
                    "type": "number",
                    "description": "Target temperature in Celsius",
                },
                "location": {
                    "type": "string",
                    "description": "Location (e.g. 'office', 'home', 'bedroom')",
                },
            },
            "required": ["temperature"],
        },
    },
    {
        "name": "check_energy_credits",
        "description": "Check the resident's energy credit balance and solar contribution. Use when the user asks about credits, energy savings, or solar.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    # ----- Scenario 3: Power User -----
    {
        "name": "analyze_revenue",
        "description": "Analyze revenue data from a city source like the Smart Grid. Use when the user asks about revenue, financials, or earnings.",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Revenue source (e.g. 'Smart Grid', 'Transit', 'Real Estate')",
                },
                "period": {
                    "type": "string",
                    "description": "Time period (e.g. 'last month', 'Q1 2026', 'YTD')",
                },
            },
        },
    },
    {
        "name": "create_projection",
        "description": "Create a multi-year financial projection. Use when the user asks for projections, forecasts, or future revenue models.",
        "parameters": {
            "type": "object",
            "properties": {
                "years": {
                    "type": "number",
                    "description": "Number of years to project (default: 10)",
                },
                "tenant_increase_pct": {
                    "type": "number",
                    "description": "Assumed increase in tenant density as a percentage (default: 20)",
                },
            },
        },
    },
    {
        "name": "generate_deck",
        "description": "Generate a branded presentation deck. Use when the user asks to create a deck, slides, or presentation.",
        "parameters": {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "description": "Format or audience (e.g. 'Board review', 'Investor pitch', 'Internal update')",
                },
                "brand_kit": {
                    "type": "string",
                    "description": "Brand kit to use (default: 'Harbour City')",
                },
            },
        },
    },
    {
        "name": "send_notification",
        "description": "Send a notification to a person via Eve wearable and email. Use when the user asks to notify, email, or alert someone.",
        "parameters": {
            "type": "object",
            "properties": {
                "recipient": {
                    "type": "string",
                    "description": "Name of the person to notify",
                },
                "content": {
                    "type": "string",
                    "description": "Message content",
                },
                "priority": {
                    "type": "string",
                    "description": "Priority level",
                    "enum": ["low", "normal", "high", "urgent"],
                },
            },
            "required": ["recipient", "content"],
        },
    },
    # ----- Scenario 5: Board Prep (Executive Assistant) -----
    {
        "name": "draft_narrative",
        "description": "Draft speaker notes / narrative talking points for a presentation. Use when the user asks for talking points, narrative, what to say, or recommendations for a deck.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Narrative topic (e.g. 'Q1 financial results', 'board review', 'investor pitch')",
                },
                "audience": {
                    "type": "string",
                    "description": "Audience (e.g. 'Board of Directors', 'Investors', 'Executive Team')",
                },
            },
        },
    },
    {
        "name": "request_stakeholder_input",
        "description": "Email a group of stakeholders to request input or review on a deliverable. Use when the user wants to gather inputs, send out for review, or ping stakeholders before a meeting.",
        "parameters": {
            "type": "object",
            "properties": {
                "deliverable": {
                    "type": "string",
                    "description": "What stakeholders are being asked to review (e.g. 'Q1 board deck', 'sustainability projections')",
                },
                "recipients": {
                    "type": "string",
                    "description": f"Comma-separated stakeholder names (default: {MANAGEMENT_STAKEHOLDERS_WITH_ROLES})",
                },
                "deadline": {
                    "type": "string",
                    "description": "When inputs are needed by (e.g. '3 PM today', 'end of day')",
                },
            },
            "required": ["deliverable"],
        },
    },
    {
        "name": "book_meeting_room",
        "description": "Book a meeting room and send calendar invites to attendees. Use when the user asks to book a room, schedule a meeting, or set up a board meeting.",
        "parameters": {
            "type": "object",
            "properties": {
                "room": {
                    "type": "string",
                    "description": "Room name (e.g. 'Tower A Boardroom', 'Convention Center Summit Hall')",
                },
                "time": {
                    "type": "string",
                    "description": "Meeting time (e.g. '4 PM today', 'tomorrow 10 AM')",
                },
                "attendees": {
                    "type": "string",
                    "description": "Comma-separated attendee names or a group (e.g. 'Board of Directors', 'exec team')",
                },
                "purpose": {
                    "type": "string",
                    "description": "Short meeting subject for the calendar invite",
                },
            },
        },
    },
    {
        "name": "order_catering",
        "description": "Order catering (coffee, pastries, lunch) for a group meeting, paid via Face-ID. Use when the user asks to order coffee/food for a meeting or group.",
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "string",
                    "description": "What to order (e.g. 'espresso bar and pastries', 'sandwich platters')",
                },
                "headcount": {
                    "type": "number",
                    "description": "Number of attendees (default: 8)",
                },
                "location": {
                    "type": "string",
                    "description": "Delivery location (default: Tower A Boardroom)",
                },
            },
            "required": ["items"],
        },
    },
    {
        "name": "render_chart",
        "description": "Render a data visualization as a dashboard widget. Use when presenting numeric data that benefits from a visual — revenue trends, energy mix, projections. Call MULTIPLE times with different titles to show multiple charts side by side. Each unique title creates a new widget; reusing a title updates the existing chart.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Chart title (unique per chart, e.g. 'Revenue Trend', 'Revenue Mix')",
                },
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "donut", "sparkline"],
                    "description": "Chart kind. bar=categories, line=trend over time, donut=share of whole, sparkline=compact trend",
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Category labels (e.g. ['Q2 2025','Q3 2025','Q4 2025','Q1 2026'])",
                },
                "values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Numeric values matching labels order",
                },
                "unit": {
                    "type": "string",
                    "description": "Unit suffix for tooltips (e.g. '$B', 'MW', '%')",
                },
                "color": {
                    "type": "string",
                    "enum": ["blue", "green", "amber", "red"],
                    "description": "Primary accent color",
                },
            },
            "required": ["title", "chart_type", "labels", "values"],
        },
    },
    {
        "name": "generate_slide_preview",
        "description": "Show a 5-slide visual preview grid of a generated presentation — each card has a title, hero statistic, and caption. Call this AFTER generate_deck to give the user a glanceable view of what's in the deck.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Deck topic (e.g. 'Q1 2026 Board Review')",
                },
                "slides": {
                    "type": "array",
                    "description": "Exactly 5 slide objects in presentation order",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Slide title (short)"},
                            "hero_stat": {"type": "string", "description": "Headline number (e.g. '$5.13B', '+14.2%', '87%')"},
                            "caption": {"type": "string", "description": "1-line caption explaining the stat"},
                        },
                        "required": ["title", "hero_stat", "caption"],
                    },
                },
            },
            "required": ["slides"],
        },
    },
    # ----- Scenario 6: Tourist / Visitor Concierge -----
    {
        "name": "plan_day_itinerary",
        "description": "Plan a full day tourist itinerary for Harbour City, weather-aware, with breakfast / activities / lunch / dinner / sunset. Use when a visitor or tourist asks what to do today, or asks for an itinerary / day plan.",
        "parameters": {
            "type": "object",
            "properties": {
                "guest_name": {
                    "type": "string",
                    "description": "Visitor name if known (optional)",
                },
                "interests": {
                    "type": "string",
                    "description": "Comma-separated interests (e.g. 'food, wellness, walking, swimming'). Leave empty for a balanced plan.",
                },
            },
        },
    },
    {
        "name": "book_itinerary",
        "description": "Confirm and book all items in a generated itinerary (reservations, tickets, transport). Use ONLY after the user confirms they want bookings made for the itinerary.",
        "parameters": {
            "type": "object",
            "properties": {
                "itinerary_id": {
                    "type": "string",
                    "description": "Itinerary reference (default: the most recent one)",
                }
            },
        },
    },
    # ----- Scenario 4: Proactive Guardian -----
    {
        "name": "get_weather_alert",
        "description": "Get current weather alerts and warnings. Use when the user asks about weather, storms, or alerts.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "activate_flood_gates",
        "description": "Schedule or activate the smart flood gates. Use when discussing flood protection or storm preparation.",
        "parameters": {
            "type": "object",
            "properties": {
                "close_time": {
                    "type": "string",
                    "description": "When the gates should close (e.g. '9:00 PM', 'immediately')",
                }
            },
            "required": ["close_time"],
        },
    },
    {
        "name": "send_mass_alert",
        "description": "Send a mass alert to all residents via the Super App. Use for emergency notifications, safety advisories, or city-wide announcements.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Alert message content",
                },
                "zones": {
                    "type": "string",
                    "description": "Affected zones (e.g. 'all low-level zones', 'Marina District')",
                },
            },
            "required": ["message"],
        },
    },
    {
        "name": "check_backup_power",
        "description": "Check emergency backup power status for a facility. Use when discussing emergency preparedness or power continuity.",
        "parameters": {
            "type": "object",
            "properties": {
                "facility": {
                    "type": "string",
                    "description": "Facility name (e.g. 'Data Center', 'Hospital', 'Command Center')",
                }
            },
        },
    },
    {
        "name": "book_emergency_accommodation",
        "description": "Arrange discounted emergency hotel accommodation for residents in affected zones.",
        "parameters": {
            "type": "object",
            "properties": {
                "zone": {
                    "type": "string",
                    "description": "Affected zone (e.g. 'low-level zones', 'Marina District')",
                },
                "discount_pct": {
                    "type": "number",
                    "description": "Discount percentage to offer (default: 10)",
                },
            },
        },
    },
    # ----- Generic Dashboard Widget -----
    {
        "name": "update_dashboard",
        "description": (
            "Display a widget card on the city dashboard with structured data. "
            "The data parameter IS the content shown to the user, so populate it with "
            "all relevant information. Generate realistic city data for any query. "
            "Each unique title creates a new widget; reusing a title updates it. "
            "Call this for ANY query, including those without a dedicated function."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Widget card title (e.g., 'Grocery Deliveries', 'Air Quality')",
                },
                "data": {
                    "type": "string",
                    "description": (
                        "JSON string of key-value pairs to display as widget rows. "
                        "MUST contain actual data. "
                        "Example: '{\"store\": \"FreshMart Phase 1\", \"items\": \"Milk, Eggs, Bread\", "
                        "\"total\": \"$47.80\", \"status\": \"Delivered\", \"eta\": \"2:30 PM\"}'"
                    ),
                },
                "color": {
                    "type": "string",
                    "enum": ["blue", "green", "amber", "red"],
                    "description": "blue=info, green=good, amber=warning, red=alert",
                },
            },
            "required": ["title", "data"],
        },
    },
]
