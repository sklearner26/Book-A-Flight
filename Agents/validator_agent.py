from state import TravelState
from utils.logging import create_log_entry
import json
import time
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
)
from config import llm
from tools.flight_tool import parse_route

def validator_agent(state: TravelState):
    """
    Validates user query to ensure:
    1. Query is related to travel/vacations/flight booking/trip planning.
    2. Origin and destination are either clearly specified or inferable.
    If not related or missing key route info, gently asks for details or declines politely.
    """
    start_time = time.time()
    query = state["user_query"]
    logs = [
        create_log_entry("info", f"Trip Validator activated. Evaluating query intent: '{query}'")
    ]
    
    validation_prompt = f"""You are an intelligent Travel Request Validator.
Analyze the user's travel query and determine:
1. Is this query related to travel, trip planning, tourism, vacations, flight routes, or hotel bookings?
2. Has the user mentioned or clearly implied their ORIGIN (where they are starting/flying from)?
3. Has the user mentioned or clearly implied their DESTINATION (where they want to go)?

User Query:
"{query}"

Respond strictly with a JSON object in this exact format (no surrounding text or markdown ticks):
{{
    "is_travel_related": true,
    "origin": "Origin City/Country or null",
    "destination": "Destination City/Country or null",
    "is_valid": true,
    "reason": "Brief explanation of evaluation",
    "gentle_reply": "Friendly response if invalid or missing information, otherwise empty string"
}}

Rules:
- If the query is NOT travel related (e.g. math questions, general coding, sports, cooking, etc.):
  "is_travel_related": false, "is_valid": false,
  "gentle_reply": "Hello! I am your AI Travel Concierge. I specialize in planning personalized vacations, finding live flight routes, scouting cozy hotels, and crafting complete daily itineraries. It looks like your query isn't about travel. Where in the world would you love to travel to? Please share your dream destination!"
- If the query is travel related but is missing ORIGIN (departure city/country):
  "is_valid": false,
  "gentle_reply": "I would love to help you plan your trip! To look up the best live flight routes and calculate your budget accurately, could you please let me know your departure city or airport (where you are flying from)?"
- If the query is travel related but is missing DESTINATION:
  "is_valid": false,
  "gentle_reply": "I would be delighted to plan your journey! Where would you like to travel? Please let me know your desired destination city or country so our travel team can get to work!"
- If BOTH origin and destination are present (or for general international flight route search queries):
  "is_valid": true,
  "gentle_reply": ""
"""

    logs.append(create_log_entry("reasoning", "Analyzing travel intent, origin entity, and destination entity..."))
    
    tool_start = time.time()
    response = llm.invoke([
        SystemMessage(content="You are a precise JSON-only validation agent."),
        HumanMessage(content=validation_prompt)
    ])
    tool_duration = round(time.time() - tool_start, 2)
    
    raw_response = response.content.strip()
    # Clean possible markdown wrapping
    if raw_response.startswith("```json"):
        raw_response = raw_response[7:]
    if raw_response.startswith("```"):
        raw_response = raw_response[3:]
    if raw_response.endswith("```"):
        raw_response = raw_response[:-3]
    raw_response = raw_response.strip()

    try:
        val_data = json.loads(raw_response)
    except Exception as e:
        # Fallback if JSON parsing fails: use heuristic route parsing
        dep, arr = parse_route(query)
        is_travel = any(w in query.lower() for w in ["trip", "travel", "flight", "hotel", "visit", "tour", "vacation", "holiday", "days", "day", "ticket", "go to", "from"])
        val_data = {
            "is_travel_related": is_travel,
            "origin": dep,
            "destination": arr,
            "is_valid": bool(dep and arr) if is_travel else False,
            "reason": "Evaluated via fallback parser",
            "gentle_reply": "Could you please specify your departure city and destination to plan your flights and itinerary?" if not (dep and arr) else ""
        }

    is_valid = val_data.get("is_valid", False)
    is_travel = val_data.get("is_travel_related", False)
    origin = val_data.get("origin")
    destination = val_data.get("destination")
    gentle_reply = val_data.get("gentle_reply", "")
    reason = val_data.get("reason", "Query validation complete.")

    end_time = time.time()
    duration = round(end_time - start_time, 2)

    if is_valid:
        logs.append(create_log_entry("success", f"Validation passed: Origin='{origin}', Destination='{destination}'"))
    elif not is_travel:
        logs.append(create_log_entry("warn", "Query is not travel related. Pausing pipeline."))
    else:
        logs.append(create_log_entry("warn", f"Missing travel details: Origin='{origin}', Destination='{destination}'"))

    trace_item = {
        "step_id": "step_validator",
        "agent_id": "validator_agent",
        "agent_name": "Trip Validator Agent",
        "role": "Route & Intent Verification",
        "icon": "🧭",
        "status": "completed" if is_valid else "clarification_needed",
        "start_time": start_time,
        "end_time": end_time,
        "duration_sec": duration,
        "thoughts": [
            f"1. Intent Classification: Travel Related = {is_travel}",
            f"2. Origin Detection: '{origin or 'Not Specified'}'",
            f"3. Destination Detection: '{destination or 'Not Specified'}'",
            f"4. Gatekeeper Outcome: {'Proceed to Flight Finder' if is_valid else 'Requesting clarification from user'}"
        ],
        "tool_calls": [
            {
                "tool_name": "Groq LLM Intent & Entity Classifier",
                "input": {"query": query},
                "status": "200 OK",
                "output_preview": json.dumps(val_data),
                "duration_sec": tool_duration
            }
        ],
        "observations": {
            "travel_intent": "Confirmed" if is_travel else "Non-Travel Query",
            "origin_found": origin or "Missing",
            "destination_found": destination or "Missing",
            "validation_status": "Valid - Proceeding" if is_valid else "Paused - Clarification Needed"
        },
        "reasoning": reason,
        "output_preview": gentle_reply if not is_valid else f"Valid travel query: {origin} -> {destination}",
        "raw_output": raw_response,
        "logs": logs
    }

    ai_messages = [AIMessage(content=gentle_reply)] if not is_valid else []

    return {
        "is_valid": is_valid,
        "validation_message": gentle_reply,
        "messages": ai_messages,
        "llm_calls": state.get("llm_calls", 0) + 1,
        "trace": [trace_item]
    }
