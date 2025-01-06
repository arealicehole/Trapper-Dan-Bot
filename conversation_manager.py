import re
import base64
import discord
from config import MAX_HISTORY, MAX_FILE_SIZE, IGNORE_PREFIX
from image_processor import ImageProcessor
from config import SYSTEM_PROMPT

class ConversationManager:
    @staticmethod
    def create_system_message():
        return {
            'role': 'system',
            'content': SYSTEM_PROMPT
        }

    @staticmethod
    def sanitize_username(username: str) -> str:
        return re.sub(r'[^\w]', '', re.sub(r'\s+', '_', username))

    @staticmethod
    async def process_message(msg: discord.Message, role: str) -> dict:
        username = ConversationManager.sanitize_username(msg.author.name)
        
        if msg.attachments:
            for attachment in msg.attachments:
                if attachment.content_type.startswith('image/'):
                    image_data = attachment.url
                    if attachment.size > MAX_FILE_SIZE:
                        resized_image = await ImageProcessor.resize_image(attachment.url)
                        if resized_image:
                            image_base64 = base64.b64encode(resized_image.getvalue()).decode('utf-8')
                            image_data = f"data:image/jpeg;base64,{image_base64}"
                        else:
                            raise ValueError("Failed to resize image")

                    return {
                        'role': role,
                        'name': username,
                        'content': [
                            {'type': 'text', 'text': 'Check out this image and tell me what you think about it:'},
                            {'type': 'image_url', 'image_url': {'url': image_data}}
                        ]
                    }
                else:
                    return {
                        'role': role,
                        'name': username,
                        'content': f"I've attached a file: {attachment.filename}"
                    }
        else:
            return {
                'role': role,
                'name': username,
                'content': msg.content
            }

    @staticmethod
    async def build_conversation(message: discord.Message) -> list:
        conversation = [ConversationManager.create_system_message()]
        
        async for msg in message.channel.history(limit=MAX_HISTORY):
            if msg.author.bot and msg.author.id != message.guild.me.id:
                continue
            if msg.content.startswith(IGNORE_PREFIX):
                continue

            role = 'assistant' if msg.author.id == message.guild.me.id else 'user'
            processed_message = await ConversationManager.process_message(msg, role)
            conversation.append(processed_message)
                
        conversation.reverse()
        return conversation