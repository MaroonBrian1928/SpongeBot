import json
import os
import random
import discord
from discord import app_commands
from discord.ui import View, Button
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

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

ALLOWED_GUILD_IDS = env_id_set("ALLOWED_GUILD_IDS")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def load_data():
    with open("spongebob_content.json", "r", encoding="utf-8") as f:
        return json.load(f)

DATA = load_data()

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

async def enforce_allowlist():
    if not ALLOWED_GUILD_IDS:
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

if not TOKEN:
    raise SystemExit("Missing DISCORD_TOKEN in .env")

client.run(TOKEN)
