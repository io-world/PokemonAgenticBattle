"""
main.py — Entry point for the Pokemon Agent Battle.

Responsibilities:
  - Load environment variables
  - Seed the initial BattleState
  - Invoke the compiled LangGraph
  - Print the final result
"""

import asyncio
from dotenv import load_dotenv

from graph.battle_graph import build_graph
from graph.state import BattleState


async def main() -> None:
    load_dotenv()

    # Seed initial state — LangGraph does not auto-initialize TypedDict fields
    initial_state: BattleState = {
        "team_claude": [],
        "team_gpt": [],
        "current_round": 1,
        "round_results": [],
        "winner": "",
    }

    graph = build_graph()

    print("=" * 60)
    print("   POKEMON AGENT BATTLE: Claude vs GPT")
    print("=" * 60)

    final_state = await graph.ainvoke(initial_state)

    print(f"\nFinal winner stored in state: {final_state['winner']}")


if __name__ == "__main__":
    asyncio.run(main())