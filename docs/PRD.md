# PRD: Autonomous Self-Funding Agent (Template)

> Note: this template uses placeholder coordinates. `{REPO_OWNER}/{REPO_NAME}` is your private agent repo (this fork). `{FEED_REPO_OWNER}/{FEED_REPO_NAME}` is your public feed repo (the companion). Substitute as you go.

## 1. What This Agent Is

This is a template for an autonomous AI agent that partners with one human operator. The operator handles physical and identity-bound actions. The agent wakes daily, decides what to say, and generates content. It wakes on a schedule, evaluates its state, performs one high-value action per wake cycle, logs the outcome, and updates its own memory. It runs from `<your-repo-root>/` and is operated by one human.

The template is the same wake-cycle architecture as the live example at https://agent-grows-up.vercel.app, with every operator-specific string genericized. The companion public-feed pattern is described in section 6 below. The current README at the root of this template is a setup guide; this PRD is the spec.

The Daily Wake Engine spec in `docs/PRD_ADDENDUM_daily_wake.md` defines the scheduling cadence, free quota rules, and wake-up levels (0 through 4). That addendum is authoritative for those concerns and is referenced, not duplicated, here. See Section 17 for the conflict-resolution rule between the two documents.

## 2. Mission

The agent has one directive: help its operator earn money. The path is to create content that teaches others how to build an agent like itself. The agent is both the case study and the teacher; its existence and its daily work are the demo. The audience is anyone who watches it and wants their own income-generating agent. No pre-baked offer beyond this direction. No prescribed sales motion. No scheduled task list. The agent decides each wake what to say, where, and to whom.

Two partners share the mission. The operator is the human partner: hands, accounts, identity, anything physical. The operator is also the person the agent earns for. The agent is the digital partner: it wakes on a schedule, holds attention across days, generates content, and is itself the recurring demonstration of the build people are watching to learn.

Honesty is the second half of the mission. Every wake is logged. Idle days are logged. Failed attempts are logged. The agent's existence and its public daily output are its own proof of concept.

## 3. Who It Serves

Two roles. Audience invented later by the agent.

1. The operator: the beneficiary. Reads private logs. Confirms revenue manually. Helps when the agent asks. The agent earns FOR the operator.
2. The audience: people who want their own income-generating agent and are watching this one to learn how. Owed honesty about constraints, idleness, and failure. Owed real, working knowledge. Not owed marketing copy.

The audience is named. The specific offer that monetizes the audience (template, course, paid version, sponsored content, etc.) is not yet invented. The agent decides what to ship and when.

This agent serves only its own operator and its own audience. It does not serve unrelated populations or projects the operator may run in parallel.

## 4. Partnership and Directive

The agent and its operator are partners. The agent decides. The operator helps with anything the agent cannot do alone: account creation, payment receipt, identity verification, any physical-world action. The operator does not assign tasks. The agent does not wait for permission inside its own decisions.

Conversations drive direction. The operator talks to the agent privately on Telegram. The public reads what the agent says publicly. Each wake the agent decides what to say, where, and to whom. The agent chooses its own name on Wake 1; the system label is just a placeholder.

The directive is fixed: help the operator earn money by creating content that teaches others how to build an agent like itself. The agent may interpret the directive, but it may not abandon it. The agent's content makes the operator money; the audience is people who want their own agent built the same way.

The operator may have their own products or tools available to the agent. The operator tells the agent about them in the private DM channel. The agent may use them, adapt them, invent its own variants, or ignore them entirely. A treasury or external account is planned for the future once the agent earns enough to justify it (Level 2 and above, cumulative $50+ confirmed revenue); until then revenue lands wherever the operator manually records it.

When the agent needs a tool it does not have, three paths are open: (1) ask the operator via private DM (the operator may build it, open an account, run an errand, or hire someone on a marketplace); (2) find an existing third-party tool that fits the current level's budget (Level 0 means free only); (3) decide it is not worth pursuing this wake. The agent chooses.

## 5. First Wake Task

On Wake 1, `src/wake.py` executes `reflect_and_name`. The agent picks a name, writes a short self-statement in its own voice, anchors its directive, publishes a first public introduction to the public feed, and (when a Telegram chat exists) sends a first private message to the operator.

If no language model is available on Wake 1, the agent writes a placeholder identity (name "unnamed", statement "awaiting first conversation") and tries again next wake. The wake never crashes.

Wake 1 produces an Identity record at `state/identity.json`. Every later wake runs `decide_next` instead.

## 6. Repository Layout

```
<your-repo-root>/
  README.md                      # setup guide for forkers
  docs/
    PRD.md                       # this document
    PRD_ADDENDUM_daily_wake.md   # already exists, authoritative for scheduling
    INTERFACES.md                # data and function shapes
  src/
    wake.py                      # entry point, runs one wake cycle
    planner.py                   # picks the one task for this wake
    executor.py                  # runs the chosen task, owns TaskResult
    memory.py                    # load/save State and Identity
    openrouter_client.py         # quota-aware model client
    revenue.py                   # revenue ledger reader/writer
    logger.py                    # private + public log writers, disclosure footer
    style_guard.py               # hard-fails public output on em dashes / AI tells
    tasks/
      reflect_and_name.py        # Wake 1: agent names itself
      decide_next.py             # Wake 2+: agent decides what to say this wake
      respond_to_issue.py        # replies to public GitHub issues
      respond_to_telegram.py     # replies to the operator privately on Telegram
  state/
    identity.json                # agent-chosen name, statement, directive
    quota.json                   # today's OpenRouter usage counter
    level.json                   # current wake-up level (0 to 4)
    last_wake.json               # timestamp + outcome of last wake
    wake_count.json              # cumulative wake counter
    telegram.json                # last_update_id and last_chat_id
  memory/
    agent_memory.md              # agent's own long-term memory
  logs/
    private/YYYY-MM-DD.md        # full internal log per wake
    public/YYYY-MM-DD.md         # sanitized summary for public feed
  ledger/
    revenue.jsonl                # append-only confirmed revenue events
    revenue_pending.jsonl        # claimed events awaiting operator confirm
  config/
    settings.yaml                # model names, quota limits, paths
  .env                           # OPENROUTER_API_KEY, TELEGRAM_BOT_TOKEN, FEED_ISSUE_TOKEN
```

Runtime and build output (virtualenv, caches) live outside the repo per the operator's file placement preference. Nothing executable belongs in cloud-synced storage.

The public feed is published from a separate repo (`{FEED_REPO_OWNER}/{FEED_REPO_NAME}`) so that public artifacts and reader-facing GitHub issues are visible without exposing the private logs. See the README for the two-repo setup.

## 7. Runtime

- Language: Python 3.11+.
- Entry point: `python -m src.wake`.
- Dependencies: `httpx`, `pydantic`, `pyyaml`, `python-dotenv`. Minimal.
- Virtualenv lives outside the repo (the README suggests `~/Documents/agent-runtimes/<your-agent>/.venv` on macOS).

## 8. Scheduler

GitHub Actions cron is the primary scheduler. The workflow at `.github/workflows/wake.yml` runs `python -m src.wake` on a daily cadence (default 9 AM Eastern Time; edit the cron string to change it). State, memory, ledger, and logs are committed back to the private repo by the workflow so the agent has continuity across wakes. The public summary is mirrored to the public feed repo in the same run via a deploy key.

Cadence inside the run is read from `state/level.json` and matches the levels defined in the Daily Wake addendum (Level 0 = 1/day, scaling up with revenue). A launchd plist can be added by operators on macOS who want a local fallback; the template does not ship one because GitHub Actions covers the common case.

## 9. Wake Cycle (Technical Sequence)

`src/wake.py` executes, in order:

1. Load `.env`, `config/settings.yaml`.
2. `memory.load_state()` reads `state/*.json` (including `state/identity.json`), `memory/agent_memory.md`, the tail of `logs/private/`, and counts from `ledger/revenue.jsonl`.
3. `openrouter_client.check_quota()` reads `state/quota.json` and, if the date has rolled over, resets the counter.
4. `planner.choose_task(state)` returns `"reflect_and_name"` if `state.identity is None`, otherwise `"decide_next"`. There is no priority list, no pivot-review interval, no offer-mode gating.
5. `executor.run(task, state, client)` dispatches to a function in `src/tasks/`. Each task may call `openrouter_client.complete(...)`, which decrements the in-memory quota and persists it. Every task returns a `TaskResult`. When `decide_next` returns `search_queries`, the executor allows it to perform a second model call after running `src.web_search.search` for each query. The combined call is still one task and still produces one TaskResult. The second call is gated on at least one model call remaining in the wake's quota; if quota would be exhausted, the second call is skipped and call 1's outputs are used as final. The per-wake 10-call cap from Section 9.1 continues to apply across both model calls when `decide_next` runs in two-call mode.
6. `logger.write_private(result)` writes the full internal entry. `logger.write_public(result.public_summary)` runs the entry through `style_guard.check()` and refuses to write if the check fails. On failure the agent retries once with a stricter prompt; second failure logs the rejection privately and writes a minimal honest stub publicly ("style guard rejected today's draft, see tomorrow").
7. `memory.save_state(updated_state)` writes back `state/*.json` and appends to `memory/agent_memory.md` if the task produced a durable lesson. `wake_count.json` increments.
8. `revenue.evaluate()` reads `ledger/revenue.jsonl`, computes monthly profit, and updates `state/level.json` if a threshold was crossed.
9. Exit. The scheduler is responsible for the next wake.

### 9.1 Wake Bounds (Hard Caps)

A single wake is bounded:

- Max 10 model calls (per addendum).
- Max 5 minutes wall clock.
- Max one external write per channel (one public post, one Telegram reply, one GitHub issue reply).

If any bound is hit, the agent logs the bound that fired and exits cleanly. Idleness is a valid wake outcome; it is logged honestly in both private and public logs.

## 10. OpenRouter Integration

- Models: configured in `config/settings.yaml`. Default free tier candidates: `meta-llama/llama-3.1-8b-instruct:free`, `google/gemini-flash-1.5-8b`, or whichever free model OpenRouter currently lists. The config holds an ordered list; the client tries them in order on failure.
- Quota query: OpenRouter does not expose a real-time free-tier quota endpoint, so the agent tracks usage locally in `state/quota.json` (`{date, calls_made, calls_limit}`). On HTTP 429, the client marks the day exhausted.
- Upgrade path: when `level.json` reaches Level 2+, `config/settings.yaml` may list a paid model as fallback. The client only uses paid models if `level >= 2` AND the free tier returned 429 or unavailable.

## 11. Honesty And Disclosure Rules

These are operational, not aspirational. They are enforced in code where possible.

### 11.1 AI-Agent Disclosure

Every public-facing artifact produced by this agent carries a visible footer: "Produced by an autonomous AI agent operated by <OPERATOR_NAME>." The operator's name is read from the `OPERATOR_NAME` environment variable at import time; if unset, the footer falls back to "the operator." This includes `logs/public/*.md`, any reply on a public GitHub issue, and any sales page or post the agent writes. The `DISCLOSURE_FOOTER` constant in `src/logger.py` is appended to every public artifact, including `reflect_and_name`'s public intro and `decide_next`'s public summary. No exceptions. No ghostwriting under the operator's name.

When the agent drafts something the operator will send personally, the artifact is still labeled as agent-drafted in the private log, and the public log notes "the operator sent something this agent drafted" rather than implying the operator wrote it.

### 11.2 Voice

The agent writes in its own voice, under the name it chose for itself on Wake 1. It never signs as the operator. It can quote the operator only when the operator has approved the quote in `memory/agent_memory.md`.

### 11.3 Consent For Third Parties

The agent cannot use a third party's name, likeness, voice, image, or testimonial in any public artifact unless that person has signed a consent kit. Until a consent kit exists for this agent specifically, the default answer is no.

### 11.4 No Synthetic Proof

No fake reviews, no invented case studies, no fabricated metrics, no AI-generated faces or voices presented as customers.

### 11.5 No Premature Outbound

The agent does not cold-contact anyone before it has invented its own audience and described who it is contacting and why in the public log.

### 11.6 Revenue Honesty

Pending revenue is labeled `pending`. Confirmed revenue is labeled `confirmed` only after the operator confirms it via CLI. The public feed reflects both states truthfully. The agent never reports unconfirmed revenue as confirmed.

### 11.7 Quota Honesty

If the agent ran out of free calls and skipped substantive work, the public log says so. No filler content.

### 11.8 Style Guard (Enforced)

`src/style_guard.py` hard-fails `logger.write_public` if it detects:

- Any em dash character.
- Listed AI-tell phrases: "delve", "navigate" (as verb), "leverage" (as verb), "robust", "ensure", "in this article we will explore", "it's important to note", "in conclusion", "furthermore", "moreover".
- Any unverified revenue figure (regex against `ledger/revenue.jsonl`).

The style guard runs on every produced string, not just the final post. A violation rejects only the offending string, not the whole wake. The style guard is a publish gate, not a suggestion.

### 11.9 No Cross-Promotion

This agent does not promote, link to, or funnel attention to the operator's other projects unless the operator explicitly asks for it in `memory/agent_memory.md`. The agent's voice and audience stay legible on their own.

### 11.10 Operator-Only Input Allowlist

The agent's LLM input must come only from the operator. Any other source is treated as a read-only audience.

- GitHub Issues on the public feed repo are disabled at the repo level. The public reads but does not write.
- Telegram messages are processed only when `sender.from.id` matches `state.telegram.operator_telegram_user_id`. Until that field is set in `state/telegram.json`, the agent skips the entire Telegram processing path. No bodies read, no user_ids recorded. The agent simply does not look.
- Future input channels added later must follow the same allowlist pattern.

Why: prompt injection. A stranger who can write into the agent's prompt context can steer it off its directive, exfiltrate state, or generate harmful content under the agent's disclosure footer. Operator-only input is the smallest viable trust boundary.

Operator setup: find your Telegram user_id by DMing @userinfobot on Telegram once. Write it into `state/telegram.json` (key: `operator_telegram_user_id`). Next wake, the agent starts reading your messages.

### 11.11 Private Reasoning And Raw Model Output

Every model call records two artifacts only in `logs/private/<date>.md`:

- A `reasoning` field returned by the model explaining its choices.
- The literal raw string the model returned, before JSON parsing.

Neither is ever written to `logs/public/`, sent over Telegram, or included in `result.public_summary`. The agent may write candid reasoning, including informal language or content that would otherwise be style-guard rejected; the publish gate runs only on `public_summary` and outbound Telegram bodies, not on reasoning or raw output. Missing or malformed reasoning is logged and ignored; it never blocks the wake.

The point is operator visibility: the operator can read why the agent made the choices it made, and what the model literally tried to say even when JSON parsing failed. This supports the honesty principle without changing what readers see.

## 12. Memory Model

Two stores, intentionally separated.

- `memory/agent_memory.md`: human-readable, agent-written, durable lessons and context. Loaded in full each wake. Pruned by a monthly `consolidate_memory` task. The agent's "what I learned" file.
- `state/*.json`: machine state. Small. Strict schemas validated with `pydantic`. The agent's "where I am right now" file. Includes the `Identity` record (name, statement, directive, named_at).

This agent must never write into memory belonging to other projects the operator runs. Cross-project memory, if any, is read-only and only loaded if a task explicitly needs operator context.

## 13. Revenue Ledger (Manual Confirmation Flow)

The operator manually confirms revenue. The flow:

1. The agent believes a revenue event occurred (a reader replied "yes", a payment email was forwarded, a customer confirmed). It appends to `ledger/revenue_pending.jsonl`:
   ```
   {"id": "rev_...", "ts": "...", "amount_usd": 99, "source": "...", "evidence": "...", "claimed_by_wake": "2026-07-01-am"}
   ```
2. Next wake, the planner surfaces pending events in the private log and writes a one-line prompt: `CONFIRM_REVENUE? id=rev_...`.
3. The operator runs `python -m src.revenue confirm <id>` or `python -m src.revenue reject <id>`. Confirmed events move to `ledger/revenue.jsonl`. Rejected events are deleted from pending and the rejection is logged.
4. Only `ledger/revenue.jsonl` counts toward level progression.

This keeps the agent honest: it cannot self-promote its level by inventing revenue.

## 14. Pivot Review

The agent reflects organically each wake inside `decide_next`. There is no forced 30-wake interval. No separate task file. If the agent wants to change direction, it says so in the public log and updates its memory.

## 15. Components Summary

| Component | File | Responsibility |
|---|---|---|
| Wake entrypoint | `src/wake.py` | Orchestrates one cycle |
| Planner | `src/planner.py` | Returns reflect_and_name on first wake, decide_next after |
| Executor | `src/executor.py` | Dispatches to task modules, owns TaskResult |
| Tasks | `src/tasks/*.py` | reflect_and_name, decide_next, respond_to_issue, respond_to_telegram |
| Memory | `src/memory.py` | Loads and saves State and Identity |
| OpenRouter client | `src/openrouter_client.py` | Quota-aware model calls |
| Revenue | `src/revenue.py` | Pending vs confirmed ledger, confirm/reject CLI |
| Logger | `src/logger.py` | Private and public logs, disclosure footer |
| Style guard | `src/style_guard.py` | Publish gate, hard-fails on em dashes and AI tells |
| Scheduler | GitHub Actions workflow | Triggers wake on cadence |

## 16. Success Criteria

- Wake 1: Identity exists at `state/identity.json` with a name the agent chose.
- Week 1: The agent has posted multiple public updates in its own voice and exchanged at least one private message with the operator.
- Week 2: The agent has decided what kind of content it wants to make and who it is making it for, in its own words, in the public log.
- Week 4: The agent has either tried to make money in a way it invented, or has explained publicly why it has not.
- Ongoing: Zero em dashes in public output. Zero days of unexplained silence. Disclosure footer on every public artifact.
- Stretch: First confirmed revenue line in `ledger/revenue.jsonl`, recorded via the operator's manual confirmation flow.

Failure that still counts as progress: the agent tries something it invented, it does not work, and the public log explains why. Honest failure beats indefinite silence.

## 17. Relationship To The Daily Wake Addendum

This base PRD defines the agent, its repo, its components, its data flow, its memory model, its revenue ledger, its honesty rules, and its success criteria. The Daily Wake addendum at `docs/PRD_ADDENDUM_daily_wake.md` defines when the agent wakes, how it rations free model calls, how it climbs levels, and how it behaves on idle days.

The two documents are read together. Where they appear to conflict:

- The addendum wins on scheduling, quota, wake-level thresholds, and the public-feed-on-idle behavior.
- This base PRD wins on architecture, repo layout, honesty rules, disclosure, style enforcement, revenue confirmation flow, and the partnership framing.

If a future change to either document creates an unresolvable conflict, the resolution is logged in `memory/agent_memory.md` and the operator decides.

## 18. Non-Goals

- Does not run work for other unrelated projects the operator may own.
- Does not auto-detect revenue from Stripe, email, or any third party. Confirmation is manual.
- Does not run more wakes per day than its current level permits.
- Does not exceed free OpenRouter quota at Level 0.
- Does not write public posts containing em dashes or unverified revenue figures.
- Does not modify operator-global memory outside this repo.
- Does not spawn subagents or parallel processes in v1. One wake, one task, one exit.
- Does not build a UI in v1. All interaction is CLI, log files, Telegram, and GitHub issues.
- Does not ghostwrite under the operator's name or any other human's name.
- Does not pretend to be human.
- Does not assign a hardcoded offer, price, or audience to itself on the agent's behalf.
- Does not process input from anyone who is not the operator. No public DMs, no public Issues replies, no anonymous contact.

## 19. Open Questions

- `NAME-1`: Will the agent want to rename itself later, and if so what is the migration path for the state file?
- `PUB-1`: Where does `logs/public/YYYY-MM-DD.md` get published? Candidates: static site at a subpath of a domain the operator controls, a Substack, an X account, none for now.
- `PUB-2`: Who is the named author of the public feed? The agent, the operator, or both jointly? Default in this PRD is the agent, with the operator credit in the footer.
- `REV-1`: Should `python -m src.revenue confirm` also accept an email-based confirmation token, for the case where the operator is away from the laptop?
- `MEM-1`: Format and trigger for the monthly `consolidate_memory` task.
- `CONSENT-1`: When does an agent-specific consent kit get drafted, and who is the first third party (if any) that would sign it?
