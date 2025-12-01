import io
import os
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from elevenlabs import ElevenLabs

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "Rachel")
GUILD_ID = os.getenv("GUILD_ID")


class TTSBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        self.voices_cache: dict[str, str] = {}

    async def setup_hook(self):
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Synced slash commands to guild {GUILD_ID}")
        else:
            await self.tree.sync()
            print("Synced global slash commands (may take up to 1 hour to appear)")

    async def on_ready(self):
        print(f"Bot is ready! Logged in as {self.user}")
        await self.load_voices()

    async def load_voices(self):
        """Load available voices from ElevenLabs."""
        try:
            response = self.eleven_client.voices.get_all()
            self.voices_cache = {
                voice.name: voice.voice_id for voice in response.voices
            }
            print(f"Loaded {len(self.voices_cache)} voices from ElevenLabs")
        except Exception as e:
            print(f"Failed to load voices: {e}")


bot = TTSBot()


@bot.tree.command(name="voices", description="List all available ElevenLabs voices")
async def voices(interaction: discord.Interaction):
    """List all available voices."""
    if not bot.voices_cache:
        await interaction.response.send_message(
            "No voices loaded. Try again later.", ephemeral=True
        )
        return

    voice_list = "\n".join(f"• {name}" for name in sorted(bot.voices_cache.keys()))
    embed = discord.Embed(
        title="Available Voices",
        description=voice_list,
        color=discord.Color.blue(),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def voice_autocomplete(
    _interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    """Autocomplete for voice selection."""
    voices = list(bot.voices_cache.keys())
    return [
        app_commands.Choice(name=voice, value=voice)
        for voice in voices
        if current.lower() in voice.lower()
    ][:25]


@bot.tree.command(name="tts", description="Generate TTS and send as audio file")
@app_commands.describe(
    text="The text to convert to speech",
    voice="The voice to use (default: Rachel)",
)
@app_commands.autocomplete(voice=voice_autocomplete)
async def tts(
    interaction: discord.Interaction,
    text: str,
    voice: Optional[str] = None,
):
    """Generate TTS and send as an audio file."""
    voice_name = voice or DEFAULT_VOICE

    await interaction.response.defer()

    try:
        voice_id = bot.voices_cache.get(voice_name)
        if not voice_id:
            await interaction.followup.send(
                f"Voice '{voice_name}' not found. Use `/voices` to see available voices.",
                ephemeral=True,
            )
            return

        audio_generator = bot.eleven_client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )

        audio_data = b"".join(audio_generator)
        audio_file = discord.File(
            io.BytesIO(audio_data),
            filename="tts.mp3",
            description=f"TTS: {text[:50]}...",
        )

        await interaction.followup.send(
            f"Generated with voice: **{voice_name}**",
            file=audio_file,
        )

    except Exception as e:
        await interaction.followup.send(f"Error generating speech: {e}", ephemeral=True)


def main():
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN environment variable not set")
        return
    if not ELEVENLABS_API_KEY:
        print("Error: ELEVENLABS_API_KEY environment variable not set")
        return

    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
