# Zerbania - Discord Bot

A Discord bot with ElevenLabs text-to-speech and Google Gemini image generation.

## Features

- `/tts <text> [voice]` - Generate TTS and send as a playable audio file
- `/voices` - List all available ElevenLabs voices
- `/img <prompt> [image]` - Generate images from text, or modify uploaded images

## Setup

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to **Bot** section and create a bot
4. Enable **Message Content Intent** under Privileged Gateway Intents
5. Copy the bot token
6. Go to **Installation** and set Install Link to "Discord Provided Link"
7. Go to **OAuth2 > URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Permissions: `Send Messages`, `Attach Files`
8. Use the generated URL to invite the bot to your server

### 2. Get API Keys

**ElevenLabs:**
1. Go to [ElevenLabs](https://elevenlabs.io/)
2. Sign up and go to Settings > API Keys
3. Create and copy your API key

**Google AI Studio (for image generation):**
1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Get an API key

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:

```
DISCORD_TOKEN=your_discord_bot_token
ELEVENLABS_API_KEY=your_elevenlabs_api_key
GOOGLE_AI=your_google_ai_api_key
DEFAULT_VOICE=Rachel
GUILD_ID=your_server_id  # For instant slash command sync
```

To get your Guild ID: Enable Developer Mode in Discord settings, then right-click your server > Copy Server ID.

## Deployment (Docker)

```bash
# Start
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down

# Update
git pull && docker compose up -d --build
```

## Local Development

```bash
uv sync
uv run zerbania
```

## Usage

- `/tts Hello world!` - Generate speech with default voice
- `/tts Hello! voice:Brian` - Use a specific voice (autocomplete available)
- `/voices` - See all available voices
- `/img A cat wearing a hat` - Generate an image
- `/img Make this cyberpunk image:[upload]` - Modify an uploaded image
