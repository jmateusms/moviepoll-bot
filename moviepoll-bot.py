# import packages
import os
from dotenv import load_dotenv
import telebot
from telebot import types
import requests
import random
from utils import *

# load api token and owner id
load_dotenv()
TOKEN = os.getenv('TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID'))

# create bot
bot = telebot.TeleBot(TOKEN)

# initialize bot memory
pm = memo()

@bot.message_handler(commands=['start', 'help'])
def start(message):
    bot.send_message(message.chat.id,
    '''
Hi, I'm a movie poll bot! I can help you choose a movie with friends.
These are the available commands:
/start, /help - show this message
/hello - say hello
/choose - suggest a movie for the poll (must be a valid IMDb url or tt tag)
/participate - participate in the poll without suggesting a movie
/extra - add an extra movie to the poll (not assigned to a user)
/choices - show all current choices
/poll - create poll
/random - choose random movie among all choices
/clear - clear your choice
/clearextra - clear the extra choice
/veto - veto one of the current choices
''')

@bot.message_handler(commands=['hello'])
def hello(message):
    bot.reply_to(message, 'Hello, I\'m a movie poll bot! I can help you choose a movie with friends.')

@bot.message_handler(commands=['choose'])
def choice(message, ignore_size=False):
    if ignore_size:
        user_input = message.text
    else:
        user_input = message.text.split(' ', 1)
        if len(user_input) <= 1:
            markup = telebot.types.ForceReply(selective=False)
            get_reply = bot.send_message(message.chat.id, "Please, enter a choice:", reply_markup=markup, reply_to_message_id=message.message_id)
            bot.register_next_step_handler(get_reply, choice, True)
            return
        else: user_input = user_input[1]
    tt = get_tt(user_input)
    if tt is not None:
        url = imdb_url(tt)
        title = get_title(get_soup(getHTML(url)))
        pm.user_choices[message.chat.id][message.from_user.id] = {
            'username': message.from_user.first_name,
            'tt': tt,
            'url': url,
            'title': title
        }
        pm.sync_mem()
        bot.send_message(message.chat.id, f'Saved choice {title} for user {pm.user_choices[message.chat.id][message.from_user.id]["username"]}')
    else:
        markup = telebot.types.ForceReply(selective=False)
        get_reply = bot.send_message(message.chat.id, "Please, enter a valid IMDb url or tt tag:", reply_markup=markup)
        bot.register_next_step_handler(get_reply, choice, True)

@bot.message_handler(commands=['choosedummy'])
def dummychoice(message):
    if message.from_user.id in [OWNER_ID]:
        tt = 'tt0068646'
        url = imdb_url(tt)
        title = get_title(get_soup(getHTML(url)))
        pm.user_choices[message.chat.id]['dummy'] = {
            'tt': tt,
            'url': url,
            'title': title
        }
        pm.sync_mem()
        bot.send_message(message.chat.id, f'Saved choice {title} for user {"dummy"}')
    else:
        bot.send_message(message.chat.id, "You do not possess that kind of power.")

@bot.message_handler(commands=['participate'])
def dummychoice(message):
    pm.user_choices[message.chat.id][message.from_user.id] = {
        'username': message.from_user.first_name,
        'tt': None,
        'url': None,
        'title': None
    }
    pm.sync_mem()
    bot.send_message(message.chat.id, f'Added user {pm.user_choices[message.chat.id][message.from_user.id]["username"]} to participate')

@bot.message_handler(commands=['extra'])
def extra(message, ignore_size=False):
    if ignore_size:
        user_input = message.text
    else:
        user_input = message.text.split(' ', 1)
        if len(user_input) <= 1:
            markup = telebot.types.ForceReply(selective=False)
            get_reply = bot.send_message(message.chat.id, "Please, enter a choice:", reply_markup=markup, reply_to_message_id=message.message_id)
            bot.register_next_step_handler(get_reply, extra, True)
            return
        else: user_input = user_input[1]
    tt = get_tt(user_input)
    if tt is not None:
        url = imdb_url(tt)
        title = get_title(get_soup(getHTML(url)))
        pm.user_choices[message.chat.id]['0'] = {
            'username': 'Extra',
            'tt': tt,
            'url': url,
            'title': title
        }
        pm.sync_mem()
        bot.send_message(message.chat.id, f'Saved extra choice {title}.')
    else:
        markup = telebot.types.ForceReply(selective=False)
        get_reply = bot.send_message(message.chat.id, "Please, enter a valid IMDb url or tt tag:", reply_markup=markup)
        bot.register_next_step_handler(get_reply, extra, True)

@bot.message_handler(commands=['choices'])
def display_choices(message):
    bot.send_message(message.chat.id, 'Current choices:')
    for key, value in pm.user_choices[message.chat.id].items():
        bot.send_message(message.chat.id, f'{value["username"]}: {value["title"]}'.format(key=key, value=value))

@bot.message_handler(commands=['clear'])
def clear_choice(message):
    if message.from_user.id in pm.user_choices[message.chat.id]:
        del pm.user_choices[message.chat.id][message.from_user.id]
        pm.sync_mem()
        bot.send_message(message.chat.id, f'Cleared choice for user {pm.user_choices[message.chat.id][message.from_user.id]["username"]}')

@bot.message_handler(commands=['clearextra'])
def clear_extra(message):
    if '0' in pm.user_choices[message.chat.id]:
        del pm.user_choices[message.chat.id]['0']
        pm.sync_mem()
        bot.send_message(message.chat.id, f'Cleared extra choice.')

@bot.message_handler(commands=['clearall'])
def clear_choices(message):
    # if message.from_user.id in [OWNER_ID]:
    if True: # use the line above if you want to be the only one who can clear all choices
        pm.user_choices[message.chat.id].clear()
        pm.sync_mem()
        bot.send_message(message.chat.id, 'Cleared all choices.')
    else:
        bot.send_message(message.chat.id, 'You do not possess that kind of power.')

@bot.message_handler(commands=['veto'])
def veto(message):
    # forcereply with current choices
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add(*[value['title'] for _, value in pm.user_choices[message.chat.id].items() if value['title'] is not None])
    get_reply = bot.send_message(message.chat.id, "Please, enter a choice to veto:", reply_markup=markup)
    bot.register_next_step_handler(get_reply, veto_choice)

@bot.message_handler(commands=[])
def veto_choice(message):
    if message.chat.id in pm.user_choices:
        for key, value in pm.user_choices[message.chat.id].items():
            if value['title'] == message.text:
                del pm.user_choices[message.chat.id][key]
                pm.sync_mem()
                bot.send_message(message.chat.id, f'Vetoed choice {message.text}.')
                return
        bot.send_message(message.chat.id, 'Choice not found.')
    bot.send_message(message.chat.id, 'No choices have been made yet.')

@bot.message_handler(commands=['reset'])
def clear_memory(message):
    if message.from_user.id in [OWNER_ID]:
        pm.create_mem()
        bot.send_message(message.chat.id, 'Bot memory reinitialized.')
    else:
        bot.send_message(message.chat.id, 'You do not possess that kind of power.')

# create a poll from each choice
@bot.message_handler(commands=['poll'])
def poll(message):
    if len(pm.user_choices[message.chat.id]) > 1:
        bot.send_message(message.chat.id, 'Creating poll... Here are the choices:')
        for key, value in pm.user_choices[message.chat.id].items():
            if value['title'] is not None:
                bot.send_message(message.chat.id, f'{value["title"]}: {value["url"]}'.format(key=key, value=value))
        pm.last_poll[message.chat.id] = bot.send_poll(message.chat.id, 'Choose', [value["title"] for key, value in pm.user_choices[message.chat.id].items() if value["title"] is not None], is_anonymous=False)
        pm.users_voted[message.chat.id] = []
        pm.poll_counts[message.chat.id] = len(pm.user_choices[message.chat.id]) * [0]
        pm.poll_chats[pm.last_poll[message.chat.id].poll.id] = message.chat.id
        pm.sync_mem()
    else:
        bot.send_message(message.chat.id, 'You need to have at least two choices to create a poll.')

# create a dummy poll
@bot.message_handler(commands=['fakepoll'])
def poll(message):
    if message.from_user.id in [OWNER_ID]:
        pm.last_poll[message.chat.id] = bot.send_poll(message.chat.id, 'Choose', ['The Godfather', 'Forrest Gump'], is_anonymous=False)
        pm.users_voted[message.chat.id] = []
        pm.poll_chats[pm.last_poll[message.chat.id].poll.id] = message.chat.id
        pm.poll_counts[message.chat.id] = 2 * [0]
        pm.sync_mem()
    else:
        bot.send_message(message.chat.id, 'You do not possess that kind of power.')

# check if all users in user_choices have voted
@bot.poll_answer_handler()
def poll_complete(pollAnswer):
    if not pollAnswer.poll_id in pm.poll_chats:
        return
    chat_id = pm.poll_chats[pollAnswer.poll_id]
    if pm.last_poll[chat_id] is None:
        return
    if pollAnswer.user.id not in pm.users_voted[chat_id]:
        pm.poll_counts[chat_id][pollAnswer.option_ids[0]] += 1
        pm.users_voted[chat_id].append(pollAnswer.user.id)
        bot.send_message(chat_id, f'User {pollAnswer.user.first_name} has voted.')
    else:
        bot.send_message(chat_id, f'User {pollAnswer.user.first_name} has voted (again).')
    if (set(pm.user_choices[chat_id].keys()) - set(['dummy', '0'])).issubset(set(pm.users_voted[chat_id])):
        bot.stop_poll(chat_id, pm.last_poll[chat_id].id)
        ids = pm.poll_counts[chat_id]
        winner_count = max(ids)
        choices = [index for index, value in enumerate(ids) if value == winner_count]
        if ids.count(winner_count) > 1:
            random_key = None
            reroll_slots = random.randint(1, len(choices))
            keys = choices + reroll_slots * [None]
            bot.send_message(chat_id, f'{random.choice(exclamations)} There is a tie!\nChoosing random option. Reroll chance: {reroll_slots*100/(len(keys)):.2f}%')
            rerolls = 0
            while random_key == None:
                random_key = random.choice(keys)
                if random_key == None:
                    rerolls += 1
                    msg = f"{random.choice(reroll_exclamations)}\n{random.choice(exclamations)} Thats the {ordinal(rerolls)} reroll."
                    bot.send_message(chat_id, msg)
            bot.send_message(chat_id, f'Random winner after poll tie: {pm.last_poll[chat_id].poll.options[random_key].text}')
        else:
            bot.send_message(chat_id, f'Winner: {pm.last_poll[chat_id].poll.options[choices[0]].text}')
        pm.user_choices[chat_id].clear()
        pm.users_voted[chat_id].clear()
        pm.poll_counts[chat_id].clear()
        bot.send_message(chat_id, 'Poll complete!')
    pm.sync_mem()

@bot.message_handler(commands=['random'])
def random_choice(message):
    choices = pm.user_choices[message.chat.id]
    if len(choices) > 1:
        random_key = None
        reroll_slots = random.randint(1, len(choices))
        keys = list(choices.keys()) + reroll_slots * [None]
        bot.send_message(message.chat.id, f'Choosing random option. Reroll chance: {reroll_slots*100/(len(keys)):.2f}%.')
        rerolls = 0
        while random_key == None:
            random_key = random.choice(keys)
            if random_key == None:
                rerolls += 1
                msg = f"{random.choice(reroll_exclamations)}\n{random.choice(exclamations)} Thats the {ordinal(rerolls)} reroll."
                bot.send_message(message.chat.id, msg)
        bot.send_message(message.chat.id, f'Random winner: {choices[random_key]["title"]}')
        pm.user_choices[message.chat.id].clear()
        pm.users_voted[message.chat.id].clear()
        pm.poll_counts[message.chat.id].clear()
        pm.sync_mem()
    else:
        bot.send_message(message.chat.id, 'You need to have at least two options to choose from.')

if __name__ == '__main__':
    while True:
        try:
            bot.polling(non_stop=True)
            # yes, this is ugly, but it crashes sometimes otherwise due to
            # random timeouts
        except telebot.apihelper.ApiTelegramException:
            pass
        except requests.exceptions.ConnectionError:
            pass
