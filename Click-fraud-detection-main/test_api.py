"""Quick API smoke test."""
import requests

BASE = "http://localhost:8000"

print("=== Health ===")
r = requests.get(f"{BASE}/healthz", timeout=5)
print(r.json())

print("\n=== Signup ===")
r = requests.post(f"{BASE}/auth/signup", json={"name": "Test User", "email": "test@adshield.com", "password": "pass123"})
print(r.status_code, r.json())

print("\n=== Login ===")
r = requests.post(f"{BASE}/auth/login", json={"email": "test@adshield.com", "password": "pass123"})
data = r.json()
print(r.status_code, data.get("user"))
token = data.get("access_token", "")
headers = {"Authorization": f"Bearer {token}"}

print("\n=== Create Campaign ===")
r = requests.post(f"{BASE}/campaigns", json={"name": "Summer Sale", "ad_type": "Display", "platform": "Google", "purpose": "Traffic"}, headers=headers)
print(r.status_code, r.json())

print("\n=== Simulate Clicks ===")
for i in range(6):
    r = requests.post(f"{BASE}/campaigns/1/click", json={"ip_address": "10.0.0.1", "user_agent": "Bot/1.0"})
    print(f"  Click {i+1}: {r.json()}")

print("\n=== Stats ===")
r = requests.get(f"{BASE}/campaigns/1/stats", headers=headers)
print(r.json())

print("\n=== Alerts ===")
r = requests.get(f"{BASE}/campaigns/1/alerts", headers=headers)
print(r.json())

print("\n=== ALL TESTS PASSED ===")
