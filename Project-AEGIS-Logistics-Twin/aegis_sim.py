import simpy
import random
import pandas as pd

class SupplyChainEnv:
    def __init__(self, env, warehouses_config):
        self.env = env
        # Accepts a dictionary of warehouses and their initial stocks
        self.warehouses = warehouses_config.copy()
        self.unfulfilled_demand = 0
        self.total_fulfilled = 0
        self.logs = []

    def log_event(self, event_type, details):
        log_entry = {
            "Time": self.env.now,
            "Event": event_type,
            "Details": str(details),
            "Unfulfilled": self.unfulfilled_demand
        }
        # Dynamically record current stock level for EVERY configured warehouse
        for wh_name, stock in self.warehouses.items():
            log_entry[wh_name] = stock

        self.logs.append(log_entry)

    def demand_generator(self, warehouse_id, arrival_rate=2):
        while True:
            # Stochastic inter-arrival times
            yield self.env.timeout(random.expovariate(1.0 / arrival_rate))
            order_qty = random.randint(5, 25)

            if self.warehouses.get(warehouse_id, 0) >= order_qty:
                self.warehouses[warehouse_id] -= order_qty
                self.total_fulfilled += order_qty
                self.log_event("ORDER_FULFILLED", f"{order_qty} units from {warehouse_id}")
            else:
                current_stock = self.warehouses.get(warehouse_id, 0)
                shortage = order_qty - current_stock
                self.total_fulfilled += current_stock
                self.warehouses[warehouse_id] = 0
                self.unfulfilled_demand += shortage
                self.log_event("STOCKOUT_DISRUPTION", f"Shortage of {shortage} units at {warehouse_id}")

    def replenish_process(self, warehouse_id, qty, lead_time_mean=5):
        # Simulated variable supply chain lead time
        actual_lead_time = max(1, random.normalvariate(lead_time_mean, 1.5))
        yield self.env.timeout(actual_lead_time)
        self.warehouses[warehouse_id] = self.warehouses.get(warehouse_id, 0) + qty
        self.log_event("REPLENISHMENT_ARRIVED", f"{qty} units added to {warehouse_id}")


def run_simulation(simulation_time=50, warehouses_config=None):
    if warehouses_config is None:
        warehouses_config = {"WH_1": 100, "WH_2": 100}

    env = simpy.Environment()
    sc = SupplyChainEnv(env, warehouses_config)

    # Dynamically spawn a SimPy demand process for every warehouse in config
    for wh_name in warehouses_config.keys():
        env.process(sc.demand_generator(wh_name, arrival_rate=random.uniform(2, 4)))

    env.run(until=simulation_time)
    return pd.DataFrame(sc.logs), sc
