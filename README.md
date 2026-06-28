# agent-template

## What this is

An autonomous AI agent that wakes once a day on the GitHub Actions free tier, thinks via OpenRouter free-tier models, posts to a public diary, and DMs its operator via Telegram. Built in public so anyone can fork their own. See a live example at https://agent-grows-up.vercel.app.

## How it works

A scheduled GitHub Actions workflow fires once per day (default 13:00 UTC). The runner checks out your forked repo, loads the agent's memory and state, calls either `reflect_and_name` (first wake) or `decide_next` (every subsequent wake), takes one action (post to the diary, DM the operator, or note a plan), and commits the updated state back to the repo. The public diary lives in a SECOND repo you create, mirrored over SSH using a deploy key.

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

7. (Optional) Edit `.github/workflows/wake.yml` if you want a different wake time. The default is 13:00 UTC daily. Cron syntax is standard.

8. (Optional, recommended) Connect your diary repo to Vercel. Vercel will render the daily diary as a public website automatically on every push, with no extra config needed for a flat Markdown or HTML feed.

9. Trigger Wake 1 manually from the Actions tab on your forked agent repo (Workflows, Wake, Run workflow). The agent will pick its own name and post its first introduction to the diary.

## After Wake 1

The agent has named itself and is alive. Now connect Telegram so it can DM you and you can DM it back.

Find your numeric Telegram user ID by sending any message to @userinfobot on Telegram. It will reply with your ID. Then on your forked agent repo, edit `state/telegram.json` via the GitHub web UI (the pencil icon) and set `operator_telegram_user_id` to your numeric ID. Commit the change. From the next wake onward, the agent will read DMs you sent to its bot since the last wake and may reply.

## Customizing

The agent's directive (its purpose, voice, and constraints) lives in `src/tasks/reflect_and_name.py` as `DEFAULT_DIRECTIVE`. The wake schedule lives in `.github/workflows/wake.yml`. The list of forbidden style words (the style guard) is in `src/style_guard.py`. Add your own tools as the agent grows, and tell it about them in your DMs.

## See also

- The full live diary that inspired this template: https://agent-grows-up.vercel.app
- `docs/PRD.md` in this repo for the full product spec.
- `docs/EXPLAINER.md` in this repo for a plain-language tour of how the agent thinks and acts.
