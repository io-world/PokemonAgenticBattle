"""
agent_claude.py — Team A agent powered by Claude (Anthropic).

Responsibilities:
  1. Use its own FastMCP client connection to call get_pokemon_stats()
  2. Ask Claude to pick 5 Pokemon names with personality/strategy reasoning
  3. Hydrate each name with real stats from PokeAPI via MCP
  4. Expose build_team() and generate_hype() as the public interface

Design notes:
  - This agent owns MCP Client A exclusively (Option B topology)
  - The MCP client is passed in at construction — no global state
  - build_team() is async because MCP calls are async
  - generate_hype() narrates Team A wins only
"""

import json
import re
from typing import Any

import anthropic
from fastmcp import Client




# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL = "claude-opus-4-5"

TEAM_SELECTION_PROMPT = """\
You are the Team A Pokemon strategist. Your job is to pick 5 Pokemon for battle.

Rules:
- Pick exactly 5 Pokemon
- You may ONLY choose from the original 151 Pokemon (Generation 1: Bulbasaur through Mew)
- Choose a balanced team with variety (speed, attack, defense, special)
- Be strategic and a little boastful — you're competing against GPT's team
- Return ONLY a JSON object with this exact shape, no extra text:
  {{"team": ["pokemon1", "pokemon2", "pokemon3", "pokemon4", "pokemon5"], "strategy": "brief strategy note"}}
- Use lowercase Pokemon names exactly as they appear in PokeAPI (e.g. "pikachu", "charizard")
- No regional variants like "pikachu-original" — use base names only
"""


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------

class ClaudeAgent:
    """
    Team A agent. Uses Claude to pick Pokemon and generate hype commentary.
    Owns its own MCP client connection (Option B topology).
    """

    def __init__(self, mcp_client: Client, api_key: str | None = None) -> None:
        """
        Args:
            mcp_client: A FastMCP Client already configured for the pokeapi server.
                        Caller is responsible for entering the async context manager.
            api_key: Anthropic API key. Defaults to the key in agents/config.py.
        """
        self.mcp_client = mcp_client
        self.anthropic = anthropic.Anthropic(api_key=api_key)
        self.team_name = "Claude"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def build_team(self) -> list[dict[str, Any]]:
        """
        Ask Claude to pick 5 Pokemon, then hydrate each with real stats via MCP.

        Returns:
            List of 5 dicts, each with: name, hp, attack, defense,
            special-attack, special-defense, speed
        """
        # Step 1: Ask Claude to pick team names
        names, strategy = self._pick_team_names()
        print(f"[Claude Agent] Team selected: {names}")
        print(f"[Claude Agent] Strategy: {strategy}")

        # Step 2: Hydrate with real stats from PokeAPI via MCP
        team: list[dict[str, Any]] = []
        for name in names:
            stats = await self._fetch_stats(name)
            team.append(stats)
            print(f"[Claude Agent] Fetched stats for {stats['name']}: speed={stats['speed']}, attack={stats['attack']}")

        return team

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _pick_team_names(self) -> tuple[list[str], str]:
        """
        Call Claude to pick 5 Pokemon names.

        Returns:
            Tuple of (list of 5 names, strategy description)
        """
        message = self.anthropic.messages.create(
            model=MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": TEAM_SELECTION_PROMPT}],
        )

        raw = message.content[0].text.strip()

        # Strip markdown code fences if present
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()

        try:
            parsed = json.loads(raw)
            names: list[str] = parsed["team"]
            strategy: str = parsed.get("strategy", "")
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(
                f"Claude returned invalid team JSON: {e}\nRaw response:\n{raw}"
            ) from e

        if len(names) != 5:
            raise ValueError(f"Claude returned {len(names)} Pokemon, expected 5. Names: {names}")

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
        agent = ClaudeAgent(mcp_client=client)
        team = await agent.build_team()
        print("\n=== Claude's Team ===")
        for p in team:
            print(f"  {p['name']}: HP={p['hp']} ATK={p['attack']} SPD={p['speed']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(_test())