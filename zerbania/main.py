import io
import os
from typing import Optional

import discord
import httpx
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from elevenlabs import ElevenLabs
from google import genai
from google.genai import types

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
GOOGLE_AI_KEY = os.getenv("GOOGLE_AI")
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "Rachel")
GUILD_ID = os.getenv("GUILD_ID")


class TTSBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        self.genai_client = (
            genai.Client(api_key=GOOGLE_AI_KEY) if GOOGLE_AI_KEY else None
        )
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

    async def on_message(self, message: discord.Message):
        # Ignore messages from the bot itself
        if message.author == self.user:
            return

        # Check if bot was mentioned
        if self.user not in message.mentions:
            return

        if not self.genai_client:
            await message.reply("Chat is not configured. Set GOOGLE_AI in .env")
            return

        # Remove the bot mention from the message
        content = message.content
        for mention in message.mentions:
            content = content.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
        content = content.strip()

        if not content:
            await message.reply("Hey! Ask me something.")
            return

        # Show typing indicator
        async with message.channel.typing():
            try:
                contents = [
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=content),
                        ],
                    ),
                ]

                config = types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=1024,
                    ),
                )

                # Collect response from stream
                response_text = ""
                for chunk in self.genai_client.models.generate_content_stream(
                    model="gemini-3-pro-preview",
                    contents=contents,
                    config=config,
                ):
                    if chunk.text:
                        response_text += chunk.text

                if not response_text:
                    await message.reply("I couldn't generate a response. Try again.")
                    return

                # Discord has a 2000 character limit
                if len(response_text) > 2000:
                    # Split into chunks
                    chunks = [response_text[i:i+1990] for i in range(0, len(response_text), 1990)]
                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            await message.reply(chunk)
                        else:
                            await message.channel.send(chunk)
                else:
                    await message.reply(response_text)

            except Exception as e:
                await message.reply(f"Error: {e}")


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


@bot.tree.command(
    name="img", description="Generate an image from text or modify an uploaded image"
)
@app_commands.describe(
    prompt="Describe the image you want to generate",
    image="Optional: Upload an image to modify/use as reference",
)
async def imagine(
    interaction: discord.Interaction,
    prompt: str,
    image: Optional[discord.Attachment] = None,
):
    """Generate an image using Gemini."""
    if not bot.genai_client:
        await interaction.response.send_message(
            "Image generation is not configured. Set GOOGLE_AI in .env",
            ephemeral=True,
        )
        return

    await interaction.response.defer()

    try:
        parts = []

        # If an image is provided, download and include it
        if image:
            if not image.content_type or not image.content_type.startswith("image/"):
                await interaction.followup.send(
                    "Please upload a valid image file.", ephemeral=True
                )
                return

            async with httpx.AsyncClient() as client:
                response = await client.get(image.url)
                image_bytes = response.content

            parts.append(
                types.Part.from_bytes(data=image_bytes, mime_type=image.content_type)
            )

        parts.append(types.Part.from_text(text=prompt))

        contents = [
            types.Content(
                role="user",
                parts=parts,
            ),
        ]

        config = types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH",
                    threshold="OFF",
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT",
                    threshold="OFF",
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_HARASSMENT",
                    threshold="OFF",
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    threshold="OFF",
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_CIVIC_INTEGRITY",
                    threshold="OFF",
                ),
            ],
        )

        # Use streaming to get the image
        image_data = None
        mime_type = None

        for chunk in bot.genai_client.models.generate_content_stream(
            model="gemini-3-pro-image-preview",
            contents=contents,
            config=config,
        ):
            if (
                chunk.candidates is None
                or chunk.candidates[0].content is None
                or chunk.candidates[0].content.parts is None
            ):
                continue

            part = chunk.candidates[0].content.parts[0]
            if part.inline_data and part.inline_data.data:
                image_data = part.inline_data.data
                mime_type = part.inline_data.mime_type
                break

        if not image_data:
            await interaction.followup.send(
                "Failed to generate image. Try a different prompt.", ephemeral=True
            )
            return

        ext = mime_type.split("/")[-1] if mime_type else "png"
        image_file = discord.File(
            io.BytesIO(image_data),
            filename=f"generated.{ext}",
        )

        await interaction.followup.send(
            f"**Prompt:** {prompt[:100]}{'...' if len(prompt) > 100 else ''}",
            file=image_file,
        )

    except Exception as e:
        await interaction.followup.send(f"Error generating image: {e}", ephemeral=True)


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
