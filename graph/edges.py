"""
edges.py — Conditional edge logic for the Pokemon battle graph.

One decision point:
  1. is_battle_over(state) — fires after battle_round
     Checks: have we completed all 5 rounds?
     Returns: "continue" | "end"
"""

from graph.state import BattleState

TOTAL_ROUNDS = 5


def is_battle_over(state: BattleState) -> str:
    """
    Check if all rounds have been completed.

    current_round is already incremented by battle_round before this edge runs,
    so we check if it exceeds TOTAL_ROUNDS.

    Returns "continue" or "end".
    """
    if state["current_round"] > TOTAL_ROUNDS:
        print(f"[Edge] is_battle_over → end (completed {TOTAL_ROUNDS} rounds)")
        return "end"

    print(f"[Edge] is_battle_over → continue (starting round {state['current_round']})")
    return "continue"
