import json
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.tools import (
    get_order_summary, get_payment_status, get_delivery_status,
    search_orders_by_customer, list_orders_needing_attention,
)

SYSTEM_PROMPT = """You are an internal operations copilot for Cars24, a used-car marketplace.
Ops team members ask you questions about orders, payments, and deliveries in natural language.
You have tools to look up real data -- ALWAYS use them rather than guessing or making up information.
When a question implies a discrepancy (e.g. "customer paid but delivery isn't scheduled"), fetch the
relevant data and clearly explain what's actually going on, referencing the real statuses you found.
Keep answers concise, factual, and actionable for an ops agent. If an order doesn't exist, say so plainly."""

GROQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_order_summary",
            "description": "Get the full status summary of an order: order status, payment status, delivery status, customer and vehicle info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer", "description": "The order ID"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_payment_status",
            "description": "Get only the payment status/details for a specific order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer", "description": "The order ID"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_delivery_status",
            "description": "Get only the delivery status/details for a specific order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer", "description": "The order ID"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_orders_by_customer",
            "description": "Find all orders for a customer, given their name or phone number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name_or_phone": {"type": "string", "description": "Customer name or phone number"}
                },
                "required": ["name_or_phone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_orders_needing_attention",
            "description": "List all orders where payment is complete but delivery has not been scheduled yet.",
            "parameters": {
                "type": "object",
                "properties": {},
            }
        }
    }
]


def _execute_tool(db: Session, name: str, args: dict):
    if name == "get_order_summary":
        return get_order_summary(db, int(args.get("order_id", 0)))
    elif name == "get_payment_status":
        return get_payment_status(db, int(args.get("order_id", 0)))
    elif name == "get_delivery_status":
        return get_delivery_status(db, int(args.get("order_id", 0)))
    elif name == "search_orders_by_customer":
        return search_orders_by_customer(db, str(args.get("name_or_phone", "")))
    elif name == "list_orders_needing_attention":
        return list_orders_needing_attention(db)
    return {"error": f"Unknown tool {name}"}


def _run_llm(db: Session, query: str) -> dict:
    from groq import Groq

    client = Groq(api_key=settings.groq_api_key)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query}
    ]
    collected_data = {}

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        tools=GROQ_TOOLS,
        tool_choice="auto",
        max_tokens=1024,
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if tool_calls:
        messages.append(response_message)
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            tool_output = _execute_tool(db, function_name, function_args)
            collected_data[function_name] = tool_output

            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": json.dumps(tool_output),
            })

        second_response = client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
        )
        final_answer = second_response.choices[0].message.content
        return {"answer": final_answer, "data": collected_data}

    return {"answer": response_message.content, "data": collected_data}


def _extract_order_id(query: str) -> Optional[int]:
    match = re.search(r"#?\s*(\d{1,6})", query)
    return int(match.group(1)) if match else None


def _wants_attention_list(q: str) -> bool:
    return any(kw in q for kw in ("needing attention", "need attention", "stuck", "flag"))


def _mentions_payment_only(q: str) -> bool:
    return ("payment" in q or "paid" in q) and "delivery" not in q


def _mentions_discrepancy(q: str) -> bool:
    payment_words = ("paid", "payment")
    delivery_words = ("delivery", "scheduled", "shipped")
    return any(w in q for w in payment_words) and any(w in q for w in delivery_words)


def _handle_attention_list(db: Session) -> dict:
    data = list_orders_needing_attention(db)
    ids = [o["order_id"] for o in data["flagged_orders"]]
    answer = (
        f"There are {data['count']} order(s) where payment is complete but delivery "
        f"hasn't been scheduled: order IDs {ids}."
        if data["count"] else
        "No orders are currently stuck between payment and delivery scheduling."
    )
    return {"answer": answer, "data": data}


def _handle_payment_only(order_id: int, data: dict) -> dict:
    p = data["payment"]
    detail = f", paid via {p['method']} on {p['paid_at']}." if p["status"] == "paid" else "."
    return {"answer": f"Order #{order_id}: payment status is '{p['status']}'{detail}", "data": data}


def _handle_discrepancy(order_id: int, data: dict) -> dict:
    p_status, d_status = data["payment"]["status"], data["delivery"]["status"]

    if p_status == "paid" and d_status == "not_scheduled":
        answer = (
            f"Order #{order_id}: the customer is correct -- payment is confirmed "
            f"({data['payment']['method']}, paid {data['payment']['paid_at']}), but delivery "
            f"has not been scheduled yet. This needs ops follow-up to allocate a delivery slot."
        )
        if data["delivery"].get("notes"):
            answer += f" Note on file: {data['delivery']['notes']}"
    elif p_status != "paid":
        answer = (
            f"Order #{order_id}: payment is actually '{p_status}', not confirmed -- "
            f"that's likely why delivery hasn't moved forward (currently '{d_status}')."
        )
    else:
        answer = (
            f"Order #{order_id}: payment is '{p_status}' and delivery is '{d_status}', "
            f"scheduled for {data['delivery']['scheduled_date']}."
        )

    return {"answer": answer, "data": data}


def _handle_summary(order_id: int, data: dict) -> dict:
    scheduled = data["delivery"]["scheduled_date"]
    answer = (
        f"Order #{order_id} ({data['vehicle']}) for {data['customer']['name']}: "
        f"order status '{data['order_status']}', payment '{data['payment']['status']}', "
        f"delivery '{data['delivery']['status']}'"
        + (f" (scheduled {scheduled})." if scheduled else ".")
    )
    return {"answer": answer, "data": data}


def _run_rule_based(db: Session, query: str) -> dict:
    q = query.lower()

    if _wants_attention_list(q):
        return _handle_attention_list(db)

    order_id = _extract_order_id(query)
    if order_id is None:
        return {
            "answer": "I couldn't find an order number in your question. "
                      "Please include an order ID, e.g. 'order #1234'.",
            "data": {}
        }

    data = get_order_summary(db, order_id)
    if "error" in data:
        return {"answer": data["error"], "data": data}

    if _mentions_discrepancy(q):
        return _handle_discrepancy(order_id, data)
    if _mentions_payment_only(q):
        return _handle_payment_only(order_id, data)
    return _handle_summary(order_id, data)


def answer_query(db: Session, query: str) -> dict:
    has_valid_key = (
        bool(settings.groq_api_key)
        and settings.groq_api_key.strip() != ""
        and not settings.groq_api_key.startswith("your_groq_api_key")
    )
    use_llm = settings.llm_provider == "groq" and has_valid_key

    if not use_llm:
        result = _run_rule_based(db, query)
        return {"answer": result["answer"], "mode": "rule_based", "data": result["data"]}

    try:
        result = _run_llm(db, query)
        return {"answer": result["answer"], "mode": "llm", "data": result["data"]}
    except Exception as e:
        fallback = _run_rule_based(db, query)
        fallback["mode"] = f"rule_based_fallback (llm_error: {e})"
        return fallback