# Pokemon Agent Battle

Claude vs GPT in a 5-round Pokemon stat battle, powered by LangGraph, FastMCP, and PokeAPI.

> The PokeAPI calls could have been plain async functions inside a LangGraph node — the MCP server is intentionally here to practice the MCP pattern (tool exposure, client/server separation, FastMCP setup) rather than out of necessity.

## About

This project is a hands-on way to learn how modern AI agent frameworks fit together. Two competing LLMs — Anthropic's **Claude** and OpenAI's **ChatGPT** — each act as independent agents that pick a team of Pokemon and argue their strategy. The battle is orchestrated by **LangGraph**, a framework built on top of LangChain that lets you model agent workflows as stateful graphs with nodes (steps) and edges (transitions), including loops and conditional branching. Real Pokemon stats are fetched from the public PokeAPI through a **FastMCP** server, giving both agents access to the same grounded data. The result is a concrete, fun example of multi-agent coordination, stateful graph execution, and LLM tool use — all in one project.

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Copy `.env` and fill in your API keys:
   ```
   OPENAI_API_KEY=your-openai-key-here
   ANTHROPIC_API_KEY=your-anthropic-key-here
   ```

## Running

The MCP server must be running before you start the battle. Open **two terminals**:

**Terminal 1 — start the MCP server:**
```bash
uv run python mcp_server/pokeapi_server.py
```
Leave this running. It serves Pokemon stats from PokeAPI on `http://localhost:8000/mcp`.

**Terminal 2 — run the battle:**
```bash
uv run python main.py
```

## Tech stack

| Library | Role |
|---|---|
| **LangGraph** | Orchestrates the battle as a stateful, cyclical graph |
| **FastMCP** | MCP server that exposes PokeAPI as LLM-callable tools |
| **Anthropic SDK** | Claude agent (Team A) |
| **OpenAI SDK** | GPT agent (Team B) |

## How it works

```
START → build_team_claude → build_team_gpt → battle_round ──┐
                                                              ↓
                                                      [is_battle_over?]
                                                       │           │
                                                   "continue"    "end"
                                                       │           │
                                                  battle_round  result_node → END
```

Each round tests a different stat (speed, attack/defense, special-attack/special-defense, HP, attack+speed). The agent that wins 3 of 5 rounds takes the battle.
