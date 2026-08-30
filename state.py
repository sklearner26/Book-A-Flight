from typing import TypedDict, Annotated, Dict, Any
import operator

from langchain_core.messages import AnyMessage


class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]

    user_query: str

    is_valid: bool
    validation_message: str

    flight_results: str
    hotel_results: str
    itinerary: str

    llm_calls: int

    trace: Annotated[list[Dict[str, Any]], operator.add]

