import requests
import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

def test_backend():
    print(f"Testing Cars24 AI Copilot Backend at {BASE_URL}...\n")

    # 1. Health Check
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=3)
        assert r.status_code == 200, f"Health check failed: {r.status_code}"
        print("[OK] 1. GET /health - OK:", r.json())
    except Exception as e:
        print(f"[FAIL] 1. Health check failed: {e}")
        print("--> Make sure backend is running: python -m uvicorn app.main:app --reload")
        sys.exit(1)

    # 2. List Orders
    try:
        r = requests.get(f"{BASE_URL}/orders?limit=3", timeout=3)
        assert r.status_code == 200
        orders = r.json()
        print(f"[OK] 2. GET /orders - Fetched {len(orders)} sample orders.")
    except Exception as e:
        print(f"[FAIL] 2. GET /orders failed: {e}")

    # 3. Direct Order Lookup
    try:
        r = requests.get(f"{BASE_URL}/orders/1", timeout=3)
        assert r.status_code == 200
        order = r.json()
        print(f"[OK] 3. GET /orders/1 - Customer: {order['customer']['name']}, Status: {order['status']}")
    except Exception as e:
        print(f"[FAIL] 3. GET /orders/1 failed: {e}")

    # 4. Copilot Query: Summary
    queries = [
        "Give me a full status summary for order #1.",
        "Customer says they've paid for order #5 but delivery isn't scheduled - what's going on?",
        "What orders need attention right now?"
    ]

    print("\n[INFO] 4. Testing Copilot /query endpoint:")
    for q in queries:
        try:
            r = requests.post(f"{BASE_URL}/query", json={"query": q}, timeout=10)
            data = r.json()
            print(f"\n   Q: \"{q}\"")
            print(f"   Mode: [{data.get('mode')}]")
            print(f"   Ans: {data.get('answer')}")
        except Exception as e:
            print(f"[FAIL] Query failed for '{q}': {e}")

    print("\n[SUCCESS] All core tests completed successfully!")

if __name__ == "__main__":
    test_backend()
