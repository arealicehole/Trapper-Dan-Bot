import discord
import openai
from discord import app_commands
from discord.ext import commands
from config import IGNORE_PREFIX
from conversation_manager import ConversationManager
from openai_client import get_openai_response
from utils import send_response, setup_logger
from gemini_client import generate_shirt_designs
import io

logger = setup_logger(__name__)

intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info('The bot is online and ready to chat!')
    await bot.tree.sync()

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


@bot.tree.command(name="design", description="Create a new t-shirt design for the Kannakickback.")
@app_commands.describe(
    prompt="A description of the design you want to add to the shirt.",
    side="Which side of the shirt to design: 'front' or 'back' (defaults to front)"
)
async def design(interaction: discord.Interaction, prompt: str, side: str = "front"):
    """Creates a t-shirt design using user's prompt."""
    await interaction.response.defer() # Defer the response to avoid timeouts

    # Validate the side parameter
    side = side.lower()
    if side not in ["front", "back"]:
        await interaction.followup.send("Yo, pick either 'front' or 'back' for the side.")
        return

    try:
        # Generate the image
        image = await generate_shirt_designs(prompt, side)

        if not image:
            await interaction.followup.send("Sorry, I couldn't create the design. Something went wrong with the image generation.")
            return

        # Create discord.File object
        file = discord.File(image, filename=f"design_{side}.png")

        # Send the image
        await interaction.followup.send(
            f"Aight, here's the {side} design for '{prompt}'.",
            file=file
        )

    except Exception as e:
        logger.error(f"Error in /design command: {e}")
        await interaction.followup.send("Man, something went sideways. I couldn't finish the design. Try again in a bit.")
