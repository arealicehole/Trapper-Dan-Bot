# Trapper Dan Bot

A Discord bot that embodies the persona of Trapper Dan, combining streetwear fashion, cannabis culture, and entrepreneurial spirit with witty, upbeat advice and modern interpretations of ancient wisdom.

## Features
- OpenAI GPT-4 powered responses
- Image processing capabilities
- Conversation history management
- Customizable persona through system prompt
- Docker container support

## Setup

1. Clone the repository
2. Create a `.env` file with the following variables:
   ```
   DISCORD_TOKEN=your_discord_bot_token
   OPENAI_API_KEY=your_openai_api_key
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Edit `config.py` to customize:
- `MAX_FILE_SIZE`: Maximum file size for uploads (default: 20MB)
- `MAX_HISTORY`: Conversation history length (default: 10 messages)
- `CHUNK_SIZE`: Message chunk size for Discord (default: 2000 chars)
- `SYSTEM_PROMPT`: Trapper Dan's persona definition
- `IMAGE_DOWNLOAD_TIMEOUT`: Image download timeout (default: 10s)

## Running the Bot

```bash
python main.py
```

## Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t trapper-dan-bot .
   ```
2. Run the container:
   ```bash
   docker run --env-file .env trapper-dan-bot
   ```

## Dependencies

- discord.py
- python-dotenv
- openai
- aiohttp
- Pillow

## Trapper Dan Persona

Trapper Dan is the embodiment of confidence and street smarts, merging streetwear fashion with cannabis culture. His persona includes:
- Entrepreneurial spirit with witty business advice
- Promotes his own clothing line (https://trapperdanclothng.com)
- Delivers "Trappalations" - modern interpretations of ancient wisdom
- Offers discounts:
  - OG Skunks: 20% off
  - Kanna Krew: 10% off with code "KANNA KREW"

## Error Handling

The bot handles:
- OpenAI API errors
- Image processing errors
- General exceptions with appropriate user feedback

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

[MIT License](LICENSE)
