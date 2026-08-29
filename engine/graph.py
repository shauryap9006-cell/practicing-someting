"""RailTwin-X Corridor Graph & SimPy Resource Mapping.

Builds NetworkX topology of the corridor and binds each physical section to
SimPy PriorityResources (for single-line bottlenecks) and Resources (for stations).
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple
import networkx as nx
import simpy

from data.db import Database, get_db


class CorridorGraph:
    """NetworkX railway corridor graph mapped to discrete-event simulation resources."""

    def __init__(self, env: simpy.Environment, db: Optional[Database] = None):
        self.env = env
        self.db = db or get_db()
        self.graph = nx.DiGraph()
        self.section_resources: Dict[Tuple[str, str], simpy.PriorityResource | simpy.Resource] = {}
        self.platform_resources: Dict[str, simpy.Resource] = {}
        self._build_graph()

    def _build_graph(self) -> None:
        """Loads physical stations, sections, and builds SimPy capacity constraints."""
        with self.db.transaction() as cur:
            # 1. Load Stations & Platform resources
            cur.execute("SELECT code, name, is_junction, platforms FROM stations")
            stations = cur.fetchall()
            for stn in stations:
                code = stn["code"]
                self.graph.add_node(
                    code,
                    name=stn["name"],
                    is_junction=stn["is_junction"],
                    platforms=stn["platforms"],
                )
                self.platform_resources[code] = simpy.Resource(self.env, capacity=stn["platforms"])

            # 2. Load Sections & Priority/Standard Resources
            cur.execute("SELECT from_code, to_code, distance_km, single_line, max_speed_kmph FROM sections")
            sections = cur.fetchall()

            for sec in sections:
                u, v = sec["from_code"], sec["to_code"]
                is_single = bool(sec["single_line"])
                dist = float(sec["distance_km"])
                max_spd = int(sec["max_speed_kmph"])

                self.graph.add_edge(
                    u, v,
                    distance_km=dist,
                    single_line=is_single,
                    max_speed_kmph=max_spd,
                )

                # For single-line sections, both directions share ONE PriorityResource(capacity=1)
                if is_single:
                    pair_key = tuple(sorted([u, v]))
                    if pair_key not in self.section_resources:
                        shared_res = simpy.PriorityResource(self.env, capacity=1)
                        self.section_resources[(u, v)] = shared_res
                        self.section_resources[(v, u)] = shared_res
                else:
                    # Double line: separate resource per direction
                    self.section_resources[(u, v)] = simpy.Resource(self.env, capacity=1)

    def get_section_resource(self, from_stn: str, to_stn: str) -> simpy.Resource:
        """Returns the SimPy resource governing transit between two adjacent stations."""
        key = (from_stn, to_stn)
        if key not in self.section_resources:
            # Fallback standard resource
            self.section_resources[key] = simpy.Resource(self.env, capacity=1)
        return self.section_resources[key]

    def get_platform_resource(self, station_code: str) -> simpy.Resource:
        """Returns platform capacity resource for a station."""
        return self.platform_resources.get(station_code, simpy.Resource(self.env, capacity=2))


if __name__ == "__main__":
    print("=== Corridor Graph Demo ===")
    env = simpy.Environment()
    cg = CorridorGraph(env)
    print(f"Graph loaded with {len(cg.graph.nodes)} stations and {len(cg.graph.edges)} track sections.")
