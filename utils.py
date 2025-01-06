import logging
from config import CHUNK_SIZE

def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

async def send_response(message, response: str):
    for i in range(0, len(response), CHUNK_SIZE):
        chunk = response[i:i+CHUNK_SIZE]
        await message.reply(chunk)