# Arc

Multi-agent network operations agent for **telecom site fault response** — RAISE Summit, Vultr track.

A deterministic Watchdog ingests the site alarm feed and triggers an Orchestrator running specialized agents in two phases, with a human validation loop on a native iOS app in the middle. All reasoning on **Vultr Serverless Inference**, grounded via **VultronRetriever** in real telecom operations documents. Output: a prioritized action report with a full citation trail.

- **Roadmap:** [docs/ROADMAP.md](docs/ROADMAP.md)
- **Board:** https://github.com/users/aminssutt/projects/3

## Requirements

- **Python ≥ 3.12.** The codebase uses PEP 604 `X | None` annotations evaluated at runtime, so the macOS system `python3` (3.9) crashes on import. `.python-version` pins `3.12` for pyenv; use it (or any 3.12+) for every lane (backend, agents, contracts).
- Copy [`.env.example`](.env.example) to a local `.env` and fill secrets there — never commit `.env` (the repo is public).

## Compliance
Multi-step agent (plans, retrieves more than once, calls real tools, decides, outputs a prioritized action report). Not a basic RAG app · not a dashboard · not an image analyzer (agents reason over structured data, never pixels). Public repo, new work only — built entirely at the event.

## Team
| | |
|---|---|
| vgtray | Agentic AI & workflows (lead) |
| aminssutt | Agentic AI & workflows |
| simerugby | Backend |
| daniwavy5032 | Control-room web + iOS app |
| designspear-epic | Design & UI/UX |
