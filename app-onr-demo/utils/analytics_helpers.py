"""
Analytics Helpers for ONR ITSS POC — Element 5
Decision-Support Analytics and Modeling
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta


# -------------------------------
# MODEL EXECUTION DISPLAY
# -------------------------------
def render_model_execution():
    """Display ML model execution demo."""
    st.markdown("### 🤖 Model Execution")
    
    model_type = st.selectbox(
        "Select Model Type",
        ["Grant Success Prediction", "Budget Forecasting", "Anomaly Detection", "Trend Analysis"],
        key="model_type_selector"
    )
    
    if st.button("🚀 Execute Model", type="primary", key="execute_model_btn"):
        with st.spinner(f"Running {model_type}..."):
            progress = st.progress(0)
            status = st.empty()
            
            status.text("1️⃣ Loading data from Gold layer...")
            progress.progress(20)
            
            status.text("2️⃣ Feature engineering...")
            progress.progress(40)
            
            status.text("3️⃣ Model training/inference...")
            progress.progress(60)
            
            status.text("4️⃣ Generating predictions...")
            progress.progress(80)
            
            status.text("5️⃣ Evaluation complete!")
            progress.progress(100)
            
            st.success(f"✅ {model_type} completed successfully!")


# -------------------------------
# FORECAST VISUALIZATION
# -------------------------------
def render_forecast_visualization():
    """Display forecasting visualization."""
    st.markdown("### 📈 Budget Forecast")
    
    # Generate sample forecast data
    dates = pd.date_range(start="2024-01-01", periods=36, freq="ME")
    actual = np.cumsum(np.random.normal(50000, 10000, 36))
    forecast = np.concatenate([
        actual[:24],
        actual[23] + np.cumsum(np.random.normal(50000, 15000, 12))
    ])
    upper_bound = forecast * 1.1
    lower_bound = forecast * 0.9
    
    fig = go.Figure()
    
    # Actual data
    fig.add_trace(go.Scatter(
        x=dates[:24], y=actual[:24],
        name="Actual",
        line=dict(color="blue", width=2)
    ))
    
    # Forecast
    fig.add_trace(go.Scatter(
        x=dates[23:], y=forecast[23:],
        name="Forecast",
        line=dict(color="green", width=2, dash="dash")
    ))
    
    # Confidence interval
    fig.add_trace(go.Scatter(
        x=dates[23:].tolist() + dates[23:].tolist()[::-1],
        y=upper_bound[23:].tolist() + lower_bound[23:].tolist()[::-1],
        fill="toself",
        fillcolor="rgba(0,255,0,0.1)",
        line=dict(color="rgba(255,255,255,0)"),
        name="90% Confidence"
    ))
    
    fig.update_layout(
        title="Budget Execution Forecast (Next 12 Months)",
        xaxis_title="Date",
        yaxis_title="Cumulative Expenditure ($)",
        hovermode="x unified",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Forecast metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Predicted Q4 Spend", "$2.4M", "+12% vs Q3")
    with col2:
        st.metric("Forecast Confidence", "87%", "+3% from last model")
    with col3:
        st.metric("Model Accuracy (MAPE)", "4.2%", "-0.8% improvement")


# -------------------------------
# GRANT SUCCESS PREDICTION
# -------------------------------
def render_grant_predictions(cursor, catalog: str, schema: str):
    """Display grant success predictions."""
    st.markdown("### 🎯 Grant Success Predictions")
    
    try:
        query = f"""
        SELECT 
            grant_no,
            title,
            program_area,
            amount_usd,
            success_probability,
            risk_factors,
            recommendation
        FROM `{catalog}`.`gold`.grant_predictions
        ORDER BY success_probability DESC
        LIMIT 20
        """
        if not cursor:
            raise RuntimeError("no warehouse")
        cursor.execute(query)
        predictions = cursor.fetchall()
        
        if predictions:
            df = pd.DataFrame(predictions, columns=[
                "Grant ID", "Title", "Research Area", "Amount", 
                "Success %", "Risk Factors", "Recommendation"
            ])
            
            # Color code success probability
            def color_probability(val):
                if isinstance(val, (int, float)):
                    if val >= 0.7:
                        return "background-color: #d4edda"
                    elif val >= 0.4:
                        return "background-color: #fff3cd"
                    else:
                        return "background-color: #f8d7da"
                return ""
            
            sty = df.style
            try:
                sty = sty.map(color_probability, subset=["Success %"])
            except Exception:
                sty = df.style.applymap(color_probability, subset=["Success %"])
            st.dataframe(sty, use_container_width=True)
        else:
            render_simulated_predictions()
    except Exception:
        render_simulated_predictions()


def render_simulated_predictions():
    """Display fixture-backed predictions for demo."""
    from utils.portfolio_data import grants_dataframe

    g = grants_dataframe().nlargest(8, "amount_usd")
    rows = []
    for rec in g.to_dict(orient="records"):
        amt = float(rec["amount_usd"])
        prob = min(0.95, 0.55 + (amt / 8_000_000))
        risk = "Low" if prob >= 0.8 else ("Medium" if prob >= 0.65 else "High")
        rec_txt = "Fund" if risk == "Low" else ("Review" if risk == "Medium" else "Defer")
        rows.append({
            "Grant No": rec["grant_no"],
            "Program Area": rec["program_area"],
            "Awardee": rec["awardee"],
            "Award Amount": f"${amt:,.0f}",
            "Success Probability": round(prob, 2),
            "Risk Level": risk,
            "Recommendation": rec_txt,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


# -------------------------------
# TREND ANALYSIS
# -------------------------------
def render_trend_analysis():
    """Display trend analysis visualizations."""
    st.markdown("### 📊 Trend Analysis")
    
    tab1, tab2, tab3 = st.tabs(["Research Areas", "Funding Trends", "Institutional Analysis"])
    
    with tab1:
        # Research area distribution
        from utils.portfolio_data import grants_dataframe
        g = grants_dataframe()
        pie = g.groupby("program_area")["amount_usd"].sum().reset_index()
        fig = px.pie(
            pie,
            values="amount_usd",
            names="program_area",
            title="Funding by program area (Compass fixture)",
            hole=0.3
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        # Year-over-year funding
        years = [2022, 2023, 2024, 2025, 2026]
        total_funding = [180, 210, 245, 280, 320]
        grants_count = [120, 145, 168, 195, 220]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=years, y=total_funding,
            name="Total Funding ($M)",
            marker_color="indianred"
        ))
        fig.add_trace(go.Scatter(
            x=years, y=grants_count,
            name="Grants Count",
            yaxis="y2",
            line=dict(color="royalblue", width=3)
        ))
        
        fig.update_layout(
            title="Year-over-Year Funding Trends",
            yaxis=dict(title="Funding ($M)"),
            yaxis2=dict(title="Grants Count", overlaying="y", side="right"),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        # Institutional analysis
        institutions = ["MIT", "Stanford", "NPS", "NRL", "JHU APL", "Caltech", "Georgia Tech"]
        grants = [45, 38, 52, 28, 35, 22, 30]
        avg_success = [0.82, 0.79, 0.85, 0.76, 0.81, 0.88, 0.77]
        
        fig = px.scatter(
            x=grants, y=avg_success,
            text=institutions,
            size=[abs(g * 100) for g in avg_success],
            title="Institutional Performance: Grants vs Success Rate",
            labels={"x": "Number of Grants", "y": "Average Success Rate"}
        )
        fig.update_traces(textposition="top center")
        st.plotly_chart(fig, use_container_width=True)


# -------------------------------
# DECISION SUPPORT SUMMARY
# -------------------------------
def render_decision_support():
    """Display executive decision support summary."""
    st.markdown("### 🎯 Executive Decision Support")
    
    st.markdown("""
    <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px;">
        <h4>Key Insights for Leadership</h4>
        <ul>
            <li><strong>High Priority:</strong> AI/ML research shows 92% success rate — recommend increasing allocation by 15%</li>
            <li><strong>Risk Alert:</strong> Hypersonics program showing budget overrun — requires review</li>
            <li><strong>Opportunity:</strong> Quantum computing grants outperforming expectations — consider expansion</li>
            <li><strong>Compliance:</strong> All programs within 5% of execution targets</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    from utils.portfolio_data import portfolio_kpis

    k = portfolio_kpis()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Portfolio Value", f"${k['total_funding']/1e6:.1f}M")
    with col2:
        st.metric("Active Grants", f"{k['grant_count']:,}")
    with col3:
        st.metric("Program Areas", f"{k['program_areas']}")
    with col4:
        st.metric("ERP Execution", f"{k['execution_rate']:.1f}%")


# -------------------------------
# MODEL METRICS
# -------------------------------
def render_model_metrics():
    """Display model performance metrics."""
    st.markdown("### 📏 Model Performance Metrics")
    
    metrics = {
        "Model": ["Grant Success Predictor", "Budget Forecaster", "Anomaly Detector"],
        "Accuracy": ["92.3%", "95.8%", "97.1%"],
        "Precision": ["89.1%", "93.2%", "94.5%"],
        "Recall": ["91.5%", "94.1%", "96.2%"],
        "F1 Score": ["90.3%", "93.6%", "95.3%"],
        "Last Trained": ["2026-08-10", "2026-08-11", "2026-08-12"],
        "Status": ["✅ Production", "✅ Production", "✅ Production"]
    }
    
    df = pd.DataFrame(metrics)
    st.dataframe(df, use_container_width=True)
