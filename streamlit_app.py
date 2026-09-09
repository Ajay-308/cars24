import streamlit as st
import requests
import time
import json

st.set_page_config(
    page_title="Cars24 AI Operations Copilot",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #ff5a00;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1rem;
        color: #6c757d;
        margin-bottom: 1.5rem;
    }
    .stButton>button {
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# State initialization
if "query_input" not in st.session_state:
    st.session_state["query_input"] = ""
if "trigger_query" not in st.session_state:
    st.session_state["trigger_query"] = False
if "current_result" not in st.session_state:
    st.session_state["current_result"] = None

def select_prompt(text: str):
    st.session_state["query_input"] = text
    st.session_state["trigger_query"] = True

def clear_query():
    st.session_state["query_input"] = ""
    st.session_state["current_result"] = None
    st.session_state["trigger_query"] = False

# Sidebar
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/CARS24_Official_Logo.png/800px-CARS24_Official_Logo.png", width=180)
    st.markdown("### ⚙️ Backend Connection")
    api_url = st.text_input("FastAPI Base URL", value="http://127.0.0.1:8000", help="Address where your FastAPI server is running")

    backend_online = False
    try:
        health_resp = requests.get(f"{api_url}/health", timeout=2)
        if health_resp.status_code == 200 and health_resp.json().get("status") == "ok":
            backend_online = True
            st.success("🟢 Backend Connected (`/health` OK)")
        else:
            st.warning(f"🟡 Backend returned status {health_resp.status_code}")
    except Exception:
        st.error("🔴 Backend Disconnected\n\nRun:\n`python -m uvicorn app.main:app --reload`")

    st.divider()
    st.markdown("### 💡 Quick Prompt Suggestions")
    suggestions = [
        "What orders need attention right now?",
        "Give me a full status summary for order #1.",
        "Customer says they've paid for order #5 but delivery isn't scheduled - what's going on?",
        "What's the payment status for order #3?",
        "Find orders for customer 'Sandra' or phone '620'",
    ]

    for s in suggestions:
        st.button(
            s,
            key=f"btn_{s}",
            use_container_width=True,
            on_click=select_prompt,
            args=(s,)
        )

    st.divider()
    st.markdown(
        """
        **System Mode Info:**
        - **LLM Mode**: Uses Groq Tool Calling when `GROQ_API_KEY` is configured.
        - **Rule-based Mode**: Instant fallback logic even with zero API keys.
        """
    )

# Header
st.markdown('<div class="main-title">🚗 Cars24 AI Operations Copilot</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Natural language operational intelligence for orders, payments, and delivery tracking.</div>', unsafe_allow_html=True)

tab_copilot, tab_orders, tab_test_bench = st.tabs(["🤖 Ops Copilot (Ask Question)", "📦 Order Explorer", "🧪 API Test Bench"])

# TAB 1: Ops Copilot
with tab_copilot:
    st.markdown("#### Ask anything about customer orders, payments, or delivery status")

    query_val = st.text_input(
        "Enter operations question:",
        key="query_input",
        placeholder="e.g., What is the payment and delivery status for order #12?",
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        submit_button = st.button("🚀 Ask Copilot", type="primary", use_container_width=True)
    with col2:
        st.button("🔄 Clear", use_container_width=False, on_click=clear_query)

    # Check if a query was triggered (via button click or sidebar selection)
    should_run = (submit_button or st.session_state.get("trigger_query", False)) and bool(st.session_state.get("query_input", "").strip())

    if should_run:
        st.session_state["trigger_query"] = False
        active_q = st.session_state["query_input"].strip()

        if not backend_online:
            st.error(f"❌ Cannot connect to FastAPI server at `{api_url}`. Make sure Uvicorn is running!")
        else:
            with st.spinner("🤖 Copilot is querying database tools & reasoning..."):
                start_time = time.time()
                try:
                    res = requests.post(
                        f"{api_url}/query",
                        json={"query": active_q},
                        headers={"Content-Type": "application/json"},
                        timeout=20,
                    )
                    duration = round(time.time() - start_time, 2)

                    if res.status_code == 200:
                        data = res.json()
                        st.session_state["current_result"] = {
                            "query": active_q,
                            "answer": data.get("answer", "No answer provided"),
                            "mode": data.get("mode", "unknown"),
                            "data": data.get("data"),
                            "duration": duration,
                        }
                    else:
                        st.error(f"Error {res.status_code}: {res.text}")
                except Exception as ex:
                    st.error(f"Request failed: {str(ex)}")

    # Display result if present
    if st.session_state.get("current_result"):
        res = st.session_state["current_result"]
        st.markdown("---")
        st.markdown(f"**Question:** *{res.get('query')}*")

        mode = res.get("mode", "")
        mode_color = "green" if "llm" in mode.lower() and "fallback" not in mode.lower() else "orange"
        st.caption(f"⚡ Mode: **:{mode_color}[{mode.upper()}]** | ⏱️ Latency: **{res.get('duration', 0)}s**")

        st.markdown("### 📋 Copilot Answer")
        st.markdown(res.get("answer"))

        structured_data = res.get("data")
        if structured_data:
            with st.expander("🔍 View Retrieved Database Data (Underlying Tool Output)", expanded=False):
                st.json(structured_data)

# TAB 2: Order Explorer
with tab_orders:
    st.markdown("#### Real-time Database Orders")
    if not backend_online:
        st.warning("Backend is offline. Start FastAPI to browse orders.")
    else:
        col_limit, col_search, col_btn = st.columns([1, 2, 1])
        with col_limit:
            limit = st.selectbox("Rows to fetch", [10, 20, 50, 100], index=1)
        with col_search:
            search_id = st.text_input("Lookup Specific Order ID (optional)", placeholder="e.g. 1")
        with col_btn:
            st.write("")
            st.write("")
            refresh_orders = st.button("🔄 Refresh Data", use_container_width=True)

        try:
            if search_id.strip():
                order_resp = requests.get(f"{api_url}/orders/{search_id.strip()}", timeout=5)
                if order_resp.status_code == 200:
                    order = order_resp.json()
                    st.success(f"Found Order #{order['id']}")
                    st.json(order)
                elif order_resp.status_code == 404:
                    st.error(f"Order #{search_id} not found.")
                else:
                    st.error(f"Error {order_resp.status_code}: {order_resp.text}")
            else:
                orders_resp = requests.get(f"{api_url}/orders?skip=0&limit={limit}", timeout=5)
                if orders_resp.status_code == 200:
                    orders = orders_resp.json()
                    st.write(f"Showing **{len(orders)}** recent orders:")

                    table_rows = []
                    for o in orders:
                        cust = o.get("customer", {})
                        veh = o.get("vehicle", {})
                        pay = o.get("payment") or {}
                        delv = o.get("delivery") or {}

                        table_rows.append({
                            "Order ID": o["id"],
                            "Customer": cust.get("name", "N/A"),
                            "Phone": cust.get("phone", "N/A"),
                            "Vehicle": f"{veh.get('year', '')} {veh.get('make', '')} {veh.get('model', '')}",
                            "Amount (₹)": f"{o.get('amount', 0):,.2f}",
                            "Order Status": o.get("status", "").upper(),
                            "Payment Status": pay.get("status", "N/A").upper(),
                            "Delivery Status": delv.get("status", "N/A").upper(),
                            "Delivery Partner": delv.get("partner", "Unassigned"),
                        })

                    st.dataframe(table_rows, use_container_width=True)
                else:
                    st.error(f"Failed to fetch orders: {orders_resp.status_code}")
        except Exception as e:
            st.error(f"Failed to connect to backend: {e}")

# TAB 3: API Test Bench
with tab_test_bench:
    st.markdown("#### Fast Diagnostic & Endpoint Testing")
    st.write("Click any endpoint below to verify its status, payload, and response time.")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**1. Health Check**")
        if st.button("Test `GET /health`", use_container_width=True):
            try:
                t0 = time.time()
                r = requests.get(f"{api_url}/health", timeout=3)
                t1 = time.time()
                st.code(f"Status: {r.status_code} ({round((t1-t0)*1000, 1)} ms)\n\n{json.dumps(r.json(), indent=2)}")
            except Exception as err:
                st.error(str(err))

    with c2:
        st.markdown("**2. List Orders**")
        if st.button("Test `GET /orders?limit=5`", use_container_width=True):
            try:
                t0 = time.time()
                r = requests.get(f"{api_url}/orders?skip=0&limit=5", timeout=3)
                t1 = time.time()
                st.code(f"Status: {r.status_code} ({round((t1-t0)*1000, 1)} ms)\n\nFound {len(r.json())} items")
            except Exception as err:
                st.error(str(err))

    with c3:
        st.markdown("**3. Copilot Query**")
        if st.button("Test `POST /query` (ID #1)", use_container_width=True):
            try:
                t0 = time.time()
                payload = {"query": "What's the status of order #1?"}
                r = requests.post(f"{api_url}/query", json=payload, timeout=5)
                t1 = time.time()
                st.code(f"Status: {r.status_code} ({round((t1-t0)*1000, 1)} ms)\n\n{json.dumps(r.json(), indent=2)}")
            except Exception as err:
                st.error(str(err))
