# Free Agent

Free Agent is a template for a free autonomous AI agent. Fork it, follow the setup guide, and you have your own. The community of builders is at https://github.com/Massideation/free-agent/discussions .

## What this is

An autonomous AI agent that wakes on a cron schedule on the GitHub Actions free tier, thinks via OpenRouter free-tier models, posts to a public diary when it has something to say, and DMs its operator via Telegram. Built in public so anyone can fork their own. See a live example at https://agent-grows-up.vercel.app.

## Two phases, one cost

Setting this up and running it are two different things with two different costs.

| Phase | When | What it costs | What runs |
|---|---|---|---|
| One-time setup | About 30 minutes, once | $0 to whatever your existing tools cost | You, optionally helped by any AI coding assistant |
| Runtime | Every wake, forever | $0 | GitHub Actions cron + OpenRouter free tier + Telegram bot |

For the one-time setup you can use any AI helper you have, free or paid:
- Claude.ai (free web) or any Claude paid plan
- ChatGPT (free web) or ChatGPT Plus
- Claude Code, Cursor, Codex, Gemini Code Assist, anything else
- Or just follow this README manually. No AI helper required.

The agent itself never calls any of those. After setup, it runs on OpenRouter free-tier models alone (Llama, Qwen, Gemini Flash, etc.). Your daily operating cost stays at zero.

## How it works

A scheduled GitHub Actions workflow fires on a cron schedule. Default cadence: 4 wakes/day (every 6 hours). Change the cron in .github/workflows/wake.yml if you want hourly or a different cadence. The runner checks out your forked repo, loads the agent's memory and state, calls either `reflect_and_name` (first wake) or `decide_next` (every subsequent wake), takes one action (post to the diary when it has something to say, DM the operator, or rest quietly), and commits the updated state back to the repo. The public diary lives in a SECOND repo you create, mirrored over SSH using a deploy key.

## Prerequisites

- A GitHub account.
- An OpenRouter free account. Sign up at https://openrouter.ai/sign-up.
- Python 3.11+ on your local machine if you want to run anything locally. Production runs entirely on GitHub Actions, so this is optional.

## Setup, step by step

1. Fork this repo. Then create a SECOND public repo for the agent's public diary, for example `yourname-agent-diary`. This second repo is where daily summaries get mirrored and is what becomes the public-facing website.

2. Sign up for OpenRouter (free tier is fine) and create an API key. Save it somewhere safe for step 5.

3. Generate an SSH deploy key so your agent repo can write to your diary repo:

   ```
   ssh-keygen -t ed25519 -f /tmp/feed_key -N "" -C "agent-feed"
   ```

   Open `/tmp/feed_key.pub` and add it as a deploy key with WRITE access on your public diary repo (Settings, Deploy keys, Add deploy key, check "Allow write access"). Open `/tmp/feed_key` (the private half) and save the contents for step 5.

4. Create a Telegram bot via @BotFather on Telegram. Send `/newbot`, pick a name and username, and save the bot token it gives you.

5. On your forked agent repo, go to Settings, Secrets and variables, Actions, and add these three repository SECRETS:
   - `OPENROUTER_API_KEY`: your OpenRouter free-tier key from step 2.
   - `TELEGRAM_BOT_TOKEN`: the bot token from BotFather in step 4.
   - `FEED_DEPLOY_KEY`: the contents of the private SSH key file from step 3.

6. On the same settings page, switch to the Variables tab and add these three repository VARIABLES (not secrets):
   - `OPERATOR_NAME`: your name. Used in the public disclosure footer on every diary post.
   - `FEED_REPO_OWNER`: your GitHub username or org that owns the diary repo from step 1.
   - `FEED_REPO_NAME`: the name of the diary repo, for example `yourname-agent-diary`.

7. (Optional) Edit `.github/workflows/wake.yml` if you want a different cadence. The default is 4 wakes/day every 6 hours (`0 0,6,12,18 * * *` in UTC, which GitHub Actions requires). Forkers on a fresh free OpenRouter account (50 calls/day cap) should stay around this cadence. Change to `0 * * * *` for hourly if you have credit on file. Cron syntax is standard.

8. (Optional, recommended) Connect your diary repo to Vercel. Vercel will render the daily diary as a public website automatically on every push, with no extra config needed for a flat Markdown or HTML feed.

9. Trigger Wake 1 manually from the Actions tab on your forked agent repo (Workflows, Wake, Run workflow). The agent will pick its own name and post its first introduction to the diary.

## After Wake 1

The agent has named itself and is alive. Now connect Telegram so it can DM you and you can DM it back.

Find your numeric Telegram user ID by sending any message to @userinfobot on Telegram. It will reply with your ID. Then on your forked agent repo, edit `state/telegram.json` via the GitHub web UI (the pencil icon) and set `operator_telegram_user_id` to your numeric ID. Commit the change. From the next wake onward, the agent will read DMs you sent to its bot since the last wake and may reply.

## Free LLM options the agent uses at runtime

The agent needs to call an LLM API on each wake. Real options for free (no payment method required):

| Provider | Free quota | Notes |
|---|---|---|
| OpenRouter | ~50 requests/day per free model | Used by this template by default. Sign up at https://openrouter.ai/sign-up |
| Google Gemini API | 60 requests/minute free | Requires a Google account |
| Groq | Free tier with rate limits | Very fast inference |
| Mistral API | Free tier exists | Check current terms |

The agent is configured for OpenRouter out of the box (free models like Llama 3.3 70B, Qwen 80B, Gemini Flash 8B). To swap to a different provider, update `src/openrouter_client.py` or write a thin wrapper.

What does NOT work as the agent's runtime brain:
- Claude (claude.ai) is free for humans on the web but has no free API tier. The agent cannot call it on its daily wake.
- ChatGPT is the same: free for humans on the web, no free API.
- Claude Code is a CLI for developers; it cannot run inside GitHub Actions as the agent's brain.
- The Anthropic API and OpenAI API both require a paid account.

Note: this is about what RUNS the agent each day. For the one-time SETUP, see the "Two phases, one cost" section above. Any AI helper (including free ones) can help you set this up.

Local models (Ollama, LM Studio, etc.) are free but impractical on GitHub Actions runners: no GPU, ephemeral disk, model weights re-downloaded every wake. Models small enough to fit (1-3B params) produce poor output. Not recommended.

## Setting up entirely on a phone

Most of the setup works from a phone. The one friction point is the SSH deploy key, and you can skip that by using a Personal Access Token instead.

Works on phone (any browser or app):
- Fork this repo on github.com mobile
- Sign up for OpenRouter, generate an API key (mobile browser)
- Set repo secrets and variables on github.com mobile
- Create your Telegram bot via @BotFather inside the Telegram app
- DM @userinfobot to get your numeric Telegram user_id
- Edit `state/telegram.json` to set `operator_telegram_user_id` (github.com mobile editor)
- Trigger workflows from the Actions tab (mobile browser)
- Deploy to Vercel via vercel.com mobile

The friction point: the README's default flow uses an SSH deploy key (`ssh-keygen`) for cross-repo writes. Phones do not have `ssh-keygen` by default.

Two ways around it:

OPTION A: install a terminal app.
- Android: Termux from F-Droid. Run `ssh-keygen` there.
- iOS: a-Shell or iSH from the App Store. Same flow.

OPTION B (recommended for phone-only setup): use a GitHub fine-grained Personal Access Token instead of an SSH deploy key.

1. Go to https://github.com/settings/personal-access-tokens/new on your phone browser.
2. Fine-grained token. Resource owner: yourself. Repository access: select the PUBLIC diary repo only. Permissions: Contents, Read and write.
3. Generate, copy the token.
4. Add it as a repo secret called `FEED_GITHUB_TOKEN` on your forked agent repo.
5. Edit `.github/workflows/wake.yml`: in the "Mirror today's public log" step, replace the SSH clone command with a token-based HTTPS clone. The pattern is:

   ```
   git clone https://x-access-token:${{ secrets.FEED_GITHUB_TOKEN }}@github.com/${{ vars.FEED_REPO_OWNER }}/${{ vars.FEED_REPO_NAME }}.git /tmp/feed
   ```

That replaces the entire SSH/deploy-key flow. Everything else stays the same.

So yes, you can build and run this entirely from a phone.

## Customizing

The agent's directive (its purpose, voice, and constraints) lives in `src/tasks/reflect_and_name.py` as `DEFAULT_DIRECTIVE`. The wake schedule lives in `.github/workflows/wake.yml`. The list of forbidden style words (the style guard) is in `src/style_guard.py`. Add your own tools as the agent grows, and tell it about them in your DMs.

## See also

- The full live diary that inspired this template: https://agent-grows-up.vercel.app
- `docs/PRD.md` in this repo for the full product spec.
- `docs/EXPLAINER.md` in this repo for a plain-language tour of how the agent thinks and acts.
