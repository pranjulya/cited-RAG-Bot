# CLAUDE.md

Claude Code must follow the repository-wide rules in `AGENTS.md`.

## Start Here

Before any implementation:

1. read `AGENTS.md`;
2. read `Implementation.md`;
3. read the current phase file under `implementation/`;
4. read the architecture documents referenced by that phase;
5. confirm the phase prerequisites and scope.

## Working Style

- Implement one phase at a time.
- Do not edit future-phase functionality while working on the current phase.
- Prefer small, reviewable changes.
- Add or update tests with implementation.
- Do not change architecture without updating the relevant ADR first.
- Do not hardcode provider/model/storage configuration that belongs in settings.
- Do not expose secrets or sensitive document content in logs.
- Keep provider-specific code behind adapters.
- Preserve provenance and collection isolation wherever relevant.

## Review Before Completion

Before marking a phase complete, verify:

- required tests pass;
- linting passes;
- type checking passes where configured;
- phase acceptance criteria are satisfied;
- architecture invariants remain intact;
- Learning material is updated;
- the phase status is updated accurately.

Do not claim completion based only on code generation.