# CLAUDE.md

Claude Code must follow the repository-wide rules in `AGENTS.md`.

## Start Here

Before any implementation:

1. read `MEMORY.md` (Current state first) so a cleared chat can resume;
2. read `AGENTS.md`;
3. read `Implementation.md`;
4. read `docs/architecture/decisions/ADR-011-v1-locked-policies.md`;
5. for UI work, read `docs/architecture/decisions/ADR-012-glass-box-console.md` and `implementation/ui/README.md`;
6. read the current phase file under `implementation/` or `implementation/ui/`;
7. read the architecture documents referenced by that phase;
8. confirm the phase prerequisites and scope. Do not re-open ADR-011 or ADR-012 locks.
9. After the phase PR is opened, update `MEMORY.md` and push it on the phase branch before the session is cleared.

## Working Style

- Follow the Git Workflow in `AGENTS.md`: never commit, push, or merge directly to `main`; one branch per implementation or bug fix; land through a pull request.
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