"""
state.py — BattleState TypedDict

This is the single source of truth that flows through every LangGraph node.
Every node receives the full state and returns a partial update dict.
"""

from typing import TypedDict


class BattleState(TypedDict):
    team_claude: list[dict]       # 5 pokemon dicts with base stats
    team_gpt: list[dict]          # 5 pokemon dicts with base stats
    current_round: int            # 1–5, incremented by next_round node
    round_results: list[dict]     # one dict per completed round
    winner: str                   # "Claude", "GPT", or "Tie"


# round_results entry shape (for reference, not enforced at runtime):
# {
#   "round": int,
#   "stat": str,              # e.g. "speed", "attack"
#   "claude_pokemon": str,
#   "gpt_pokemon": str,
#   "claude_stat_value": int,
#   "gpt_stat_value": int,
#   "winner": str,            # "Claude" | "GPT" | "Tie"
#   "margin_pct": float,      # abs((a-b)/b) * 100
# }
