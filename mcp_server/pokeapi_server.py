"""
MCP server for Pokemon battle data.

Exposes two tools:
  - get_pokemon_stats(name) → fetches base stats from PokeAPI
  - get_popular_pokemon_list() → returns hardcoded popular list for hype checks

Run standalone:
    uv run python mcp_server/pokeapi_server.py

Or import the `mcp` instance directly for in-process use by agents.
"""

import httpx
from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POKEAPI_BASE = "https://pokeapi.co/api/v2"

POPULAR_POKEMON: list[str] = [
    "pikachu",
    "charizard",
    "mewtwo",
    "gengar",
    "eevee",
    "snorlax",
    "lucario",
    "garchomp",
]

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="pokeapi-server",
    instructions=(
        "Provides Pokemon stats and metadata for battle simulations. "
        "Use get_pokemon_stats to fetch a Pokemon's base stats from PokeAPI. "
        "Use get_popular_pokemon_list to check which Pokemon trigger hype commentary."
    ),
)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool
async def get_pokemon_stats(name: str) -> dict:
    """
    Fetch base stats for a Pokemon by name.

    Returns a dict with keys:
        name, hp, attack, defense, special_attack, special_defense, speed

    Raises ValueError if the Pokemon is not found.
    """
    clean_name = name.strip().lower()

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{POKEAPI_BASE}/pokemon/{clean_name}")

    if response.status_code == 404:
        raise ValueError(f"Pokemon '{name}' not found in PokeAPI.")

    response.raise_for_status()
    data = response.json()

    # PokeAPI returns stats as a list of {base_stat, stat: {name}} objects
    stat_map: dict[str, int] = {
        entry["stat"]["name"]: entry["base_stat"]
        for entry in data["stats"]
    }

    return {
        "name": data["name"],
        "hp": stat_map.get("hp", 0),
        "attack": stat_map.get("attack", 0),
        "defense": stat_map.get("defense", 0),
        "special_attack": stat_map.get("special-attack", 0),
        "special_defense": stat_map.get("special-defense", 0),
        "speed": stat_map.get("speed", 0),
    }


@mcp.tool
async def get_popular_pokemon_list() -> dict:
    """
    Return the hardcoded list of popular Pokemon that trigger hype commentary.

    Returns a dict with key:
        popular: list[str]  — lowercase Pokemon names
    """
    return {"popular": POPULAR_POKEMON}


# ---------------------------------------------------------------------------
# Standalone entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Runs as a streamable HTTP MCP server
    # Note: uv run python mcp_server/pokeapi_server.py
    #cd "/Users/ranhesse/Documents/DevelopmentProjects/PokemonAgentBattle/"
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)