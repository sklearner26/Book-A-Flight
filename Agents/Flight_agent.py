import time

from state import TravelState

from utils.logging import create_log_entry

from tools.flight_tool import (
    search_flights,
    parse_route,
)

from langchain_core.messages import AIMessage


def flight_agent(state: TravelState):
    start_time = time.time()
    query = state["user_query"]
    logs = [
        create_log_entry("info", f"Flight Specialist activated. Analyzing travel query: '{query}'")
    ]
    
    # Reasoning step 1: Route parsing
    dep_iata, arr_iata = parse_route(query)
    logs.append(create_log_entry("reasoning", f"Parsed route entities: Origin IATA = '{dep_iata or 'ANY'}', Destination IATA = '{arr_iata or 'ANY'}'"))
    
    # Tool execution
    tool_start = time.time()
    flight_data = search_flights(query)
    tool_duration = round(time.time() - tool_start, 2)
    
    logs.append(create_log_entry("tool", f"AviationStack API called for route {dep_iata or 'Global'} -> {arr_iata or 'Global'} ({tool_duration}s)"))
    
    # Reasoning step 2: Result analysis
    is_live_data = "No live flight data found" not in flight_data and "Flight API error" not in flight_data
    flight_count = flight_data.count("Flight:") if is_live_data else 0
    
    if is_live_data:
        reasoning_summary = (
            f"Successfully resolved flight route from {dep_iata or 'Origin'} to {arr_iata or 'Destination'}. "
            f"Retrieved {flight_count} live scheduled flights from AviationStack with operational status, "
            f"terminals, and flight numbers."
        )
        logs.append(create_log_entry("success", f"Identified {flight_count} live flight options."))
    else:
        reasoning_summary = (
            f"Searched AviationStack database for route {dep_iata or 'Origin'} -> {arr_iata or 'Destination'}. "
            f"Live flight status API returned no active flights or limitations for this specific route. "
            f"Flagged for synthesis agent to provide estimated airline routes and travel guidance."
        )
        logs.append(create_log_entry("warn", "No live scheduled flights directly matched. Passing route context."))
    
    end_time = time.time()
    duration = round(end_time - start_time, 2)
    
    trace_item = {
        "step_id": "step_flight",
        "agent_id": "flight_agent",
        "agent_name": "Flight Specialist Agent",
        "role": "Route Analysis & Live Flight Lookup",
        "icon": "✈️",
        "status": "completed",
        "start_time": start_time,
        "end_time": end_time,
        "duration_sec": duration,
        "thoughts": [
            f"1. Entity Extraction: Extracted origin '{dep_iata or 'Default/Auto'}' and destination '{arr_iata or 'Auto-detect'}' from user query.",
            f"2. Database Resolution: Checked IATA airport dictionary and preferred country hubs.",
            f"3. API Strategy: Queried AviationStack live tracking API with parameters dep_iata={dep_iata}, arr_iata={arr_iata}.",
            f"4. Synthesis Preparation: Formatted flight departure/arrival schedules and carrier details for the downstream itinerary planner."
        ],
        "tool_calls": [
            {
                "tool_name": "AviationStack Flights API",
                "input": {"query": query, "dep_iata": dep_iata, "arr_iata": arr_iata, "limit": 10},
                "status": "200 OK" if is_live_data else "No live flights / Informational",
                "output_preview": flight_data[:350] + ("..." if len(flight_data) > 350 else ""),
                "duration_sec": tool_duration
            }
        ],
        "observations": {
            "origin_iata": dep_iata or "Auto",
            "destination_iata": arr_iata or "Auto",
            "flights_found": flight_count,
            "status": "Live Data Available" if is_live_data else "Fallback Route Guidance"
        },
        "reasoning": reasoning_summary,
        "output_preview": flight_data[:400] + "...",
        "raw_output": flight_data,
        "logs": logs
    }

    return {
        "flight_results": flight_data,
        "messages": [
            AIMessage(content=f"Flight Specialist: {reasoning_summary}")
        ],
        "llm_calls": state.get("llm_calls", 0),
        "trace": [trace_item]
    }
