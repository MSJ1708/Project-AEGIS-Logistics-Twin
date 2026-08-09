import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
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

# Initialize scenario comparison history
if "scenario_history" not in st.session_state:
    st.session_state.scenario_history = []

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

# Helper Function: Generate PDF Operations Summary
def generate_pdf_report(sim_duration, total_fulfilled, unfulfilled_demand, num_wh, opt_cost, clean_allocs):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    
    # Title Header
    pdf.cell(0, 10, "Project AEGIS: Operations Telemetry Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 10, f"Simulation Horizon: {sim_duration} Hours | Active Nodes: {num_wh}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)
    
    # Key Performance Indicators Table
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "1. Executive Summary KPIs", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f" - Total Units Fulfilled: {total_fulfilled} units", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f" - Unfulfilled Demand Shortage: {unfulfilled_demand} units", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f" - MILP Re-Routing Cost: SAR {opt_cost}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Optimization Allocation
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "2. Optimized Shipment Re-Routing Plan", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    
    if clean_allocs:
        for route, qty in clean_allocs.items():
            pdf.cell(0, 6, f" - Route {route}: {qty} units", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 6, " - No disruptions detected. Operations running within normal safety buffers.", new_x="LMARGIN", new_y="NEXT")
        
    return bytes(pdf.output())


# Run Simulation
if st.sidebar.button("🚀 Run Digital Twin Simulation", use_container_width=True):
    df_logs, sc_obj = run_simulation(sim_duration, wh_inputs)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Fulfilled Units", sc_obj.total_fulfilled)
    col2.metric("Total Unfulfilled Demand", sc_obj.unfulfilled_demand, delta_color="inverse")
    col3.metric("Active Warehouses Configured", len(wh_inputs))

    st.subheader("Real-Time Inventory Telemetry")
    warehouse_columns = list(wh_inputs.keys()) + ["Unfulfilled"]
    fig = px.line(df_logs, x="Time", y=warehouse_columns,
                  title="Stochastic Inventory Trajectory Over Time")
    st.plotly_chart(fig, use_container_width=True)

    opt_total_cost = 0.0
    clean_allocations = {}

    # Trigger Optimization when unfulfilled demand breaches threshold
    if sc_obj.unfulfilled_demand > 0:
        st.warning("⚠️ Disruption Detected: Unfulfilled Demand Exceeds Target Buffer. Executing MILP Solver...")

        st.subheader("⚙️ Interactive Shipping Cost & Zone Demand Matrix")
        
        # Interactive Demand Table
        st.markdown("**1. Edit Target Zone Demand**")
        demand_df = pd.DataFrame([{"Zone_North": 40, "Zone_South": 35}])
        edited_demand = st.data_editor(demand_df, num_rows="fixed", key="demand_editor")
        demand = edited_demand.iloc[0].to_dict()

        # Dynamic Cost Matrix Table based on active warehouses
        st.markdown("**2. Edit Freight Costs per Unit (SAR)**")
        cost_data = {
            "Warehouse": list(wh_inputs.keys()),
            "Zone_North": [5] * len(wh_inputs),
            "Zone_South": [12] * len(wh_inputs)
        }
        cost_df = pd.DataFrame(cost_data)
        edited_costs = st.data_editor(cost_df, key="cost_editor")
        
        costs = {}
        for _, row in edited_costs.iterrows():
            costs[row["Warehouse"]] = {
                "Zone_North": row["Zone_North"],
                "Zone_South": row["Zone_South"]
            }

        capacity = {name: stock for name, stock in sc_obj.warehouses.items()}
        opt_results = optimize_supply_flow(demand, capacity, costs)
        opt_total_cost = opt_results["total_cost"]

        st.success(f"Optimized Re-Routing Solution Calculated! Total Projected Cost: SAR {opt_total_cost}")
        clean_allocations = {f"{w} -> {d}": qty for (w, d), qty in opt_results["allocations"].items()}
        st.json(clean_allocations)

    # Export Report Section
    st.markdown("---")
    st.subheader("📥 Export Operations Reports")
    col_csv, col_pdf = st.columns(2)

    with col_csv:
        csv_data = df_logs.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📄 Download Telemetry Logs (CSV)",
            data=csv_data,
            file_name="aegis_telemetry_logs.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col_pdf:
        pdf_bytes = generate_pdf_report(
            sim_duration,
            sc_obj.total_fulfilled,
            sc_obj.unfulfilled_demand,
            len(wh_inputs),
            opt_total_cost,
            clean_allocations
        )
        st.download_button(
            label="📑 Download Operations Report (PDF)",
            data=pdf_bytes,
            file_name="aegis_operations_report.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    # Automatically log run into Scenario History
    scenario_name = f"Scenario {len(st.session_state.scenario_history) + 1} ({len(wh_inputs)} WHs)"
    st.session_state.scenario_history.append({
        "Scenario": scenario_name,
        "Duration (Hrs)": sim_duration,
        "Active Warehouses": len(wh_inputs),
        "Total Fulfilled": sc_obj.total_fulfilled,
        "Unfulfilled Demand": sc_obj.unfulfilled_demand,
        "Re-Routing Cost (SAR)": opt_total_cost
    })

# Render Scenario Comparison Board
if st.session_state.scenario_history:
    st.markdown("---")
    st.subheader("📊 Scenario Benchmark Comparison (What-If Analysis)")
    
    history_df = pd.DataFrame(st.session_state.scenario_history)
    st.dataframe(history_df, use_container_width=True)

    # Comparative Bar Chart
    comp_fig = px.bar(
        history_df,
        x="Scenario",
        y=["Total Fulfilled", "Unfulfilled Demand"],
        barmode="group",
        title="Fulfillment Performance Across Tested Scenarios"
    )
    st.plotly_chart(comp_fig, use_container_width=True)

    if st.button("🗑️ Clear Scenario Benchmark History"):
        st.session_state.scenario_history = []
        st.rerun()
