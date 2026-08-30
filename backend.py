import os 
import certifi
import time
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
from Agents.validator_agent import validator_agent
from Agents.Flight_agent import flight_agent
from Agents.Hotel_agent import hotel_agent
from Agents.Itinerary_agent import itinerary_agent
from Agents.final_agent import final_agent
from state import TravelState
from config import llm
from utils.logging import create_log_entry
load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator

import psycopg
from psycopg.rows import dict_row

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
)
from langchain_groq import ChatGroq
from tools.tavily_tool import tavily_search
from tools.flight_tool import search_flights, parse_route, resolve_location_to_iata


def get_database_url():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "DATABASE_URL is missing. Please add your Render PostgreSQL External Database URL to .env"
        )

    if "sslmode=" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"

    return database_url

# =========================
# Build Graph
# =========================

def check_validation_route(state: TravelState):
    """
    Routes to flight_agent if query passed validation, otherwise routes directly to END.
    """
    if state.get("is_valid", False):
        return "flight_agent"
    return END


graph = StateGraph(TravelState)

graph.add_node("validator_agent", validator_agent)
graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("itinerary_agent", itinerary_agent)
graph.add_node("final_agent", final_agent)

graph.add_edge(START, "validator_agent")
graph.add_conditional_edges(
    "validator_agent",
    check_validation_route,
    {
        "flight_agent": "flight_agent",
        END: END
    }
)
graph.add_edge("flight_agent", "hotel_agent")
graph.add_edge("hotel_agent", "itinerary_agent")
graph.add_edge("itinerary_agent", "final_agent")
graph.add_edge("final_agent", END)


# =========================
# PostgreSQL Checkpointer
# =========================
DATABASE_URL = get_database_url()

_conn = psycopg.connect(
    DATABASE_URL,
    autocommit=True,
    row_factory=dict_row
)

checkpointer = PostgresSaver(_conn)
checkpointer.setup()

travel_graph = graph.compile(checkpointer=checkpointer)


# =========================
# Run Function (Batch)
# =========================

def run_travel_agent(user_input: str, thread_id: str | None = None):
    if not thread_id:
        thread_id = f"user_{uuid.uuid4().hex}"

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    result = travel_graph.invoke(
        {
            "messages": [
                HumanMessage(content=user_input)
            ],
            "user_query": user_input,
            "is_valid": True,
            "validation_message": "",
            "flight_results": "",
            "hotel_results": "",
            "itinerary": "",
            "llm_calls": 0,
            "trace": []
        },
        config=config
    )

    final_answer = result["messages"][-1].content if result.get("messages") else ""

    return {
        "thread_id": thread_id,
        "answer": final_answer,
        "is_valid": result.get("is_valid", True),
        "validation_message": result.get("validation_message", ""),
        "flight_results": result.get("flight_results", ""),
        "hotel_results": result.get("hotel_results", ""),
        "itinerary": result.get("itinerary", ""),
        "llm_calls": result.get("llm_calls", 0),
        "trace": result.get("trace", [])
    }


# =========================
# Stream Function (Event-Driven Generator)
# =========================

def stream_travel_agent(user_input: str, thread_id: str | None = None):
    """
    Yields step-by-step progress events for real-time observability in the frontend.
    """
    if not thread_id:
        thread_id = f"user_{uuid.uuid4().hex}"

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "user_query": user_input,
        "is_valid": True,
        "validation_message": "",
        "flight_results": "",
        "hotel_results": "",
        "itinerary": "",
        "llm_calls": 0,
        "trace": []
    }

    accumulated_trace = []
    final_answer = ""
    is_valid = True
    validation_message = ""
    flight_results = ""
    hotel_results = ""
    itinerary = ""
    llm_calls = 0

    # Stream through the LangGraph nodes
    for event in travel_graph.stream(initial_state, config=config, stream_mode="updates"):
        for node_name, node_output in event.items():
            if "trace" in node_output and node_output["trace"]:
                step_trace = node_output["trace"][-1]
                accumulated_trace.append(step_trace)
                
                # Yield agent completed step with full reasoning & tool telemetry
                yield {
                    "event": "agent_step",
                    "agent_id": step_trace["agent_id"],
                    "agent_name": step_trace["agent_name"],
                    "step_trace": step_trace,
                    "accumulated_trace": accumulated_trace
                }

            if "is_valid" in node_output:
                is_valid = node_output["is_valid"]
            if "validation_message" in node_output:
                validation_message = node_output["validation_message"]
            if "flight_results" in node_output:
                flight_results = node_output["flight_results"]
            if "hotel_results" in node_output:
                hotel_results = node_output["hotel_results"]
            if "itinerary" in node_output:
                itinerary = node_output["itinerary"]
            if "llm_calls" in node_output:
                llm_calls = node_output["llm_calls"]
            if "messages" in node_output and node_output["messages"]:
                last_msg = node_output["messages"][-1]
                if node_name == "validator_agent" and not node_output.get("is_valid", False):
                    final_answer = last_msg.content
                elif node_name == "final_agent":
                    final_answer = last_msg.content

    # Final event
    yield {
        "event": "complete",
        "thread_id": thread_id,
        "answer": final_answer,
        "is_valid": is_valid,
        "validation_message": validation_message,
        "flight_results": flight_results,
        "hotel_results": hotel_results,
        "itinerary": itinerary,
        "llm_calls": llm_calls,
        "trace": accumulated_trace
    }

