"""
generate_dataset.py
Generates a synthetic click fraud dataset matching the required schema.
"""
import numpy as np
import pandas as pd
import os

np.random.seed(42)

def generate_dataset(n=5000, fraud_rate=0.15):
    n_fraud = int(n * fraud_rate)
    n_legit = n - n_fraud

    ip_pool_fraud = [f"192.168.{np.random.randint(0,10)}.{np.random.randint(1,50)}" for _ in range(30)]
    ip_pool_legit = [f"{np.random.randint(1,255)}.{np.random.randint(0,255)}.{np.random.randint(0,255)}.{np.random.randint(1,255)}" for _ in range(3000)]

    devices     = ["mobile", "desktop", "tablet"]
    browsers    = ["Chrome", "Firefox", "Safari", "Edge", "Opera"]
    geolocations = ["US", "IN", "CN", "BR", "RU", "DE", "GB", "FR", "JP", "AU"]

    base_time = pd.Timestamp("2024-01-01")

    # --- Legitimate clicks ---
    legit_ips      = np.random.choice(ip_pool_legit, n_legit)
    legit_devices  = np.random.choice(devices, n_legit, p=[0.6, 0.3, 0.1])
    legit_browsers = np.random.choice(browsers, n_legit, p=[0.5, 0.2, 0.15, 0.1, 0.05])
    legit_timestamps = [base_time + pd.Timedelta(seconds=int(x)) for x in np.random.randint(0, 86400*30, n_legit)]
    legit_intervals  = np.random.exponential(scale=300, size=n_legit).clip(5, 3600)
    legit_ip_counts  = np.random.randint(1, 20, n_legit)
    legit_geo        = np.random.choice(geolocations, n_legit)

    # --- Fraudulent clicks ---
    fraud_ips      = np.random.choice(ip_pool_fraud, n_fraud)
    fraud_devices  = np.random.choice(devices, n_fraud, p=[0.7, 0.25, 0.05])
    fraud_browsers = np.random.choice(browsers, n_fraud, p=[0.6, 0.15, 0.1, 0.1, 0.05])
    # Fraud often happens at night
    night_offsets  = np.concatenate([np.random.randint(0, 21600, n_fraud//2),
                                     np.random.randint(75600, 86400, n_fraud - n_fraud//2)])
    fraud_timestamps = [base_time + pd.Timedelta(days=int(d), seconds=int(s))
                        for d, s in zip(np.random.randint(0,30,n_fraud), night_offsets)]
    fraud_intervals  = np.random.exponential(scale=2, size=n_fraud).clip(0.1, 30)  # Very fast
    fraud_ip_counts  = np.random.randint(50, 500, n_fraud)                          # High counts
    fraud_geo        = np.random.choice(geolocations, n_fraud, p=[0.05,0.3,0.25,0.05,0.1,0.05,0.05,0.05,0.05,0.05])

    legit_df = pd.DataFrame({
        "ip_address":    legit_ips,
        "device_type":   legit_devices,
        "browser":       legit_browsers,
        "timestamp":     legit_timestamps,
        "click_interval": legit_intervals,
        "ip_click_count": legit_ip_counts,
        "geo_location":  legit_geo,
        "is_fraud":      0,
    })
    fraud_df = pd.DataFrame({
        "ip_address":    fraud_ips,
        "device_type":   fraud_devices,
        "browser":       fraud_browsers,
        "timestamp":     fraud_timestamps,
        "click_interval": fraud_intervals,
        "ip_click_count": fraud_ip_counts,
        "geo_location":  fraud_geo,
        "is_fraud":      1,
    })

    df = pd.concat([legit_df, fraud_df], ignore_index=True).sample(frac=1, random_state=42).reset_index(drop=True)
    df["timestamp"] = df["timestamp"].astype(str)
    return df


if __name__ == "__main__":
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    df = generate_dataset()
    out = os.path.join(os.path.dirname(__file__), "dataset.csv")
    df.to_csv(out, index=False)
    print(f"[OK] Dataset saved -> {out}")
    print(df["is_fraud"].value_counts())
    print(f"Fraud rate: {df['is_fraud'].mean()*100:.1f}%")
