import time

from state import TravelState

from config import llm

from utils.logging import create_log_entry

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
)

def itinerary_agent(state: TravelState):
    start_time = time.time()
    logs = [
        create_log_entry("info", "Itinerary Architect activated. Reviewing flight schedules, hotel options, and traveler requirements.")
    ]
    
    prompt = f"""Create a complete, highly practical travel itinerary.

User Query:
{state['user_query']}

Flight Information Found:
{state['flight_results']}

Hotel Suggestions Found:
{state['hotel_results']}

Requirements:
- Design a structured day-by-day itinerary (Day 1, Day 2, etc.).
- Group morning, afternoon, and evening activities by logical geographic proximity.
- Account for budget constraints, local transportation, meals, and rest periods.
- Be specific with landmarks, attractions, and cultural experiences.
"""

    logs.append(create_log_entry("reasoning", "Prompting LLM (Qwen 3.8 27B) to synthesize day-by-day schedule with geographic clustering..."))
    
    tool_start = time.time()
    response = llm.invoke([
        SystemMessage(content="You are an expert master travel planner and itinerary designer."),
        HumanMessage(content=prompt)
    ])
    tool_duration = round(time.time() - tool_start, 2)
    
    itinerary_content = response.content
    logs.append(create_log_entry("tool", f"LLM Generation completed in {tool_duration}s"))
    logs.append(create_log_entry("success", "Constructed comprehensive day-by-day travel itinerary draft."))
    
    end_time = time.time()
    duration = round(end_time - start_time, 2)
    
    trace_item = {
        "step_id": "step_itinerary",
        "agent_id": "itinerary_agent",
        "agent_name": "Itinerary Architect Agent",
        "role": "Day-by-Day Scheduling & Activity Optimization",
        "icon": "🗺️",
        "status": "completed",
        "start_time": start_time,
        "end_time": end_time,
        "duration_sec": duration,
        "thoughts": [
            "1. Geographic & Temporal Clustering: Grouped sightseeing attractions by district to minimize commute times.",
            "2. Schedule Realism: Balanced iconic monuments with leisure, meal suggestions, and realistic transit buffers.",
            "3. Accommodation & Flight Synergy: Anchored Day 1 around arrival/check-in and final day around departure logistics.",
            "4. Budget Alignment: Curated a mix of free public attractions and paid highlights."
        ],
        "tool_calls": [
            {
                "tool_name": "Groq Chat (qwen/qwen3.8-27b)",
                "input": {"system": "Expert travel planner", "user_prompt_len": len(prompt)},
                "status": "200 OK",
                "output_preview": itinerary_content[:350] + "...",
                "duration_sec": tool_duration
            }
        ],
        "observations": {
            "model_used": "qwen/qwen3.8-27b",
            "itinerary_characters": len(itinerary_content),
            "status": "Day-by-Day Schedule Generated"
        },
        "reasoning": "Generated structured multi-day itinerary optimizing route flow, timing, and local dining experiences.",
        "output_preview": itinerary_content[:400] + "...",
        "raw_output": itinerary_content,
        "logs": logs
    }

    return {
        "itinerary": itinerary_content,
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
        "trace": [trace_item]
    }
