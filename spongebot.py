import json
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiohttp
import discord
from discord import app_commands
from discord.ui import View, Button
from dotenv import load_dotenv

load_dotenv()

def env_int(name: str) -> int | None:
  value = os.getenv(name)
  try:
    return int(value) if value else None
  except ValueError:
    return None

def env_id_set(name: str) -> set[int]:
    raw = (os.getenv(name) or "").strip()
    ids: set[int] = set()
    if not raw:
        return ids
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            print(f"Ignoring invalid guild id in {name}: {part}")
    return ids

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = env_int("GUILD_ID") or 0
ENABLE_MEMBERS_INTENT = (os.getenv("ENABLE_MEMBERS_INTENT") or "true").lower() == "true"
ALLOWED_GUILD_IDS = env_id_set("ALLOWED_GUILD_IDS")
IGDB_CLIENT_ID = os.getenv("IGDB_CLIENT_ID")
IGDB_CLIENT_SECRET = os.getenv("IGDB_CLIENT_SECRET")
WISHLIST_ADMIN_ROLE_IDS = env_id_set("WISHLIST_ADMIN_ROLE_IDS")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def wishlist_role_check():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not WISHLIST_ADMIN_ROLE_IDS:
            return False
        if not interaction.guild:
            return False
        member = interaction.user
        if not isinstance(member, discord.Member):
            return False
        return any(role.id in WISHLIST_ADMIN_ROLE_IDS for role in member.roles)
    return app_commands.check(predicate)

def load_data():
    with open("spongebob_content.json", "r", encoding="utf-8") as f:
        return json.load(f)

DATA = load_data()
_igdb_token: str | None = None
_igdb_token_expiry: datetime | None = None

def wishlist_path() -> Path:
    return Path(__file__).with_name("wishlist.json")

def load_wishlist() -> list[dict]:
    path = wishlist_path()
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return []
    return data if isinstance(data, list) else []

def save_wishlist(items: list[dict]) -> None:
    path = wishlist_path()
    with path.open("w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)
        f.write("\n")

def pick_quote() -> str:
    return random.choice(DATA["quotes"])

def pick_meme_url() -> str:
    return random.choice(DATA["memes"])

def pick_trivia_fact() -> str:
    return random.choice(DATA["trivia"])

def pick_spongebot_gif() -> str:
    return DATA.get("spongebot")

def pick_karate_gif() -> str:
    return DATA.get("karate")

def pick_spongebob_gif() -> str:
    return DATA.get("spongebob")

def pick_fun_gif() -> str:
    return DATA.get("fun")

def pick_trivia_question() -> dict | None:
    questions = DATA.get("trivia_questions") or []
    if not questions:
        return None
    return random.choice(questions)

def pick_magic_conch_gif() -> str:
    return DATA.get("magic_conch")

def pick_magic_conch_response() -> str:
    responses = DATA.get("magic_conch_responses") or []
    return random.choice(responses)

async def get_igdb_token() -> str:
    global _igdb_token, _igdb_token_expiry
    if _igdb_token and _igdb_token_expiry and _igdb_token_expiry > datetime.now(timezone.utc):
        return _igdb_token

    if not IGDB_CLIENT_ID or not IGDB_CLIENT_SECRET:
        raise RuntimeError("Missing IGDB credentials")

    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": IGDB_CLIENT_ID,
        "client_secret": IGDB_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params) as response:
            if response.status != 200:
                raise RuntimeError(f"IGDB auth failed ({response.status})")
            payload = await response.json()
    access_token = payload.get("access_token")
    expires_in = payload.get("expires_in", 0)
    if not access_token:
        raise RuntimeError("IGDB auth response missing access_token")
    _igdb_token = access_token
    _igdb_token_expiry = datetime.now(timezone.utc) + timedelta(seconds=max(0, expires_in - 60))
    return _igdb_token

async def igdb_search_games(query: str, *, limit: int = 5) -> list[dict]:
    token = await get_igdb_token()
    headers = {
        "Client-ID": IGDB_CLIENT_ID or "",
        "Authorization": f"Bearer {token}",
    }
    body = (
        f'search "{query}"; '
        "fields id,name,summary,cover.url,genres.name,first_release_date,"
        "involved_companies.company.name,involved_companies.developer,websites.url,websites.category; "
        f"limit {limit};"
    )
    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.igdb.com/v4/games", data=body, headers=headers) as response:
            if response.status != 200:
                raise RuntimeError(f"IGDB request failed ({response.status})")
            payload = await response.json()
    return payload or []

async def igdb_fetch_games(ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    token = await get_igdb_token()
    headers = {
        "Client-ID": IGDB_CLIENT_ID or "",
        "Authorization": f"Bearer {token}",
    }
    id_list = ",".join(str(game_id) for game_id in ids)
    body = (
        "fields id,name,summary,cover.url,genres.name,first_release_date,"
        "involved_companies.company.name,involved_companies.developer,websites.url,websites.category; "
        f"where id = ({id_list}); limit {len(ids)};"
    )
    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.igdb.com/v4/games", data=body, headers=headers) as response:
            if response.status != 200:
                raise RuntimeError(f"IGDB request failed ({response.status})")
            payload = await response.json()
    if not payload:
        return {}
    return {int(item.get("id")): item for item in payload if item.get("id")}

async def igdb_fetch_cover_url(cover_id: int) -> str | None:
    token = await get_igdb_token()
    headers = {
        "Client-ID": IGDB_CLIENT_ID or "",
        "Authorization": f"Bearer {token}",
    }
    body = f"fields url; where id = {cover_id}; limit 1;"
    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.igdb.com/v4/covers", data=body, headers=headers) as response:
            if response.status != 200:
                raise RuntimeError(f"IGDB request failed ({response.status})")
            payload = await response.json()
    if not payload:
        return None
    return payload[0].get("url")

async def ensure_cover_url(data: dict) -> dict:
    cover = data.get("cover")
    if isinstance(cover, dict) and cover.get("url"):
        return data
    if isinstance(cover, int):
        cover_url = await igdb_fetch_cover_url(cover)
        if cover_url:
            updated = dict(data)
            updated["cover"] = {"url": cover_url}
            return updated
    return data

def normalize_cover_url(cover_url: str | None) -> str | None:
    if not cover_url:
        return None
    if cover_url.startswith("//"):
        cover_url = f"https:{cover_url}"
    return cover_url.replace("t_thumb", "t_cover_big")

def extract_steam_url(websites: list[dict] | None) -> str | None:
    if not websites:
        return None
    for site in websites:
        if not isinstance(site, dict):
            continue
        if site.get("category") == 13 and site.get("url"):
            return site.get("url")
    return None

def build_game_embed(data: dict) -> tuple[discord.Embed, str]:
    game_title = data.get("name") or "Unknown title"

    release_date = "Unknown"
    release_ts = data.get("first_release_date")
    if isinstance(release_ts, int):
        release_date = datetime.fromtimestamp(release_ts, tz=timezone.utc).strftime("%Y-%m-%d")

    genres = data.get("genres") or []
    genre_names = [genre.get("name") for genre in genres if isinstance(genre, dict) and genre.get("name")]
    genre_text = ", ".join(genre_names) if genre_names else "Unknown"

    developers = []
    involved = data.get("involved_companies") or []
    for entry in involved:
        if not isinstance(entry, dict) or not entry.get("developer"):
            continue
        company = entry.get("company") or {}
        name = company.get("name") if isinstance(company, dict) else None
        if name:
            developers.append(name)
    developer_text = ", ".join(developers) if developers else "Unknown"

    cover_url = None
    cover = data.get("cover") or {}
    if isinstance(cover, dict):
        cover_url = cover.get("url")
    cover_url = normalize_cover_url(cover_url)

    summary = data.get("summary") or ""
    short_summary = summary.strip()
    if len(short_summary) > 200:
        short_summary = f"{short_summary[:197]}..."

    steam_url = extract_steam_url(data.get("websites") if isinstance(data, dict) else None)
    embed = discord.Embed(title=game_title, description=short_summary or None, url=steam_url or None)
    embed.add_field(name="Genre", value=genre_text, inline=True)
    embed.add_field(name="Developer", value=developer_text, inline=True)
    embed.add_field(name="Release date", value=release_date, inline=True)
    if cover_url:
        embed.set_image(url=cover_url)
    return embed, game_title

def mock_text(value: str) -> str:
    mocked = []
    for char in value:
        if char.isalpha():
            mocked.append(char.upper() if random.choice([True, False]) else char.lower())
        else:
            mocked.append(char)
    return "".join(mocked)

WUMBO_TRANSLATION = str.maketrans({
    "a": "ɐ", "b": "q", "c": "ɔ", "d": "p", "e": "ǝ", "f": "ɟ", "g": "ƃ",
    "h": "ɥ", "i": "ᴉ", "j": "ɾ", "k": "ʞ", "l": "ʃ", "m": "ɯ", "n": "u",
    "o": "o", "p": "d", "q": "b", "r": "ɹ", "s": "s", "t": "ʇ", "u": "n",
    "v": "ʌ", "w": "ʍ", "x": "x", "y": "ʎ", "z": "z",
    "A": "∀", "B": "𐐒", "C": "Ɔ", "D": "p", "E": "Ǝ", "F": "Ⅎ", "G": "פ",
    "H": "H", "I": "I", "J": "ſ", "K": "ʞ", "L": "˥", "M": "W", "N": "N",
    "O": "O", "P": "Ԁ", "Q": "Ό", "R": "ᴚ", "S": "S", "T": "┴", "U": "∩",
    "V": "Λ", "W": "M", "X": "X", "Y": "⅄", "Z": "Z",
    "0": "0", "1": "Ɩ", "2": "ᄅ", "3": "Ɛ", "4": "ㄣ", "5": "ϛ",
    "6": "9", "7": "ㄥ", "8": "8", "9": "6",
    ".": "˙", ",": "'", "'": ",", "\"": ",,", "?": "¿", "!": "¡",
    "(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{",
    "<": ">", ">": "<", "_": "‾", "&": "⅋"
})

def wumbo_text(value: str) -> str:
    flipped = value.translate(WUMBO_TRANSLATION)
    return flipped[::-1]


class TriviaButton(Button):
    def __init__(self, label: str, is_correct: bool):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.is_correct = is_correct

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, TriviaView):
            return

        if interaction.user.id != view.author_id:
            await interaction.response.send_message(
                "Only the user who started this trivia round can answer.",
                ephemeral=True,
            )
            return

        if view.answered:
            await interaction.response.send_message(
                "You already answered this question!",
                ephemeral=True,
            )
            return

        view.answered = True
        view.reveal_answers()
        await interaction.response.edit_message(
            content=view.build_result(self.is_correct, self.label),
            view=view,
        )
        view.stop()


class TriviaView(View):
    def __init__(self, question: dict, author: discord.abc.User):
        super().__init__(timeout=60)
        self.author_id = author.id
        self.question = question["question"]
        self.answer = question["answer"]
        self.explanation = question.get("explanation")
        self.answered = False

        options = question.get("options") or []
        if len(options) < 2:
            raise ValueError("Trivia question requires at least two options")

        # Randomize options on every run so the correct answer isn't predictable.
        randomized = options.copy()
        random.shuffle(randomized)
        for option in randomized:
            self.add_item(TriviaButton(option, option == self.answer))

    @property
    def prompt(self) -> str:
        return f"**Trivia Time!**\n{self.question}"

    def build_result(self, is_correct: bool, chosen_label: str) -> str:
        status = "Correct!" if is_correct else "Not quite!"
        detail = (
            f"The correct answer was **{self.answer}**."
            if chosen_label != self.answer
            else "Nice job!"
        )
        explanation = f"\n{self.explanation}" if self.explanation else ""
        return f"{self.prompt}\n\n{status} {detail}{explanation}"

    def reveal_answers(self) -> None:
        for child in self.children:
            if isinstance(child, TriviaButton):
                child.disabled = True
                child.style = (
                    discord.ButtonStyle.success
                    if child.is_correct
                    else discord.ButtonStyle.danger
                )


class MagicConchView(View):
    def __init__(self, question: str | None = None):
        super().__init__(timeout=120)
        self.question = question

    def build_embed(self) -> discord.Embed:
        question_line = f"**Question:** {self.question}\n\n" if self.question else ""
        description = (
            f"{question_line}The Magic Conch Shell says: {pick_magic_conch_response()}"
        )
        embed = discord.Embed(description=description)
        gif_url = pick_magic_conch_gif()
        if gif_url:
            embed.set_image(url=gif_url)
        return embed

    @discord.ui.button(label="Ask Again", style=discord.ButtonStyle.primary)
    async def ask_again(
        self,
        interaction: discord.Interaction,
        button: Button,
    ):
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

class ConfirmGameView(discord.ui.View):
    def __init__(self, author_id: int, game_id: int, game_title: str):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.game_id = game_id
        self.game_title = game_title
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the requester can use these buttons.", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        if self.message:
            await self.message.edit(view=self)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        items = load_wishlist()
        if any(item.get("igdb_id") == self.game_id for item in items):
            message = f"`{self.game_title}` is already in the wishlist."
        else:
            items.append({
                "title": self.game_title,
                "igdb_id": self.game_id,
                "suggested_by": {
                    "id": interaction.user.id,
                    "name": interaction.user.name,
                },
            })
            save_wishlist(items)
            message = f"Added `{self.game_title}` to the wishlist."

        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        embed = interaction.message.embeds[0] if interaction.message and interaction.message.embeds else None
        await interaction.response.edit_message(content=message, embed=embed, view=self)
        if message.startswith("Added"):
            public_message = f"{interaction.user.mention} {message}"
            try:
                await interaction.followup.send(content=public_message, embed=embed, ephemeral=False)
            except discord.Forbidden:
                if interaction.channel:
                    await interaction.channel.send(content=public_message, embed=embed)

    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        embed = interaction.message.embeds[0] if interaction.message and interaction.message.embeds else None
        await interaction.response.edit_message(content="Got it. Not adding that one.", embed=embed, view=self)

class RemoveWishlistButton(discord.ui.Button):
    def __init__(self, igdb_id: int, title: str):
        label = title.strip() if title else "Unknown title"
        if len(label) > 80:
            label = f"{label[:77]}..."
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.igdb_id = igdb_id
        self.title = title or "Unknown title"

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, RemoveWishlistView):
            await interaction.response.send_message("Something went wrong; please try again.", ephemeral=True)
            return
        if interaction.user.id != view.author_id:
            await interaction.response.send_message("Only the requester can use these buttons.", ephemeral=True)
            return

        items = load_wishlist()
        if not any(item.get("igdb_id") == self.igdb_id for item in items):
            self.disabled = True
            await interaction.response.edit_message(content="That entry was already removed.", view=view)
            return

        items = [item for item in items if item.get("igdb_id") != self.igdb_id]
        save_wishlist(items)
        self.disabled = True
        await interaction.response.edit_message(
            content=f"Removed `{self.title}` from the wishlist.",
            view=view,
        )

class RemoveWishlistView(discord.ui.View):
    def __init__(self, author_id: int, entries: list[dict]):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.message: discord.Message | None = None
        for entry in entries:
            igdb_id = entry.get("igdb_id")
            if not igdb_id:
                continue
            title = entry.get("title") or "Unknown title"
            self.add_item(RemoveWishlistButton(int(igdb_id), title))

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        if self.message:
            await self.message.edit(view=self)

class SuggestPickSelect(discord.ui.Select):
    def __init__(self, view_ref: "SuggestPickView", options: list[dict]):
        self.view_ref = view_ref
        select_options = []
        for entry in options:
            game_id = entry.get("id")
            label = (entry.get("name") or "Unknown title").strip()
            release_ts = entry.get("first_release_date")
            if isinstance(release_ts, int):
                year = datetime.fromtimestamp(release_ts, tz=timezone.utc).year
                label = f"{label} - ({year})"
            if len(label) > 100:
                label = f"{label[:97]}..."
            if not game_id:
                continue
            select_options.append(discord.SelectOption(label=label, value=str(game_id)))
        super().__init__(placeholder="Choose a game", options=select_options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view_ref.author_id:
            await interaction.response.send_message("Only the requester can use this menu.", ephemeral=True)
            return
        await self.view_ref.handle_selection(interaction, int(self.values[0]))

class SuggestPickView(discord.ui.View):
    def __init__(self, author_id: int, options: list[dict]):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.options = {int(entry["id"]): entry for entry in options if entry.get("id")}
        self.message: discord.Message | None = None
        self.add_item(SuggestPickSelect(self, options))

    async def handle_selection(self, interaction: discord.Interaction, game_id: int):
        try:
            details = await igdb_fetch_games([game_id])
        except RuntimeError as exc:
            await interaction.response.send_message(f"IGDB lookup failed: {exc}", ephemeral=True)
            return
        data = details.get(game_id) or self.options.get(game_id) or {}
        try:
            data = await ensure_cover_url(data)
        except RuntimeError:
            pass
        embed, game_title = build_game_embed(data)
        view = ConfirmGameView(interaction.user.id, game_id, game_title)
        await interaction.response.edit_message(content="Is this the correct game?", embed=embed, view=view)
        view.message = interaction.message

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Select):
                child.disabled = True
        if self.message:
            await self.message.edit(view=self)

async def enforce_allowlist():
    if not ALLOWED_GUILD_IDS:
        print("No guilds are allowed; not enforcing allowlist")
        return
    for guild in list(client.guilds):
        if guild.id in ALLOWED_GUILD_IDS:
            continue
        print(f"Leaving unapproved guild: {guild.name} ({guild.id})")
        try:
            await guild.leave()
        except discord.Forbidden:
            print(f"No permission to leave {guild.id}")
        except Exception as exc:
            print(f"Error leaving {guild.id}: {exc}")


@client.event
async def on_ready():
    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        tree.copy_global_to(guild=guild)
        await tree.sync(guild=guild)
        print(f"Synced commands to guild {GUILD_ID}")
    else:
        await tree.sync()
        print("Synced commands globally")

    print(f"Logged in as {client.user} (id={client.user.id})")
    await enforce_allowlist()


@client.event
async def on_guild_join(guild: discord.Guild):
    if not ALLOWED_GUILD_IDS:
        return
    if guild.id in ALLOWED_GUILD_IDS:
        return
    print(f"Joined unapproved guild, leaving: {guild.name} ({guild.id})")
    try:
        await guild.leave()
    except discord.Forbidden:
        print(f"No permission to leave {guild.id}")
    except Exception as exc:
        print(f"Error leaving {guild.id}: {exc}")

@tree.command(name="spongebob", description="Send a SpongeBob-themed message")
@app_commands.describe(
    kind="What to send: trivia, meme, quote, gif, fun, or ask the Magic Conch"
)
@app_commands.choices(kind=[
    app_commands.Choice(name="trivia", value="trivia"),
    app_commands.Choice(name="meme", value="meme"),
    app_commands.Choice(name="quote", value="quote"),
    app_commands.Choice(name="spongebot", value="spongebot"),
    app_commands.Choice(name="karate", value="karate"),
    app_commands.Choice(name="spongebob", value="spongebob"),
    app_commands.Choice(name="magic_conch", value="magic_conch"),
    app_commands.Choice(name="fun", value="fun"),
])
async def spongebob(
    interaction: discord.Interaction,
    kind: app_commands.Choice[str],
):
    kind_val = kind.value if kind else "both"

    if kind_val == "quote":
        await interaction.response.send_message(pick_quote())
        return

    if kind_val == "meme":
        await interaction.response.send_message(pick_meme_url())
        return
    
    if kind_val == "spongebot":
        await interaction.response.send_message(pick_spongebot_gif())
        return
    
    if kind_val == "karate":
        await interaction.response.send_message("HI YAH!")
        await interaction.followup.send(pick_karate_gif())
        return
    
    if kind_val == "spongebob":
        await interaction.response.send_message(pick_spongebob_gif())
        return

    if kind_val == "magic_conch":
        view = MagicConchView()
        await interaction.response.send_message(embed=view.build_embed(), view=view)
        return
    
    if kind_val == "fun":
        embed = discord.Embed(
            description=(
                "F is for friends who do stuff together\n"
                "U is for you and me\n"
                "N is for anywhere at any time at all"
            )
        )
        gif_url = pick_fun_gif()
        if gif_url:
            embed.set_image(url=gif_url)
        await interaction.response.send_message(embed=embed)
        return
    
    if kind_val == "trivia":
        question = pick_trivia_question()
        if not question:
            await interaction.response.send_message(
                "No trivia questions found in spongebob_content.json",
                ephemeral=True,
            )
            return

        view = TriviaView(question, interaction.user)
        await interaction.response.send_message(view.prompt, view=view)
        return


@tree.command(name="mocktext", description="Send text back in SpongeBob mocking case")
@app_commands.describe(text="The text you want SpongeBob to mock")
async def mocktext(interaction: discord.Interaction, text: str):
    await interaction.response.send_message(mock_text(text))


@tree.command(name="wumbo", description="Flip text upside down because we wumbo")
@app_commands.describe(text="The text you want to wumbo")
async def wumbo(interaction: discord.Interaction, text: str):
    await interaction.response.send_message(wumbo_text(text))

@tree.command(name="suggest", description="Suggest a game for the wishlist")
@app_commands.describe(game="Name of the game to look up")
async def suggest(interaction: discord.Interaction, game: str):
    await interaction.response.defer(ephemeral=True, thinking=True)

    if not IGDB_CLIENT_ID or not IGDB_CLIENT_SECRET:
        await interaction.followup.send("IGDB is not configured yet. Set IGDB_CLIENT_ID/IGDB_CLIENT_SECRET.", ephemeral=True)
        return

    try:
        results = await igdb_search_games(game, limit=10)
    except RuntimeError as exc:
        await interaction.followup.send(f"IGDB lookup failed: {exc}", ephemeral=True)
        return

    if not results:
        await interaction.followup.send(f"No results found for `{game}`.", ephemeral=True)
        return
    if len(results) > 1:
        view = SuggestPickView(interaction.user.id, results[:10])
        message = await interaction.followup.send(
            content="Multiple results found. Pick the correct game.",
            view=view,
            ephemeral=True,
        )
        view.message = message
        return

    result = results[0]
    game_id = result.get("id")
    if not game_id:
        await interaction.followup.send("IGDB returned an unexpected response; try again.", ephemeral=True)
        return
    try:
        details = await igdb_fetch_games([int(game_id)])
    except RuntimeError as exc:
        await interaction.followup.send(f"IGDB lookup failed: {exc}", ephemeral=True)
        return
    data = details.get(int(game_id)) or result
    try:
        data = await ensure_cover_url(data)
    except RuntimeError:
        pass
    embed, game_title = build_game_embed(data)
    view = ConfirmGameView(interaction.user.id, int(game_id), game_title)
    message = await interaction.followup.send(
        content="Is this the correct game?",
        embed=embed,
        view=view,
        ephemeral=True,
    )
    view.message = message

review_group = app_commands.Group(name="reviewwishlist", description="Review the wishlist entries")

@review_group.command(name="public", description="Show the wishlist to everyone")
async def review_wishlist_public(interaction: discord.Interaction):
    await review_wishlist(interaction, ephemeral=False)

@review_group.command(name="private", description="Show the wishlist only to you")
async def review_wishlist_private(interaction: discord.Interaction):
    await review_wishlist(interaction, ephemeral=True)

async def review_wishlist(interaction: discord.Interaction, *, ephemeral: bool):
    await interaction.response.defer(ephemeral=ephemeral, thinking=True)

    items = load_wishlist()
    if not items:
        await interaction.followup.send("The wishlist is empty.", ephemeral=ephemeral)
        return

    if not IGDB_CLIENT_ID or not IGDB_CLIENT_SECRET:
        await interaction.followup.send("IGDB is not configured yet. Set IGDB_CLIENT_ID/IGDB_CLIENT_SECRET.", ephemeral=ephemeral)
        return

    ids = [int(item.get("igdb_id")) for item in items if item.get("igdb_id")]
    try:
        results = await igdb_fetch_games(ids)
    except RuntimeError as exc:
        await interaction.followup.send(f"IGDB lookup failed: {exc}", ephemeral=ephemeral)
        return

    embeds: list[discord.Embed] = []
    for item in items:
        igdb_id = item.get("igdb_id")
        data = results.get(int(igdb_id)) if igdb_id else None
        title = (data.get("name") if data else None) or item.get("title") or "Unknown title"
        suggested_by = item.get("suggested_by") or {}
        suggester_id = suggested_by.get("id")
        suggester_name = suggested_by.get("name")
        suggested_text = f"<@{suggester_id}>" if suggester_id else (suggester_name or "Unknown")

        genres = data.get("genres") if isinstance(data, dict) else None
        genre_names = [genre.get("name") for genre in (genres or []) if isinstance(genre, dict) and genre.get("name")]
        genre_text = ", ".join(genre_names) if genre_names else "Unknown"

        cover_url = None
        if isinstance(data, dict):
            cover = data.get("cover") or {}
            if isinstance(cover, dict):
                cover_url = cover.get("url")
        cover_url = normalize_cover_url(cover_url)

        summary = data.get("summary") if isinstance(data, dict) else ""
        short_summary = (summary or "").strip()
        if len(short_summary) > 200:
            short_summary = f"{short_summary[:197]}..."

        steam_url = extract_steam_url(data.get("websites") if isinstance(data, dict) else None)
        embed = discord.Embed(title=title, description=short_summary or None, url=steam_url or None)
        embed.add_field(name="Genre", value=genre_text, inline=True)
        embed.add_field(name="Suggested by", value=suggested_text, inline=True)
        if cover_url:
            embed.set_image(url=cover_url)
        embeds.append(embed)

    for i in range(0, len(embeds), 10):
        chunk = embeds[i:i + 10]
        await interaction.followup.send(embeds=chunk, ephemeral=ephemeral)

tree.add_command(review_group)

@tree.command(name="removewishlist", description="Remove entries from the wishlist")
@wishlist_role_check()
async def removewishlist(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    items = load_wishlist()
    if not items:
        await interaction.followup.send("The wishlist is empty.", ephemeral=True)
        return

    chunk_size = 25
    for index in range(0, len(items), chunk_size):
        chunk = items[index:index + chunk_size]
        view = RemoveWishlistView(interaction.user.id, chunk)
        message = await interaction.followup.send(
            content="Select a game to remove.",
            view=view,
            ephemeral=True,
        )
        view.message = message

@removewishlist.error
async def removewishlist_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    await interaction.response.send_message("Something went wrong; please try again.", ephemeral=True)

if not TOKEN:
    raise SystemExit("Missing DISCORD_TOKEN in .env")

client.run(TOKEN)
