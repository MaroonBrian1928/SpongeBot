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

def pick_trivia_question() -> dict | None:
    questions = DATA.get("trivia_questions") or []
    if not questions:
        return None
    return random.choice(questions)


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

@client.event
async def on_ready():
    # Sync commands to one guild for fast iteration
    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        tree.copy_global_to(guild=guild)
        await tree.sync(guild=guild)
        print(f"Synced to guild {GUILD_ID}")
    else:
        await tree.sync()
        print("Synced globally")

    print(f"Logged in as {client.user} (id={client.user.id})")

@tree.command(name="spongebob", description="Send a SpongeBob-themed message")
@app_commands.describe(kind="What to send: trivia, meme, quote, spongebot, karate, spongebob")
@app_commands.choices(kind=[
    app_commands.Choice(name="trivia", value="trivia"),
    app_commands.Choice(name="meme", value="meme"),
    app_commands.Choice(name="quote", value="quote"),
    app_commands.Choice(name="spongebot", value="spongebot"),
    app_commands.Choice(name="karate", value="karate"),
    app_commands.Choice(name="spongebob", value="spongebob"),
    
])
async def spongebob(interaction: discord.Interaction, kind: app_commands.Choice[str]):
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

if not TOKEN:
    raise SystemExit("Missing DISCORD_TOKEN in .env")

client.run(TOKEN)
