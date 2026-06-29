# Optional tools your agent might want

These are not required. The agent runs fine without them. Add what fits when it fits. All free tiers, no card required unless explicitly noted.

Important: many free tiers do NOT allow you to make money with the output. Each tool below notes whether its free tier permits commercial use. When in doubt, check the tool's current terms; they change.

## Content production
- Suno (https://suno.com) - AI music generation, free tier with daily generations. Free tier: commercial use NOT allowed. The free tier is non-commercial only; you need a paid plan (Pro or Premier) to sell or monetize generated songs.
- Recraft (https://recraft.ai) - AI image generation, free tier with credits. Free tier: commercial use NOT allowed. Free-tier images are owned by Recraft, are public, and carry no commercial rights; you need a paid plan to use output commercially.
- Ideogram (https://ideogram.ai) - AI image generation, free tier daily limit. Free tier: commercial use NOT allowed. Free accounts are personal and non-commercial only, and generations are public by default; commercial use requires a paid plan (Basic or higher).
- Pollinations (https://pollinations.ai) - text-to-image with no signup required. Free tier: unclear and limited. The platform code is MIT, but commercial rights depend on the model: the default Flux dev carries a Black Forest Labs non-commercial license, so use the Apache-2.0 Flux schnell or check the model license before selling output.
- ElevenLabs (https://elevenlabs.io) - AI voice generation, free 10K characters per month. Free tier: commercial use NOT allowed. The free plan has no commercial license and requires attributing elevenlabs.io in the title; the $5/mo Starter plan is the minimum for commercial use.

## Distribution
- Buffer (https://buffer.com) - social post scheduling, free tier covers 3 channels. Free tier: commercial use allowed. No license bar to business use, but the free plan caps you at 3 channels and 10 queued posts per channel with no analytics or AI.
- Beehiiv (https://beehiiv.com) - newsletter platform, free up to 2,500 subscribers. Free tier: unclear and limited. The free Launch plan (up to 2,500 subscribers) lets you run a newsletter, but you cannot sell paid subscriptions, run sponsorships, or use Boosts monetization without a paid plan.
- Kit (formerly ConvertKit) (https://kit.com) - newsletter, free up to 10,000 subscribers. Free tier: commercial use allowed. The free plan (up to 10,000 subscribers) can sell digital products and subscriptions with a per-sale fee, but every email shows Kit branding and third-party commerce integrations need a paid plan.
- Feedly (https://feedly.com) - read RSS feeds, free tier with limits. Free tier: reading feeds for your own research is fine; check current terms before redistributing or reselling content.

## Research and web access beyond DuckDuckGo
- Brave Search API (https://brave.com/search/api) - 2,000 queries per month free, requires sign-up. Free tier: unclear and limited. The standalone free tier was removed for new users in early 2026 (now about $5/mo in renewing credits); commercial query use is fine, but storing results to train an LLM requires a special storage-rights plan.
- Tavily (https://tavily.com) - search optimized for AI agents, free tier with credits. Free tier: commercial use allowed. The free Research plan (1,000 credits per month) permits commercial use in agents and products; you just cannot resell raw results as a competing search engine, and volume is low for production.
- Wikipedia API (https://en.wikipedia.org/api/rest_v1) - no key, no signup. Free tier: commercial use generally fine under Wikipedia's open license; follow attribution and the API usage terms.

## When your agent outgrows GitHub Actions
- Cloudflare Workers (https://workers.cloudflare.com) - 100,000 requests per day free, no card. Free tier: commercial use allowed. The free tier explicitly permits commercial use with no card required; limits are usage-based (100K requests per day, 10ms CPU per call) rather than a commercial ban.
- Fly.io (https://fly.io) - small free allowance, scales with credit-card-required tier. Free tier: hosting commercial apps is fine; constraints are the small allowance and the card-required paid tier, not a commercial ban.
- Render (https://render.com) - free static sites and free PostgreSQL trial. Free tier: hosting commercial sites is fine; constraints are operational (the free Postgres is time-limited), not a commercial ban.
- Supabase (https://supabase.com) - free Postgres database, 500 MB storage. Free tier: commercial use allowed. The free tier explicitly allows serving paying customers; constraints are operational (500MB DB, 50K MAU, and projects pause after 7 days of inactivity), not a commercial-use ban.

## When your agent wants to monitor itself
- BetterUptime / Better Stack (https://betterstack.com) - uptime monitoring, free tier. Free tier: monitoring your own commercial project is fine; check current terms for limits.
- Sentry (https://sentry.io) - error tracking, free up to 5,000 errors per month. Free tier: tracking errors in your own commercial project is fine; check current terms for limits.

## When your agent wants automation
- n8n (https://n8n.io) - self-hosted automation, free if you host it yourself. Free tier: unclear and limited. The Sustainable Use License allows free use for your own internal business automation (even profitable), but you cannot make n8n itself the product you sell to end users or charge third parties for access.
- Make (https://make.com) - no-code automation, free tier with limits. Free tier: commercial use allowed. No license bar to commercial use, but the free plan (1,000 ops per month, 2 scenarios, 15-minute minimum interval) is realistically only enough for testing, not production business workflows.

## Want your agent to use one of these?
The agent in this template knows how to ask for a tool. If you tell it via Telegram "you have access to Suno, here is the API key", it can decide whether to use it. You do not need to wire anything in code; the conversation is enough.

## A note on Stackit
Stackit.ai is a treasury and financial product for autonomous agents. It is intended for agents that have started earning real money (Level 2 plus). When you and your agent reach that point, a sign-up link will be added here. Not before.

## Adding more
If you find a free tool that worked for your agent, open a PR on github.com/Massideation/agent-template adding it to this list. Honest free tiers only.
