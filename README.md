# Zerbania - Discord TTS Bot

A Discord bot that uses ElevenLabs for high-quality text-to-speech in voice channels.

## Features

- `/say <text> [voice]` - Generate TTS and play it in your voice channel
- `/tts <text> [voice]` - Generate TTS and send as an audio file
- `/voices` - List all available ElevenLabs voices
- `/join` - Join your current voice channel
- `/leave` - Leave the voice channel
- Voice autocomplete when selecting voices

## Setup

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Enable these intents under "Privileged Gateway Intents":
   - Message Content Intent
5. Copy the bot token
6. Go to "OAuth2" > "URL Generator"
7. Select scopes: `bot`, `applications.commands`
8. Select bot permissions: `Connect`, `Speak`, `Send Messages`
9. Use the generated URL to invite the bot to your server

### 2. Get ElevenLabs API Key

1. Go to [ElevenLabs](https://elevenlabs.io/)
2. Sign up or log in
3. Go to Settings > API Keys
4. Create and copy your API key

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your tokens:

```
DISCORD_TOKEN=your_discord_bot_token
ELEVENLABS_API_KEY=your_elevenlabs_api_key
DEFAULT_VOICE=Rachel
```

## Deployment (Docker Compose)

### On your Hetzner server:

1. Clone the repository:
```bash
git clone <your-repo-url>
cd zerbania
```

2. Create your `.env` file:
```bash
cp .env.example .env
nano .env  # Add your tokens
```

3. Start the bot:
```bash
docker compose up -d
```

4. View logs:
```bash
docker compose logs -f
```

5. Stop the bot:
```bash
docker compose down
```

6. Update the bot:
```bash
git pull
docker compose up -d --build
```

## Local Development

```bash
# Install dependencies
uv sync

# Run the bot
uv run zerbania
```

## Usage

1. Join a voice channel in your Discord server
2. Use `/say Hello, this is a test!` to hear TTS
3. Use `/tts Hello!` to get an audio file instead
4. Use `/voices` to see all available voices
5. Use `/say Hello! voice:Brian` to use a specific voice
