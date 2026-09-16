"""
nodes.py — All LangGraph node functions for the Pokemon battle graph.

Node inventory:
  build_team_claude  — Claude agent picks and hydrates Team A via MCP
  build_team_gpt     — GPT agent picks and hydrates Team B via MCP
  battle_round       — Runs one stat duel between the active Pokemon per side
  hype_node          — Flavor commentary from the winning team's LLM
  next_round         — Increments current_round (pure state bump)
  result_node        — Tallies rounds, writes final winner to state

Design rules:
  - Each node takes BattleState and returns a dict (partial state update)
  - MCP client contexts are opened and closed inside the node — not shared
  - Nodes are async because MCP calls are async
  - No side effects outside of state updates and stdout logging
"""

import logging

from fastmcp import Client

from graph.state import BattleState
from agents.agent_claude import ClaudeAgent
from agents.agent_gpt import GPTAgent

logger = logging.getLogger(__name__)

MCP_URL = "http://localhost:8000/mcp"

# ---------------------------------------------------------------------------
# Round stat rotation
# Each round tests a different stat dimension. 5 rounds = 5 stats.
# ---------------------------------------------------------------------------

ROUND_STATS: dict[int, tuple[str, str | None]] = {
    1: ("speed", None),                    # higher speed wins
    2: ("attack", "defense"),              # attack vs opponent's defense
    3: ("special-attack", "special-defense"),
    4: ("hp", None),                       # raw HP comparison
    5: ("attack", "speed"),                # attack + speed sum (power round)
}


def _get_stat(pokemon: dict, stat_name: str) -> int:
    """Safe stat accessor — returns 0 if stat key missing."""
    return pokemon.get(stat_name, 0)


def _compute_round_result(
    round_num: int,
    claude_mon: dict,
    gpt_mon: dict,
) -> dict:
    """
    Compute the winner for a single round based on the stat rotation.

    For offensive vs defensive matchups (e.g. attack vs defense),
    the attacker wins if their attack exceeds the defender's defense.
    For symmetric matchups, higher raw stat wins.

    Returns a round_result dict.
    """
    stat_a_name, stat_b_name = ROUND_STATS[round_num]

    claude_val = _get_stat(claude_mon, stat_a_name)
    gpt_val = _get_stat(gpt_mon, stat_a_name if stat_b_name is None else stat_b_name)

    if stat_b_name is None:
        # Symmetric: both use same stat
        gpt_val = _get_stat(gpt_mon, stat_a_name)

    if claude_val > gpt_val:
        round_winner = "Claude"
    elif gpt_val > claude_val:
        round_winner = "GPT"
    else:
        round_winner = "Tie"

    margin_pct = (
        abs(claude_val - gpt_val) / max(gpt_val, 1) * 100
    )

    stat_label = stat_a_name if stat_b_name is None else f"{stat_a_name} vs {stat_b_name}"

    return {
        "round": round_num,
        "stat": stat_label,
        "claude_pokemon": claude_mon["name"],
        "gpt_pokemon": gpt_mon["name"],
        "claude_stat_value": claude_val,
        "gpt_stat_value": gpt_val,
        "winner": round_winner,
        "margin_pct": round(margin_pct, 1),
    }


# ---------------------------------------------------------------------------
# Node: build_team_claude
# ---------------------------------------------------------------------------

async def build_team_claude(state: BattleState) -> dict:
    """
    Claude agent opens its own MCP client, picks 5 Pokemon, hydrates stats.
    Writes result to state["team_claude"].
    """
    logger.info("\n[Node] build_team_claude — Claude is selecting its team...")

    async with Client(MCP_URL) as mcp_client:
        agent = ClaudeAgent(mcp_client=mcp_client)
        team = await agent.build_team()

    logger.info(f"[Node] build_team_claude — Team built: {[p['name'] for p in team]}")
    return {"team_claude": team}


# ---------------------------------------------------------------------------
# Node: build_team_gpt
# ---------------------------------------------------------------------------

async def build_team_gpt(state: BattleState) -> dict:
    """
    GPT agent opens its own MCP client, picks 5 Pokemon, hydrates stats.
    Writes result to state["team_gpt"].
    Option B: separate Client instance from Claude's — never shared.
    """
    logger.info("\n[Node] build_team_gpt — GPT is selecting its team...")

    async with Client(MCP_URL) as mcp_client:
        agent = GPTAgent(mcp_client=mcp_client)
        team = await agent.build_team()

    logger.info(f"[Node] build_team_gpt — Team built: {[p['name'] for p in team]}")
    return {"team_gpt": team}


# ---------------------------------------------------------------------------
# Node: battle_round
# ---------------------------------------------------------------------------

async def battle_round(state: BattleState) -> dict:
    """
    Run one stat duel for the current round and advance to the next.

    Pokemon are matched by index: round N uses pokemon[N-1] from each team.
    Appends a round_result dict to state["round_results"] and increments current_round.
    """
    logger.info("-" * 50)
    round_num = state["current_round"]
    idx = round_num - 1  # 0-indexed

    claude_mon = state["team_claude"][idx]
    gpt_mon = state["team_gpt"][idx]

    logger.info(f"\n[Node] battle_round {round_num} — {claude_mon['name']} vs {gpt_mon['name']}")

    result = _compute_round_result(round_num, claude_mon, gpt_mon)

    logger.info(
        f"[Node] battle_round {round_num} — "
        f"Stat: {result['stat']} | "
        f"Claude {result['claude_stat_value']} vs GPT {result['gpt_stat_value']} | "
        f"Winner: {result['winner']} (margin {result['margin_pct']}%)"
    )

    new_round = round_num + 1
    logger.info(f"[Node] battle_round — advancing to round {new_round}")

    return {
        "round_results": state.get("round_results", []) + [result],
        "current_round": new_round,
    }


# ---------------------------------------------------------------------------
# Node: result_node
# ---------------------------------------------------------------------------

async def result_node(state: BattleState) -> dict:
    """
    Tally the 5 round results and declare the overall winner.
    Writes state["winner"] and prints a final summary.
    """
    results = state["round_results"]
    claude_wins = sum(1 for r in results if r["winner"] == "Claude")
    gpt_wins = sum(1 for r in results if r["winner"] == "GPT")
    ties = sum(1 for r in results if r["winner"] == "Tie")

    if claude_wins > gpt_wins:
        winner = "Claude"
    elif gpt_wins > claude_wins:
        winner = "GPT"
    else:
        winner = "Tie"

    logger.info("\n" + "=" * 60)
    logger.info("BATTLE COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Claude wins: {claude_wins}  |  GPT wins: {gpt_wins}  |  Ties: {ties}")
    logger.info(f"OVERALL WINNER: {winner}")
    logger.info("=" * 60)

    return {"winner": winner}
