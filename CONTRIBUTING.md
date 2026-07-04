# Contributing to Arc

Team of 5, fully parallel lanes, PUBLIC repo. These rules keep `main` green and
conflict-free during the hackathon window. See
[docs/ROADMAP.md](docs/ROADMAP.md) for ownership and phases.

## Golden rules

1. **One feature branch per person, per topic.** Never commit to `main` directly.
2. **Nobody edits outside their directories** (see [ownership](docs/ROADMAP.md#directories--ownership) and `.github/CODEOWNERS`). Cross-cutting need → open an issue for the owner.
3. **`/contracts` is FROZEN after phase 0** — changing it follows the process below.
4. **`/data`: one owner per file** — announce on Discord before touching a file.
5. **No secrets, ever** (repo is PUBLIC). Check before every push. Keys live in local `.env` only.

## Branch naming

```
feat/<name>-<topic>
```

- `<name>` = your GitHub handle (`vgtray`, `aminssutt`, `simerugby`, `daniwavy5032`, `designspear-epic`)
- `<topic>` = short kebab-case scope, e.g. `feat/aminssutt-remediation-agent`

Other prefixes when they fit: `fix/<name>-<topic>`, `chore/<name>-<topic>`, `docs/<name>-<topic>`.

## Pull request flow

`main` is protected: **direct pushes and force-pushes are rejected for everyone,
admins included** (`enforce_admins` is on). The only way in is a PR.

1. Branch off the latest `main`:
   ```bash
   git checkout main && git pull --ff-only
   git checkout -b feat/<name>-<topic>
   ```
2. Commit small, focused changes. Reference the issue in the body (`Closes #NN`).
3. Push and open a PR **to `main`**:
   ```bash
   git push -u origin feat/<name>-<topic>
   gh pr create --base main --fill
   ```
4. **Test the merge locally before it lands** (trial merge into `main`, expect no conflicts):
   ```bash
   git checkout main && git pull --ff-only
   git merge --no-ff --no-commit feat/<name>-<topic>   # must report a clean merge
   git merge --abort                                   # then merge via the PR
   ```
5. CODEOWNERS routes review requests to the directory owner. Get the owner's OK, then merge (squash or merge commit), and delete the branch.
6. **After merging, everyone pulls `main`** and resolves any conflicts on their own branch:
   ```bash
   git checkout main && git pull --ff-only
   git checkout feat/<name>-<topic> && git rebase main   # or: git merge main
   ```

> Direct push to `main` is verified rejected (P0.2): a probe push returns
> `GH006: Protected branch update failed … Changes must be made through a pull request`.

## Changing `/contracts` (FROZEN after phase 0)

Contracts are the frozen interface every lane builds against. Changing one is a
coordinated action, never a silent edit:

1. Open a PR that touches only `/contracts` and explains the change + impact.
2. **Immediately ping on Discord** — this is mandatory, not optional.
3. The **producer** (owner of that contract) **and every consumer** must approve
   before merge. Producers/consumers are listed in
   [ROADMAP.md → shared resources](docs/ROADMAP.md#shared-resources--producer--consumer-table).
4. Merge only once all affected lanes have acknowledged and updated.

## Commit hygiene

- Conventional-ish prefixes: `feat:`, `fix:`, `chore:`, `docs:`, `test:`.
- Never commit `.env`, `*.p8`, or any credential. `.gitignore` covers the common
  cases — a `git diff --staged` scan before pushing is still on you.
