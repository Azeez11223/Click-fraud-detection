# Model card

AdShield's bundled sample data is synthetic. It does not establish detection quality on real ad traffic. Regenerate the synthetic set with `python data/generate_dataset.py` and train on its fixed, time-ordered splits with `python -m ml.train`. Do not use this model alone to make high-impact decisions.

The offline trainer records the input data SHA-256, feature names, parameters, selected threshold, and holdout metrics in `models/metadata.json`. The serving feature contract includes counts, timing, and basic user-agent flags. Online score, decision, reason codes, and model version are persisted for predictions and event ingestion.

Known limitations: generated data may not represent current bot behavior, geographies, shared networks, or platform-specific traffic. Review blocked events and monitor drift before changing thresholds.
