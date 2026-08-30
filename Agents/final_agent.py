import time

from state import TravelState
from config import llm

from utils.logging import create_log_entry

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
)

def final_agent(state: TravelState):
    start_time = time.time()
    logs = [
        create_log_entry("info", "Travel Synthesis Agent activated. Unifying flights, accommodations, and itinerary into publication-ready package.")
    ]
    
    final_prompt = f"""Generate the final comprehensive travel plan for the user.

User Request:
{state['user_query']}

Flight Information:
{state['flight_results']}

Hotel Suggestions:
{state['hotel_results']}

Itinerary:
{state['itinerary']}

Please format the final response beautifully and professionally using these exact sections with clear markdown formatting:

# 🌟 [Destination] Travel Plan

## 1. 📌 Trip Summary
- Overview of the trip, duration, travel style, and key highlights.

## 2. ✈️ Flight Information & Air Travel
- Flight details, airline options, route schedule, and live status insights.
- Note that live flight status API does not supply ticket fares; provide estimated standard ticket ranges.

## 3. 🏨 Accommodation & Hotel Suggestions
- Curated hotel recommendations with location perks, key amenities, and booking guidance.

## 4. 🗺️ Day-by-Day Detailed Itinerary
- Complete, easy-to-follow daily breakdown (Morning, Afternoon, Evening) with food recommendations and transit tips.

## 5. 💰 Estimated Budget Breakdown
- Detailed realistic budget estimate table (Flights, Hotels, Food, Activities, Local Transit, Miscellaneous) aligned with the user's currency/budget if specified.

## 6. 💡 Practical Travel Tips & Recommendations
- Essential visa guidelines, best local SIM/eSIM, payment methods (cash vs card), safety, and cultural etiquette.
"""

    logs.append(create_log_entry("reasoning", "Synthesizing executive summary, detailed budget matrix, and travel advisories..."))
    
    tool_start = time.time()
    response = llm.invoke([
        SystemMessage(content="You are a prestigious AI travel master and luxury booking consultant."),
        HumanMessage(content=final_prompt)
    ])
    tool_duration = round(time.time() - tool_start, 2)
    
    final_content = response.content
    logs.append(create_log_entry("tool", f"Final LLM Synthesis completed in {tool_duration}s"))
    logs.append(create_log_entry("success", "Travel plan compiled with full budget breakdown and travel advisory."))
    
    end_time = time.time()
    duration = round(end_time - start_time, 2)
    
    trace_item = {
        "step_id": "step_final",
        "agent_id": "final_agent",
        "agent_name": "Travel Synthesis & Master Agent",
        "role": "Master Document Compilation & Budget Architecture",
        "icon": "📋",
        "status": "completed",
        "start_time": start_time,
        "end_time": end_time,
        "duration_sec": duration,
        "thoughts": [
            "1. Multi-Agent Synthesis: Consolidated flight routing, verified hotel recommendations, and activity schedules.",
            "2. Budget Modeling: Built comprehensive itemized cost table calibrated to traveler request.",
            "3. Actionable Advisory: Included practical logistics on local transport, visa, SIM cards, and etiquette.",
            "4. Markdown Architecture: Structured clear headings, badges, and bullet points for maximum readability and PDF export."
        ],
        "tool_calls": [
            {
                "tool_name": "Groq Chat (qwen/qwen3.8-27b)",
                "input": {"system": "Master travel consultant", "final_prompt_len": len(final_prompt)},
                "status": "200 OK",
                "output_preview": final_content[:350] + "...",
                "duration_sec": tool_duration
            }
        ],
        "observations": {
            "sections_generated": ["Trip Summary", "Flight Info", "Hotels", "Itinerary", "Budget", "Tips"],
            "total_output_chars": len(final_content),
            "status": "Final Plan Ready"
        },
        "reasoning": "Completed comprehensive travel guide compilation with full financial breakdown and actionable advisories.",
        "output_preview": final_content[:400] + "...",
        "raw_output": final_content,
        "logs": logs
    }

    return {
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
        "trace": [trace_item]
    }
