# AdShield portfolio demo

## Three-minute walkthrough

1. Describe AdShield as an explainable, cost-aware click-fraud detection MVP for small advertisers.
2. Start FastAPI and Streamlit using the PowerShell commands in the README, create a local account, and run `python -m data.seed_demo --user-id <id>`.
3. Open the campaign named `[SYNTHETIC DEMO] Click review walkthrough`. Show the decision, score, reason codes, and model version alongside the sample event table.
4. Open the cost assumptions panel and adjust CPC or conversion assumptions. Explain that the recommended threshold follows a transparent cost ratio and the what-if panel uses stored scores and labels as estimates.
5. Close by showing the model card and stating that the sample traffic and labels are synthetic and that real advertiser performance has not been validated.

## Safe project description for a portfolio post

> I built AdShield, an open-source click-fraud detection MVP for small advertisers. It combines explainable rule decisions, an optional XGBoost scoring path, per-campaign cost assumptions, and a Streamlit dashboard. The included demo traffic is synthetic; I have not validated detection rates on real advertiser data, and the project does not connect directly to ad platforms.

Replace this description with your own words and add your repository/demo links after you have published them. Do not report the synthetic demo's output as measured fraud-detection performance.
