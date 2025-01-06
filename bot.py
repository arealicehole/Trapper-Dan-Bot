import discord
import openai
from discord.ext import commands
from config import IGNORE_PREFIX
from conversation_manager import ConversationManager
from openai_client import get_openai_response
from utils import send_response, setup_logger

logger = setup_logger(__name__)

intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info('The bot is online and ready to chat!')

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.content.startswith(IGNORE_PREFIX):
        return

    if bot.user not in message.mentions:
        return

    async with message.channel.typing():
        try:
            conversation = await ConversationManager.build_conversation(message)
            response = await get_openai_response(conversation)
            await send_response(message, response)
        except ValueError as e:
            logger.error(f"Error processing message: {e}")
            await message.reply(f"Yo, I couldn't process that image. {str(e)}")
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            await message.reply("Yo, I'm having some technical difficulties with processing that image. Can you try again with a different one?")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await message.reply("Something weird just happened. Let me catch my breath and we can try this again.")