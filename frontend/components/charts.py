"""
components/charts.py
Reusable chart-building functions.
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from components.styles import apply_chart_theme


FRAUD_COLOR = "#f87171"
LEGIT_COLOR = "#34d399"
BLUE_COLOR  = "#3b82f6"
CYAN_COLOR  = "#06b6d4"
GOLD_COLOR  = "#fbbf24"


def pie_fraud_legit(fraud: int, legit: int) -> go.Figure:
    """Donut chart: Fraud vs Legitimate distribution."""
    fig = go.Figure(go.Pie(
        labels=["Legitimate", "Fraud"],
        values=[legit, fraud],
        hole=0.62,
        marker=dict(
            colors=[LEGIT_COLOR, FRAUD_COLOR],
            line=dict(color="#050811", width=3),
        ),
        textfont=dict(color="#ffffff", size=12),
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#c9d1e0", family="Inter, sans-serif"),
        showlegend=True,
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#6b7a99", size=12),
            orientation="v",
        ),
        margin=dict(t=20, b=20, l=20, r=20),
        height=300,
        annotations=[dict(
            text=f"<b>{fraud+legit}</b><br><span style='font-size:11px;color:#4b5d7a'>Total</span>",
            x=0.5, y=0.5,
            font=dict(color="#e2e8f5", size=20, family="IBM Plex Mono"),
            showarrow=False,
        )]
    )
    return fig


def line_click_trend(df: pd.DataFrame) -> go.Figure:
    """Line chart showing Fraud vs Legit click trends over time."""
    df = df.copy()
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["minute"] = df["created_at"].dt.floor("min")
    trend = df.groupby(["minute", "result"]).size().reset_index(name="count")

    fig = go.Figure()
    for result, color in [("Legit", LEGIT_COLOR), ("Fraud", FRAUD_COLOR)]:
        sub = trend[trend["result"] == result]
        if not sub.empty:
            fig.add_trace(go.Scatter(
                x=sub["minute"],
                y=sub["count"],
                name=result,
                mode="lines+markers",
                line=dict(color=color, width=2),
                marker=dict(size=6, color=color),
                fill="tozeroy",
                fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.05)",
                hovertemplate="<b>%{x}</b><br>%{y} clicks<extra>" + result + "</extra>",
            ))

    fig = apply_chart_theme(fig, height=300)
    fig.update_layout(
        xaxis_title="",
        yaxis_title="Clicks",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def bar_geo_distribution(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart: fraud counts by geo location."""
    # We use ip_address as proxy data from predictions table
    # but geo would be from clicks_data. We show result counts instead.
    count_df = df.groupby("result").size().reset_index(name="count")

    colors = [FRAUD_COLOR if r == "Fraud" else LEGIT_COLOR for r in count_df["result"]]
    fig = go.Figure(go.Bar(
        x=count_df["count"],
        y=count_df["result"],
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        hovertemplate="<b>%{y}</b>: %{x} clicks<extra></extra>",
    ))
    fig = apply_chart_theme(fig, height=220)
    fig.update_layout(
        xaxis_title="Count",
        yaxis_title="",
        showlegend=False,
        margin=dict(t=10, b=20, l=20, r=20),
    )
    return fig


def gauge_confidence(value: float, is_fraud: bool) -> go.Figure:
    """Gauge chart for fraud probability."""
    color = FRAUD_COLOR if is_fraud else LEGIT_COLOR
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value * 100,
        number={
            "suffix": "%",
            "font": {"color": color, "size": 30, "family": "IBM Plex Mono"},
        },
        gauge={
            "axis": {
                "range": [0, 100],
                "tickcolor": "#2d3a52",
                "tickfont": {"color": "#4b5d7a", "size": 10},
            },
            "bar": {"color": color, "thickness": 0.6},
            "bgcolor": "#0d1229",
            "bordercolor": "rgba(255,255,255,0.06)",
            "borderwidth": 1,
            "steps": [
                {"range": [0, 30],  "color": "rgba(16,185,129,0.06)"},
                {"range": [30, 60], "color": "rgba(251,191,36,0.06)"},
                {"range": [60, 100],"color": "rgba(239,68,68,0.06)"},
            ],
            "threshold": {
                "line": {"color": "#60a5fa", "width": 2},
                "thickness": 0.75,
                "value": 50,
            },
        },
        title={
            "text": "FRAUD PROBABILITY",
            "font": {"color": "#4b5d7a", "size": 11, "family": "IBM Plex Mono"},
        },
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1e0",
        height=220,
        margin=dict(l=20, r=20, t=60, b=10),
    )
    return fig


def radar_model_metrics(metrics: dict) -> go.Figure:
    """Radar chart showing model performance."""
    cats = ["Accuracy", "Precision", "Recall", "F1 Score"]
    vals = [
        metrics.get("accuracy",  0),
        metrics.get("precision", 0),
        metrics.get("recall",    0),
        metrics.get("f1_score",  0),
    ]
    fig = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]],
        theta=cats + [cats[0]],
        fill="toself",
        fillcolor="rgba(59,130,246,0.12)",
        line=dict(color=BLUE_COLOR, width=2.5),
        marker=dict(color=BLUE_COLOR, size=8),
        name="Model Performance",
        hovertemplate="<b>%{theta}</b>: %{r:.1%}<extra></extra>",
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="#0d1229",
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                gridcolor="rgba(255,255,255,0.06)",
                tickfont=dict(color="#4b5d7a", size=9),
                tickformat=".0%",
            ),
            angularaxis=dict(
                gridcolor="rgba(255,255,255,0.06)",
                tickfont=dict(color="#93c5fd", size=12, family="IBM Plex Mono"),
            ),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1e0",
        showlegend=False,
        height=340,
        margin=dict(t=30, b=30, l=40, r=40),
    )
    return fig


def bar_hourly_activity(df: pd.DataFrame) -> go.Figure:
    """Bar chart: predictions grouped by hour of day."""
    df = df.copy()
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["hour"] = df["created_at"].dt.hour

    hourly = df.groupby(["hour", "result"]).size().reset_index(name="count")

    fig = go.Figure()
    for result, color in [("Legit", LEGIT_COLOR), ("Fraud", FRAUD_COLOR)]:
        sub = hourly[hourly["result"] == result]
        if not sub.empty:
            fig.add_trace(go.Bar(
                x=sub["hour"],
                y=sub["count"],
                name=result,
                marker=dict(color=color, opacity=0.85),
                hovertemplate="Hour %{x}:00 — %{y} " + result + " clicks<extra></extra>",
            ))

    fig = apply_chart_theme(fig, height=300)
    fig.update_layout(
        barmode="stack",
        xaxis=dict(title="Hour of Day", tickmode="linear", dtick=2),
        yaxis_title="Count",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def bar_confidence_distribution(df: pd.DataFrame) -> go.Figure:
    """Histogram of confidence scores."""
    fig = go.Figure()
    for result, color in [("Legit", LEGIT_COLOR), ("Fraud", FRAUD_COLOR)]:
        sub = df[df["result"] == result]["confidence"]
        if not sub.empty:
            fig.add_trace(go.Histogram(
                x=sub * 100,
                name=result,
                marker=dict(color=color, opacity=0.75),
                xbins=dict(start=0, end=100, size=5),
                hovertemplate="Confidence %{x:.0f}%: %{y} predictions<extra>" + result + "</extra>",
            ))
    fig = apply_chart_theme(fig, height=280)
    fig.update_layout(
        barmode="overlay",
        xaxis_title="Confidence Score (%)",
        yaxis_title="Count",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig
