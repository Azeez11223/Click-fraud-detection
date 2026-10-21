# Project scope compared with commercial click-fraud products

AdShield is an explainable open-source learning prototype for small advertisers. This comparison describes project scope, not vendor rankings or measured performance.

| Area | AdShield MVP | Commercial products may provide |
|---|---|---|
| Explainability | Per-click rules and model feature reasons, score, decision, and model version | Vendor-specific investigation workflows and proprietary risk signals |
| Cost assumptions | Per-campaign CPC and expected conversion value/rate, with a transparent threshold estimate | Vendor-specific pricing, account integrations, and reporting |
| Data scale and validation | Small demo and user-provided data; no validation on real advertiser traffic is claimed | Larger traffic histories and operational feedback loops, depending on vendor |
| Ad-platform operations | No direct Google Ads or Meta account connection; no automatic exclusions | Direct platform integrations and campaign actions may be available, depending on vendor and plan |
| Operation | Self-hosted prototype using FastAPI, Streamlit, and SQLite or PostgreSQL | Vendor-managed service and support arrangements |

Do not infer that AdShield matches a commercial product's detection rate or coverage. Compare current vendor documentation and plans before making a purchasing decision.
