# SpongeBot

SpongeBot is a lightweight Discord bot that exposes a set of SpongeBob-themed
slash commands—centered around `/spongebob` plus `/mocktext` and `/wumbo`. These
commands let you drop memes, quotes, GIFs, and interactive trivia rounds
directly inside your server.

## Features

- **Quotes & Memes** – Randomly sends one of 50 quotes or any meme/GIF stored in
  `spongebob_content.json`.
- **Targeted GIFs** – Dedicated options for `spongebot`, `karate`, `spongebob`,
  and `magic_conch` return specific themed GIFs.
- **Interactive Trivia** – Selecting the `trivia` option posts a multiple-choice
  prompt with Discord buttons so only the command invoker can answer while
  everyone sees the result.
- **Magic Conch & Text Commands** – Ask the Magic Conch for advice (with an
  “Ask Again” button) or use the dedicated `/mocktext` and `/wumbo` commands to
  transform text.
- **Game Wishlist** – Use `/suggest` to confirm games via IGDB, `/reviewwishlist`
  to browse the list publicly or privately, and `/removewishlist` to prune items
  (role-restricted).
- **JSON-driven content** – All quotes, memes, and trivia questions live in
  `spongebob_content.json`, making it simple to add or edit material without
  touching Python code.

## Getting Started

1. **Install `uv`**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. **Install dependencies**
   ```bash
   uv sync
   ```
3. **Configure environment**
   - Copy `sample.env` to `.env`.
   - Fill in `DISCORD_TOKEN` (bot token) and optionally `GUILD_ID` for faster
     command syncing while testing.
   - (Optional) Set `ALLOWED_GUILD_IDS` to a comma-separated list to enforce a
     guild allowlist; the bot will leave any other servers it joins.
   - Set `IGDB_CLIENT_ID` and `IGDB_CLIENT_SECRET` for game lookups via `/suggest`.
   - Set `WISHLIST_ADMIN_ROLE_IDS` to a comma-separated list of role IDs allowed
     to use `/removewishlist`.
4. **Populate content**
   - Edit `spongebob_content.json` if you want to add new quotes, GIFs, or
     trivia questions. Follow the existing structure.
5. **Run the bot**
   ```bash
   uv run spongebot.py
   ```
   The bot logs into Discord, syncs the `/spongebob` command, and listens for
   requests.

## Docker

Clone the repo locally, then build and run the bot via Docker:

```bash
docker build -t spongebot .
docker run --env-file .env spongebot
```

Or use docker compose with the provided `docker-compose.yml`:

```bash
docker compose up -d --build
```
The `wishlist.json` file is mounted so wishlist entries persist between restarts.
The image runs as a non-root user and installs dependencies from
`pyproject.toml` via `uv sync` before copying `spongebot.py` and
`spongebob_content.json`.

## Usage

In Discord, type `/spongebob` and choose one of the available options:

- `quote` – Random SpongeBob quote.
- `meme` – Random meme/GIF URL from the `memes` list.
- `spongebot`, `karate`, `spongebob`, `magic_conch` – Specific GIFs tied to those
  JSON keys (Magic Conch also replies with a random response and provides an “Ask
  Again” button).
- `fun` – Posts the classic F.U.N. song lines with a themed GIF.
- `trivia` – Interactive multiple-choice trivia card.

Other commands:

- `/mocktext <text>` – Transform provided text into mocking case.
- `/wumbo <text>` – Flip provided text upside-down the SpongeBob way.

If you do not pick an option, nothing is sent (the command requires a choice).

## Contributing Content

To expand the bot’s responses, edit `spongebob_content.json`:

- Add more strings to `quotes` or `memes`.
- Update the GIF URLs used for the special options.
- Append new trivia objects with `question`, `answer`, `options`, and an optional
  `explanation`.

Restart the bot after editing the file so it reloads the new data. Have fun!
