"""
main.py — Entry point for the Pokemon Agent Battle.

Responsibilities:
  - Load environment variables
  - Seed the initial BattleState
  - Invoke the compiled LangGraph
  - Print the final result
"""

import asyncio
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

from graph.battle_graph import build_graph
from graph.state import BattleState


async def main() -> None:
    load_dotenv()

    os.makedirs("logs", exist_ok=True)
    log_file = f"logs/battle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    logger = logging.getLogger(__name__)

    # Seed initial state — LangGraph does not auto-initialize TypedDict fields
    initial_state: BattleState = {
        "team_claude": [],
        "team_gpt": [],
        "current_round": 1,
        "round_results": [],
        "winner": "",
    }

    graph = build_graph()

    logger.info("=" * 60)
    logger.info("   POKEMON AGENT BATTLE: Claude vs GPT")
    logger.info("=" * 60)

    final_state = await graph.ainvoke(initial_state)

    logger.info(f"\nFinal winner stored in state: {final_state['winner']}")
    logger.info(f"Battle log saved to: {log_file}")


if __name__ == "__main__":
    asyncio.run(main())