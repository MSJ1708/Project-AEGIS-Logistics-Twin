import streamlit as st
import pandas as pd
import plotly.express as px
from aegis_sim import run_simulation
from aegis_opt import optimize_supply_flow

st.set_page_config(page_title="Project AEGIS - Supply Chain Twin", layout="wide")

st.title("🛡️ Project AEGIS: Autonomous Multi-Agent Logistics Twin")
st.caption("Stochastic SimPy Simulation & Dynamic Linear Programming Optimization Engine")

# Initialize dynamic warehouse state
if "warehouses" not in st.session_state:
    st.session_state.warehouses = [
        {"name": "WH_1", "stock": 80},
        {"name": "WH_2", "stock": 50}
    ]

# Sidebar Controls
st.sidebar.header("Simulation Settings")
sim_duration = st.sidebar.slider("Simulation Horizon (Hours)", 10, 100, 48)

st.sidebar.subheader("Warehouse Management")

# Form to add a new custom warehouse
with st.sidebar.form("add_wh_form", clear_on_submit=True):
    new_wh_name = st.text_input("New Warehouse Name", placeholder="e.g., WH_Riyadh")
    new_wh_stock = st.number_input("Initial Stock", min_value=0, value=50, step=10)
    add_btn = st.form_submit_button("➕ Add Warehouse")
    
    if add_btn:
        if new_wh_name.strip():
            st.session_state.warehouses.append({"name": new_wh_name.strip(), "stock": int(new_wh_stock)})
            st.rerun()
        else:
            st.sidebar.error("Warehouse name cannot be empty!")

# Display and edit current warehouses in sidebar
wh_inputs = {}
st.sidebar.markdown("---")
st.sidebar.markdown("**Active Warehouses:**")

for idx, wh in enumerate(st.session_state.warehouses):
    col_wh, col_del = st.sidebar.columns([4, 1])
    with col_wh:
        wh_inputs[wh["name"]] = st.number_input(
            f"{wh['name']} Initial Stock",
            min_value=0,
            value=wh["stock"],
            key=f"wh_stock_{idx}"
        )
    with col_del:
        st.write("") # spacing
        if st.button("❌", key=f"del_{idx}"):
            if len(st.session_state.warehouses) > 1:
                st.session_state.warehouses.pop(idx)
                st.rerun()
            else:
                st.sidebar.warning("At least 1 warehouse is required!")

# Run Simulation
if st.sidebar.button("🚀 Run Digital Twin Simulation", use_container_width=True):
    # For now, pass first two warehouse values to run_simulation
    wh_names = list(wh_inputs.keys())
    wh1_val = wh_inputs[wh_names[0]]
    wh2_val = wh_inputs[wh_names[1]] if len(wh_names) > 1 else 0
    
    df_logs, sc_obj = run_simulation(sim_duration, wh1_val, wh2_val)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Fulfilled Units", sc_obj.total_fulfilled)
    col2.metric("Total Unfulfilled Demand", sc_obj.unfulfilled_demand, delta_color="inverse")
    col3.metric("Active Warehouses Configured", len(wh_inputs))

    st.subheader("Real-Time Inventory Telemetry")
    fig = px.line(df_logs, x="Time", y=["Stock_WH1", "Stock_WH2", "Unfulfilled"],
                  title="Stochastic Inventory Trajectory Over Time")
    st.plotly_chart(fig, use_container_width=True)

    # Trigger Optimization when unfulfilled demand breaches threshold
    if sc_obj.unfulfilled_demand > 0:
        st.warning("⚠️ Disruption Detected: Unfulfilled Demand Exceeds Target Buffer. Executing MILP Solver...")

        # Dynamic Capacity Dict built from user's custom warehouses
        demand = {"Zone_North": 40, "Zone_South": 35}
        capacity = {name: stock for name, stock in wh_inputs.items()}
        
        # Build default routing costs for all dynamic warehouses
        costs = {}
        for name in wh_inputs.keys():
            costs[name] = {"Zone_North": 8, "Zone_South": 6}

        opt_results = optimize_supply_flow(demand, capacity, costs)

        st.success(f"Optimized Re-Routing Solution Calculated! Total Projected Cost: SAR {opt_results['total_cost']}")
        clean_allocations = {f"{w} ➡️ {d}": qty for (w, d), qty in opt_results["allocations"].items()}
        st.json(clean_allocations)
