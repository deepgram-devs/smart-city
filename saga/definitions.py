"""Function definitions sent to the Deepgram Voice Agent API."""

SAGA_FUNCTION_DEFINITIONS = [
    # ----- Agent filler (latency masking) -----
    {
        "name": "agent_filler",
        "description": "ALWAYS call this function FIRST before calling any other function. It provides a brief spoken acknowledgement while you process the request. Call it with message_type='lookup' when looking up data, 'processing' for actions, 'analyzing' for analysis tasks.",
        "parameters": {
            "type": "object",
            "properties": {
                "message_type": {
                    "type": "string",
                    "description": "Type of filler message",
                    "enum": ["lookup", "processing", "analyzing", "general"],
                }
            },
            "required": ["message_type"],
        },
    },
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
        "description": "Send a notification to a person via SAGA wearable and email. Use when the user asks to notify, email, or alert someone.",
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
]
