# run this script in order to know your own user ID
# send /userid to the bot and you will receive your ID as a reply
# this will allow you to configure the OWNER_ID variable
# with a OWNER_ID, only you will be able to use certain functions of the bot

# import packages
import os
from dotenv import load_dotenv
import telebot

# load api token
load_dotenv()
TOKEN = os.getenv('TOKEN')
OWNER_NAME = os.getenv('OWNER_NAME')
# OWNER_NAME = "John Doe" # Use your Telegram first name instead

# create bot
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['userid'])
def get_user_id(message):
    if message.from_user.first_name in [OWNER_NAME]:
        bot.send_message(message.chat.id, f'Your user ID is {message.from_user.id}')
    else:
        bot.send_message(message.chat.id, 'You do not possess that kind of power.')

if __name__ == '__main__':
    bot.polling(non_stop=True)