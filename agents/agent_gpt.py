"""
agent_gpt.py — Team B agent powered by GPT-4 (OpenAI).

Responsibilities:
  1. Use its own FastMCP client connection to call get_pokemon_stats()
  2. Ask GPT-4 to pick 5 Pokemon names with personality/strategy reasoning
  3. Hydrate each name with real stats from PokeAPI via MCP
  4. Expose build_team() and generate_hype() as the public interface

Design notes:
  - This agent owns MCP Client B exclusively (Option B topology)
  - Structurally mirrors ClaudeAgent — same interface, different LLM backend
  - generate_hype() narrates Team B wins only
  - GPT and Claude never share MCP client state
"""

import json
import re
from typing import Any

import openai
from fastmcp import Client

try:
    from agents.config import chatgpt_api_key
except ImportError:
    from config import chatgpt_api_key


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL = "gpt-4o"

TEAM_SELECTION_PROMPT = """\
You are the Team B Pokemon strategist. Your job is to pick 5 Pokemon for battle.

Rules:
- Pick exactly 5 Pokemon
- You may ONLY choose from the original 151 Pokemon (Generation 1: Bulbasaur through Mew)
- Choose a balanced team with variety (speed, attack, defense, special)
- Be strategic and a little boastful — you're competing against Claude's team
- Return ONLY a JSON object with this exact shape, no extra text:
  {"team": ["pokemon1", "pokemon2", "pokemon3", "pokemon4", "pokemon5"], "strategy": "brief strategy note"}
- Use lowercase Pokemon names exactly as they appear in PokeAPI (e.g. "pikachu", "charizard")
- No regional variants like "pikachu-original" — use base names only
"""


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------

class GPTAgent:
    """
    Team B agent. Uses GPT-4 to pick Pokemon and generate hype commentary.
    Owns its own MCP client connection (Option B topology).
    """

    def __init__(self, mcp_client: Client, api_key: str | None = None) -> None:
        """
        Args:
            mcp_client: A FastMCP Client already configured for the pokeapi server.
                        Caller is responsible for entering the async context manager.
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.
        """
        self.mcp_client = mcp_client
        self.openai = openai.OpenAI(api_key=api_key or chatgpt_api_key)
        self.team_name = "GPT"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def build_team(self) -> list[dict[str, Any]]:
        """
        Ask GPT to pick 5 Pokemon, then hydrate each with real stats via MCP.

        Returns:
            List of 5 dicts, each with: name, hp, attack, defense,
            special-attack, special-defense, speed
        """
        # Step 1: Ask GPT to pick team names
        names, strategy = self._pick_team_names()
        print(f"[GPT Agent] Team selected: {names}")
        print(f"[GPT Agent] Strategy: {strategy}")

        # Step 2: Hydrate with real stats from PokeAPI via MCP
        team: list[dict[str, Any]] = []
        for name in names:
            stats = await self._fetch_stats(name)
            team.append(stats)
            print(f"[GPT Agent] Fetched stats for {stats['name']}: speed={stats['speed']}, attack={stats['attack']}")

        return team

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _pick_team_names(self) -> tuple[list[str], str]:
        """
        Call GPT-4 to pick 5 Pokemon names.

        Returns:
            Tuple of (list of 5 names, strategy description)
        """
        response = self.openai.chat.completions.create(
            model=MODEL,
            max_tokens=300,
            response_format={"type": "json_object"},  # GPT-4o supports JSON mode
            messages=[{"role": "user", "content": TEAM_SELECTION_PROMPT}],
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if present (shouldn't happen in JSON mode, but defensive)
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()

        try:
            parsed = json.loads(raw)
            names: list[str] = parsed["team"]
            strategy: str = parsed.get("strategy", "")
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(
                f"GPT returned invalid team JSON: {e}\nRaw response:\n{raw}"
            ) from e

        if len(names) != 5:
            raise ValueError(f"GPT returned {len(names)} Pokemon, expected 5. Names: {names}")

        return [n.strip().lower() for n in names], strategy

    async def _fetch_stats(self, name: str) -> dict[str, Any]:
        """
        Fetch a single Pokemon's stats via MCP (PokeAPI under the hood).

        Raises:
            RuntimeError: if MCP call returns an error
        """
        result = await self.mcp_client.call_tool("get_pokemon_stats", {"name": name})

        if result.is_error:
            raise RuntimeError(
                f"MCP error fetching stats for '{name}': {result.data}"
            )

        return result.data


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

async def _test() -> None:
    """Quick smoke test — requires PokeAPI MCP server running on localhost:8000."""
    async with Client("http://localhost:8000/mcp") as client:
        agent = GPTAgent(mcp_client=client)
        team = await agent.build_team()
        print("\n=== GPT's Team ===")
        for p in team:
            print(f"  {p['name']}: HP={p['hp']} ATK={p['attack']} SPD={p['speed']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(_test())