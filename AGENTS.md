# AGENTS.md - Contador Oriental

This file provides references to the specification documents for AI agents.

## Specification Files

| File | Description |
|------|-------------|
| [PRODUCT_SPEC.md](AGENTS/PRODUCT_SPEC.md) | App purpose, features, and user flows |
| [ARCHITECTURE_SPEC.md](AGENTS/ARCHITECTURE_SPEC.md) | Tech stack, project structure, patterns |
| [CODING_STANDARDS_SPEC.md](AGENTS/CODING_STANDARDS_SPEC.md) | Code conventions, type hints, error handling |
| [IMPLEMENTATION_SPEC.md](AGENTS/IMPLEMENTATION_SPEC.md) | OCR flow, AI system, database schema |

## Quick Commands

```bash
# Install dependencies
uv sync

# Start Docker services
docker compose up -d

# Run tests
uv run pytest -v

# Lint
uv run ruff check .
uv run ruff format .

# Type check
uv run ty check .

# Fleting CLI
uv run fleting create page <name>
uv run fleting db migrate
uv run fleting db seed
```

## Key References

- See [CODING_STANDARDS_SPEC.md](AGENTS/CODING_STANDARDS_SPEC.md) for error handling patterns
- See [IMPLEMENTATION_SPEC.md](AGENTS/IMPLEMENTATION_SPEC.md) for OCR ticket upload flow
- See [ARCHITECTURE_SPEC.md](AGENTS/ARCHITECTURE_SPEC.md) for database schema
