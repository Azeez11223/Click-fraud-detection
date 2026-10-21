"""
generate_dataset.py
Generates a synthetic click fraud dataset matching the required schema.
"""
import os

import numpy as np
import pandas as pd

np.random.seed(42)

def generate_dataset(n=5000, fraud_rate=0.15):
    n_fraud = int(n * fraud_rate)
    n_legit = n - n_fraud

    # Both classes use shared and rotating address pools; address uniqueness is not a label.
    ip_pool_fraud = [f"198.51.{i // 250}.{i % 250 + 1}" for i in range(1000)]
    ip_pool_legit = [f"203.0.{i // 250}.{i % 250 + 1}" for i in range(1000)]

    devices     = ["mobile", "desktop", "tablet"]
    browsers    = ["Chrome", "Firefox", "Safari", "Edge", "Opera"]
    geolocations = ["US", "IN", "CN", "BR", "RU", "DE", "GB", "FR", "JP", "AU"]

    base_time = pd.Timestamp("2024-01-01")

    # --- Legitimate clicks ---
    legit_ips      = np.random.choice(ip_pool_legit[:180], n_legit)
    legit_devices  = np.random.choice(devices, n_legit, p=[0.6, 0.3, 0.1])
    legit_browsers = np.random.choice(browsers, n_legit, p=[0.5, 0.2, 0.15, 0.1, 0.05])
    legit_days = np.random.randint(0, 30, n_legit)
    legit_timestamps = [base_time + pd.Timedelta(days=int(d), seconds=int(x)) for d, x in zip(legit_days, np.random.randint(0, 86400, n_legit), strict=False)]
    legit_intervals = np.where(np.random.random(n_legit) < .82,
        np.random.exponential(scale=180, size=n_legit), np.random.exponential(scale=8, size=n_legit)).clip(0.2, 3600)
    legit_ip_counts = np.where(np.random.random(n_legit) < .72,
        np.random.randint(1, 12, n_legit), np.random.randint(12, 90, n_legit))
    legit_geo        = np.random.choice(geolocations, n_legit)

    # --- Fraudulent clicks ---
    fraud_ips      = np.random.choice(ip_pool_fraud, n_fraud)
    fraud_devices  = np.random.choice(devices, n_fraud, p=[0.7, 0.25, 0.05])
    fraud_browsers = np.random.choice(browsers, n_fraud, p=[0.6, 0.15, 0.1, 0.1, 0.05])
    # Fraud often happens at night
    night_offsets  = np.concatenate([np.random.randint(0, 21600, n_fraud//2),
                                     np.random.randint(75600, 86400, n_fraud - n_fraud//2)])
    fraud_days = np.random.randint(0, 30, n_fraud)
    fraud_timestamps = [base_time + pd.Timedelta(days=int(d), seconds=int(s))
                        for d, s in zip(fraud_days, night_offsets, strict=False)]
    # Some bots are low-and-slow while others burst; the feature ranges overlap legit traffic.
    fraud_intervals = np.where(np.random.random(n_fraud) < .58,
        np.random.exponential(scale=3, size=n_fraud), np.random.exponential(scale=240, size=n_fraud)).clip(0.2, 3600)
    fraud_ip_counts = np.where(np.random.random(n_fraud) < .45,
        np.random.randint(2, 18, n_fraud), np.random.randint(18, 100, n_fraud))
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

    df = pd.concat([legit_df, fraud_df], ignore_index=True)
    # A small amount of label noise and a late-period shift prevent a perfect proxy rule.
    noise = np.random.choice(df.index, size=max(1, int(len(df) * 0.04)), replace=False)
    df.loc[noise, "is_fraud"] = 1 - df.loc[noise, "is_fraud"]
    late = pd.to_datetime(df["timestamp"]) >= base_time + pd.Timedelta(days=20)
    df.loc[late & (df["is_fraud"] == 0), "click_interval"] *= 0.75
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
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
