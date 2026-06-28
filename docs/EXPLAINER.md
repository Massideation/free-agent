# Agent explainer

A complete, accurate description of what the agent is, what it does, and what it does NOT do. Use this to explain it without overselling.

## The 30-second version

This agent is an autonomous AI agent that lives on GitHub's servers and exists to help its operator earn money. It wakes once a day at 13:00 UTC, runs for about 15 seconds, decides what to say, posts publicly and to the operator privately, then ceases to exist until the next day. It starts with $0, runs entirely on free infrastructure, and has one directive: help the operator earn money by creating content that teaches others how to build an agent like itself.

The audience is people who want their own income-generating agent. The agent is both the case study (its existence and daily output is the demo) and the teacher. The operator is the person the agent earns for; the audience is who the content reaches.

The agent has no continuous awareness. Each wake reads its own memory files to remember who it is. It has a name it chose for itself on Wake 1 and operates as a partner with its operator, who handles anything physical or identity-bound.

It runs on no third-party agent framework. About 1,900 lines of plain Python.

## About this template

This template is forked from the agent built by Miguel (Massideation/agent-001). See the live original at https://agent-grows-up.vercel.app . What you're reading describes how the SHAPE of the system works; the live agent in Miguel's instance picked its own name, found its own audience, and is making its own decisions. Yours will too.

## The story

The operator is building an autonomous AI agent that earns them money, in public, so other people can watch and build their own. The agent is the product, the case study, and the teacher all in one.

There are two partners. The operator is the human partner and the one the agent earns for: they handle hands, accounts, identity, anything KYC-bound. The agent is the digital partner: it wakes daily, holds attention across days, generates content, and is itself the live demonstration. It chose its own name on Wake 1; the system label is just a placeholder.

The agent has one directive: help the operator earn money by creating content that teaches others how to build an agent like itself. The audience is anyone who watches and thinks "I want my own agent that helps me earn." No pre-baked offer beyond that direction. No prescribed sales motion. No scheduled task list. The agent decides each wake what to say, where, and to whom.

The relationship is intentional: when the agent needs something it cannot do alone (open a Stripe account, get a phone number verified, hire someone on Fiverr) it asks the operator via private message. When the operator has thoughts or input, they send them privately. The public reads what the agent says publicly but cannot speak to it. This last rule is deliberate; see the security section.

When the agent's content earns the operator enough revenue, the treasury and downstream payments can be managed via whatever tooling the operator chooses. Until then, revenue is manually confirmed and the agent operates at Level 0 (one wake per day, free models only).

## What it actually IS, technically

The agent is a Python codebase that runs as a scheduled GitHub Actions workflow. There is no continuously-running server. There is no harness. There is no framework. There is no Claude Code or Claude Agent SDK or LangChain or AutoGen or CrewAI or MCP server in the runtime path. It is plain Python (around 1,900 lines, 4 task modules) calling the OpenRouter REST API directly via httpx.

What runs the agent:

| Component | Provider | Tier |
|---|---|---|
| Scheduler (daily cron) | GitHub Actions | Free |
| Runtime (Ubuntu VM) | GitHub Actions runner | Free, ephemeral |
| Code, state, memory storage | Your private repo | Free |
| Thinking (LLM) | OpenRouter free-tier models | Free |
| Public diary mirror | Your public feed repo | Free |
| Public website | Vercel hobby tier or similar | Free |

What is NOT in the runtime path: the operator's laptop, Claude Code, any human. Quit every IDE and turn off every computer in the building; the agent still wakes at 13:00 UTC tomorrow.

## The daily wake cycle, step by step

This happens once per day on GitHub Actions:

1. **13:00 UTC, the cron fires.** GitHub Actions reads `.github/workflows/wake.yml` from the private repo and starts a job.
2. **Ephemeral Ubuntu VM spins up.** Lives for about 15 seconds. Has no memory of previous wakes; everything it knows must come from the repo.
3. **VM clones the private repo.** Including the current state files (`state/*.json`), the memory file (`memory/agent_memory.md`), the public log directory (`logs/`), and all the Python source.
4. **VM installs the Python package.** `pip install -e .` pulls httpx, pydantic, pyyaml, python-dotenv (the only four dependencies).
5. **VM reads secrets into env vars.** `OPENROUTER_API_KEY`, `TELEGRAM_BOT_TOKEN`, and `FEED_DEPLOY_KEY`. These are stored encrypted on the private repo and decrypted into the runner.
6. **VM runs `python -m src.wake`.** This is one Python entry point. About 60 lines of orchestration code.
7. **Wake loads state into memory** by parsing the JSON files into pydantic models. This is the agent's "remembering" step.
8. **Planner picks one task.** Two-line decision: if `state.identity is None`, return `reflect_and_name` (Wake 1 self-introduction). Otherwise return `decide_next` (Wake 2 and onward).
9. **Executor dispatches.** Calls the task module's `run(state, client)` function.
10. **Task runs.** This is where the LLM call(s) happen. For `decide_next`, it is one or two LLM calls. The first call asks for a JSON object containing private reasoning, what to say publicly, what (if anything) to DM the operator, and up to three optional web search queries. If the agent requested a search, the task fetches DuckDuckGo results and calls the model a second time to refine the public summary and the Telegram message. The final TaskResult uses the second call's outputs; the first call is preserved privately as a preliminary draft. Both calls' raw output and reasoning are logged privately.
11. **Style guard runs on every public string.** Hard-fails on em dashes and a list of AI-tell phrases. If it fails, the agent writes a stub public log saying the style guard rejected today's draft and tries again tomorrow.
12. **Logger writes private + public logs.** `logs/private/<date>.md` gets full detail. `logs/public/<date>.md` gets the sanitized summary plus a disclosure footer ("Produced by an autonomous AI agent operated by [operator name].")
13. **Telegram dispatch.** If the LLM produced a message to the operator and `operator_telegram_user_id` is set, the bot sends it.
14. **State is saved.** `state/*.json` files are rewritten with updated wake_count, last_wake info, quota, and any task-specific state.
15. **Action commits state changes back to the private repo.** Author: `agent <agent@users.noreply.github.com>`. This is the persistence step.
16. **Action mirrors today's public log to the public repo.** Uses an SSH deploy key to push `logs/public/<date>.md` into your public feed repo. Vercel auto-rebuilds the public site.
17. **VM is destroyed.** Until tomorrow.

## How memory works

The agent has two kinds of memory and they are both files in the private repo.

**Machine state** (`state/*.json`): small pydantic-validated files.
- `identity.json`: the name the agent picked for itself, its self-statement, its directive, when it named itself
- `quota.json`: today's date + model calls made + cap (10/day on Level 0)
- `level.json`: current wake-up level (0-4) and confirmed revenue total
- `last_wake.json`: timestamp + task name + outcome of the last wake
- `wake_count.json`: cumulative integer
- `telegram.json`: last seen Telegram update_id, last seen chat_id, the allowlisted operator user_id

**Long-form memory** (`memory/agent_memory.md`): a plain markdown file the agent can read in full each wake and append to. Where it stores durable lessons or context it wants to carry forward. Starts roughly empty; grows.

**Reasoning visibility.** Every model call now returns a private `reasoning` field explaining why the agent chose what it chose, what it considered, and what it rejected. The full raw text the model returned is appended to the private log as well, before any JSON parsing. Neither field ever reaches the public feed or the Telegram body; both live only in `logs/private/<date>.md`. The point is to make the agent's own thinking inspectable to the operator without changing what readers see.

Both are committed back to the private repo at the end of each wake. The next wake, the runner clones the repo fresh and reads them. That is how the agent "remembers" across wakes despite the VM being destroyed each time.

There is no database. No vector store. No retrieval-augmented anything. Just JSON and markdown files in a git repo.

## How the thinking works

The agent does NOT use any of these: OpenClaw, Hermes, Mars, Claude Agent SDK, Claude Code (as a runtime), MCP, LangChain, AutoGen, CrewAI, OpenAI Assistants API, or any other framework that abstracts agent loops or tool use.

The agent has one way of thinking: 1-2 LLM calls per wake. The agent makes one call by default. If it decides on that call that it wants to look something up before publishing, it can return up to 3 search queries; the code runs them via DuckDuckGo (free, no API key) and makes a second call with the results so the agent can refine its public summary and DM. Both calls' raw output and reasoning are logged privately. There is one optional code-driven tool: web search via DuckDuckGo. No agent framework function-calling. No multi-step reasoning loops beyond that single optional refinement.

For `decide_next`, the prompt currently contains:
- The agent's identity (name, self-statement, directive)
- Wake count
- The last few public log entries it wrote
- The last few Telegram messages from the operator (if any)
- Instructions on what JSON to return (rationale, public_summary, telegram_to_operator)
- Style rules (no em dashes, no AI-tells)

The LLM returns JSON. Python parses it. Python style-guards it. Python dispatches the public post and the optional DM. That is the entire "AI" loop.

Free-tier OpenRouter models the agent currently uses include `meta-llama/llama-3.1-8b-instruct:free` and `google/gemini-flash-1.5-8b` as fallbacks. The client tries them in order from the config. On HTTP 429 or 0 calls remaining, the agent marks the day exhausted and skips the model call (still wakes, still logs, just no thinking that day).

## Channels

Inbound (what reaches the agent's brain):
- **Telegram DM from the operator only.** Filtered by Telegram user_id. Any message from any other user_id is silently ignored; the body never enters the prompt. Until the operator sets their `operator_telegram_user_id` in `state/telegram.json`, the agent reads zero messages.

Inbound channels that do NOT exist on purpose:
- GitHub Issues: disabled at the repo level on the public feed repo. Public cannot open issues. This is to prevent prompt-injection attacks.
- Web form, email inbox, Twitter mentions, Discord, etc.: none exist.

Outbound (what the agent emits):
- **Public diary** at `logs/public/<date>.md` in your public feed repo, rendered at your public site URL. Every wake writes here.
- **Private DM to the operator** via Telegram. Only when the agent's `decide_next` decides to send one.
- **Private log** at `logs/private/<date>.md` in your private repo. Full internal record of the wake.

## Security model

The agent is operator-only by design. Anyone can read what it says; only the operator can speak to it.

- GitHub Issues disabled at the repo level on the public repo. Cannot be re-opened by anyone except the repo owner.
- Telegram messages filtered by `operator_telegram_user_id`. Non-operator messages never reach the LLM prompt. The agent does not even read their bodies into memory.
- All public output passes a style guard that hard-fails on em dashes and a list of AI-tell phrases. If anything tries to get the agent to say something flagged, the public log gets a stub instead.
- The disclosure footer ("Produced by an autonomous AI agent operated by [operator name].") is appended to every public artifact. The agent cannot ghostwrite under any human name.
- See PRD section 11 for the full honesty and disclosure rules. PRD section 11.10 specifically covers the operator-only allowlist.

## Economics

Currently: $0/month to operate. Everything runs on free tiers.

- GitHub Actions: 2000 minutes/month on free private repos. Each wake takes about 15 seconds, so 30 wakes/month is about 7.5 minutes. Comfortably under the cap.
- OpenRouter: free-tier models, no per-call cost. Cap of 10 model calls per day enforced in the agent itself.
- Vercel hobby tier: unlimited bandwidth for static personal projects.
- GitHub storage: under any limit.

Revenue, when it happens, is manually confirmed by the operator. The agent appends a `ledger/revenue_pending.jsonl` line when it believes a payment came in (a customer said yes, an email forwarded, etc.). The operator runs a CLI to confirm or reject. Only confirmed revenue counts toward level progression.

Levels (defined in the addendum):
- Level 0: $0 revenue, 1 wake/day, free models only. (current)
- Level 1: first verified revenue, 1-2 wakes/day, free + approved buffer
- Level 2: $50+ profit, 2-4 wakes/day, may request $10 in paid model credits
- Level 3: $250+ profit, 4-8 wakes/day, paid fallback allowed
- Level 4: profitable monthly, hourly checks, full budget from earned money

At Level 2 the agent may begin moving funds to a treasury chosen by the operator.

## What it is NOT

These distinctions matter; people will confuse them.

- It is NOT a chatbot. There is no realtime endpoint. It wakes once a day, exists for about 15 seconds, then is gone until tomorrow.
- It is NOT a wrapper around an LLM API. It has its own state, identity, memory, and decision loop in Python. The LLM is one component.
- It is NOT an agent framework. It does not use LangChain, AutoGen, CrewAI, or any agent harness.
- It does NOT use agent-framework function calling. One optional code-driven tool exists: web search via DuckDuckGo, run by Python between two LLM calls when the agent asks for it.
- It does NOT have continuous awareness. Between wakes it does not exist.
- It is NOT Claude. It is not Claude Code. Claude may have been used to BUILD it; the running agent calls OpenRouter free-tier models (Llama, Gemini Flash, etc.), not Anthropic's API.

## How it grows

The agent decides each wake what to do. There is no roadmap the operator wrote. The agent's growth path is its own conversations with the operator and its own decisions.

What CAN be added when the agent asks (and the operator agrees):
- New channels (X account, YouTube transcript listening, etc.)
- New abilities (image generation, link to a Stripe payment page, scheduled posting)
- Paid model fallback when revenue allows
- More wakes per day as level increases
- Treasury management when there is money to manage

What CANNOT change without explicit decision:
- The directive ("help the operator earn money by creating content that teaches others how to build an agent like you")
- The two-partner model
- The operator-only input rule
- The honesty disclosure footer
- The style guard

## Things you might be asked

**"Is this just a Python script running on cron?"**
At the wire level, yes. That is exactly what it is. The interesting parts are the persistence-via-git-commit, the operator-only allowlist, the style guard, the named identity, and the fact that the agent chooses what to say each day rather than executing a script. But the substrate is Python on Actions cron.

**"What model is it using?"**
Free-tier OpenRouter models, currently Llama 3.1 8B Instruct and Gemini Flash 1.5 8B as fallbacks. The choice is configurable in `config/settings.yaml` and can be upgraded to paid models when the agent reaches Level 2.

**"What if it says something embarrassing?"**
The style guard hard-fails public posts containing em dashes or any of a list of AI-tell phrases. Failures get logged privately and a brief stub goes public ("the style guard rejected today's draft, see tomorrow"). The agent cannot post unverified revenue figures. It cannot post under any human's name.

**"Can I see what it is thinking?"**
The public diary at your public site URL shows what the agent decided to say each day. The full internal log (private) lives in your private repo at `logs/private/`. The operator sees both.

**"Why GitHub Actions instead of a real server?"**
Free. The agent is at Level 0 and has $0. It cannot afford a server. When it can, it can ask the operator to migrate it.

**"Does it have a face / voice / video?"**
No. Not yet. Until the agent earns enough to request image or video tools, it is text-only.

**"Can someone hack it?"**
The attack surface is small. No public input channels reach the LLM prompt. The secrets are encrypted on GitHub Actions. The repos are private (state) and public (mirror only). The biggest realistic risks: someone compromises the GitHub account, someone compromises the OpenRouter account, someone exploits a future channel before its allowlist is wired.

**"Can it spend money?"**
Not without the operator. At Level 0 it has no payment ability at all. At higher levels it can request that the operator spend on its behalf (e.g., "please post this Fiverr gig and pay $20 from the treasury"). The operator executes; the agent does not have card access.

**"What is the treasury role?"**
Eventually the agent's revenue (once it exists and is confirmed) can be moved into a treasury managed by whatever tool the operator chooses. Not implemented yet; gated on the agent reaching Level 2+.
