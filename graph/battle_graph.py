"""
battle_graph.py — Assemble and compile the LangGraph battle graph.

Graph wiring:
  START
    → build_team_claude
    → build_team_gpt
    → battle_round (runs round + increments current_round)
    → [is_battle_over]:
        "continue" → battle_round
        "end"      → result_node
    → END

Usage:
  from graph.battle_graph import build_graph

  graph = build_graph()
  final_state = await graph.ainvoke(initial_state)
"""

from langgraph.graph import StateGraph, START, END

from graph.state import BattleState
from graph.nodes import (
    build_team_claude,
    build_team_gpt,
    battle_round,
    result_node,
)
from graph.edges import is_battle_over


def build_graph() -> StateGraph:
    """
    Build and compile the battle graph.

    Returns a compiled LangGraph ready for ainvoke().
    """
    builder = StateGraph(BattleState)

    # --- Register nodes ---
    builder.add_node("build_team_claude", build_team_claude)
    builder.add_node("build_team_gpt", build_team_gpt)
    builder.add_node("battle_round", battle_round)
    builder.add_node("result_node", result_node)

    # --- Wire edges ---

    # Entry point
    builder.add_edge(START, "build_team_claude")

    # Team building: sequential
    builder.add_edge("build_team_claude", "build_team_gpt")
    builder.add_edge("build_team_gpt", "battle_round")

    # After each round: check if battle is over
    builder.add_conditional_edges(
        "battle_round",
        is_battle_over,
        {
            "continue": "battle_round",
            "end": "result_node",
        },
    )

    # Final node exits graph
    builder.add_edge("result_node", END)

    return builder.compile()
