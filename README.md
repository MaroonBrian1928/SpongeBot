# SpongeBot

SpongeBot is a lightweight Discord bot that responds to a single slash command,
`/spongebob`, and delivers SpongeBob-themed fun. The command supports several
options so you can drop memes, quotes, GIFs, and even run interactive trivia
rounds directly inside your server.

## Features

- **Quotes & Memes** – Randomly sends one of 50 quotes or any meme/GIF stored in
  `spongebob_content.json`.
- **Targeted GIFs** – Dedicated options for `spongebot`, `karate`, `spongebob`,
  and `magic_conch` return specific themed GIFs.
- **Interactive Trivia** – Selecting the `trivia` option posts a multiple-choice
  prompt with Discord buttons so only the command invoker can answer while
  everyone sees the result.
- **Magic Conch & Text Generators** – Ask the Magic Conch for advice (with an
  “Ask Again” button) or use `mocktext`/`wumbo` to mOcK or flip any text.
- **JSON-driven content** – All quotes, memes, and trivia questions live in
  `spongebob_content.json`, making it simple to add or edit material without
  touching Python code.

## Getting Started

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure environment**
   - Copy `sample.env` to `.env`.
   - Fill in `DISCORD_TOKEN` (bot token) and optionally `GUILD_ID` for faster
     command syncing while testing.
3. **Populate content**
   - Edit `spongebob_content.json` if you want to add new quotes, GIFs, or
     trivia questions. Follow the existing structure.
4. **Run the bot**
   ```bash
   python spongebot.py
   ```
   The bot logs into Discord, syncs the `/spongebob` command, and listens for
   requests.

## Docker

You can also build and run the bot via Docker:

```bash
docker build -t spongebot .
docker run --env-file .env spongebot
```

## Usage

In Discord, type `/spongebob` and choose one of the available options:

- `quote` – Random SpongeBob quote.
- `meme` – Random meme/GIF URL from the `memes` list.
- `spongebot`, `karate`, `spongebob`, `magic_conch` – Specific GIFs tied to those
  JSON keys (Magic Conch also replies with a random response and provides an “Ask
  Again” button).
- `mocktext`, `wumbo` – Transform provided text into mocking case or upside-down
  “wumbo” text.
- `fun` – Posts the classic F.U.N. song lines with a themed GIF.
- `trivia` – Interactive multiple-choice trivia card.

If you do not pick an option, nothing is sent (the command requires a choice).

## Contributing Content

To expand the bot’s responses, edit `spongebob_content.json`:

- Add more strings to `quotes` or `memes`.
- Update the GIF URLs used for the special options.
- Append new trivia objects with `question`, `answer`, `options`, and an optional
  `explanation`.

Restart the bot after editing the file so it reloads the new data. Have fun!
