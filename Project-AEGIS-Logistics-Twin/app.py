import streamlit as st
import pandas as pd
import plotly.express as px
from aegis_sim import run_simulation
from aegis_opt import optimize_supply_flow

st.set_page_config(page_title="Project AEGIS - Supply Chain Twin", layout="wide")

st.title("🛡️ Project AEGIS: Autonomous Multi-Agent Logistics Twin")
st.caption("Stochastic SimPy Simulation & Dynamic Linear Programming Optimization Engine")

# Sidebar Configuration Controls
st.sidebar.header("Simulation Settings")
sim_duration = st.sidebar.slider("Simulation Horizon (Hours)", 10, 100, 48)
wh1_stock = st.sidebar.number_input("Warehouse 1 Stock", value=80)
wh2_stock = st.sidebar.number_input("Warehouse 2 Stock", value=50)

if st.button("🚀 Run Digital Twin Simulation"):
    df_logs, sc_obj = run_simulation(sim_duration, wh1_stock, wh2_stock)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Fulfilled Units", sc_obj.total_fulfilled)
    col2.metric("Total Unfulfilled Demand", sc_obj.unfulfilled_demand, delta_color="inverse")
    col3.metric("Final WH_1 Stock", sc_obj.warehouses["WH_1"])

    st.subheader("Real-Time Inventory Telemetry")
    fig = px.line(df_logs, x="Time", y=["Stock_WH1", "Stock_WH2", "Unfulfilled"],
                  title="Stochastic Inventory Trajectory Over Time")
    st.plotly_chart(fig, use_container_width=True)

    # Trigger Optimization when unfulfilled demand breaches threshold
    if sc_obj.unfulfilled_demand > 0:
        st.warning("⚠️ Disruption Detected: Unfulfilled Demand Exceeds Target Buffer. Executing MILP Solver...")

        # Inputs for Optimization Solver
        demand = {"Zone_North": 40, "Zone_South": 35}
        capacity = {"WH_1": sc_obj.warehouses["WH_1"], "WH_2": sc_obj.warehouses["WH_2"]}
        costs = {"WH_1": {"Zone_North": 5, "Zone_South": 12},
                 "WH_2": {"Zone_North": 10, "Zone_South": 4}}

        opt_results = optimize_supply_flow(demand, capacity, costs)

        st.success(f"Optimized Re-Routing Solution Calculated! Total Projected Cost: SAR {opt_results['total_cost']}")
        clean_allocations = {f"{w} ➡️ {d}": qty for (w, d), qty in opt_results["allocations"].items()}
        st.json(clean_allocations)
