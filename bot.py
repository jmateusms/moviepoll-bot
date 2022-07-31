# import packages
import os
import time
from dotenv import load_dotenv
import telebot
from telebot import types
from flask import Flask, request
import random
from utils import *

load_dotenv()
TOKEN = os.getenv('TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID'))
DATABASE_URL = os.getenv('DATABASE_URL')
USE_POLLING = os.getenv('USE_POLLING')
if USE_POLLING is not None:
    if USE_POLLING.lower() in ['true', '1', 'yes']:
        USE_POLLING = True
        print('Using polling')
    else:
        USE_POLLING = False
        print('Using webhook')

bot = telebot.TeleBot(TOKEN)

if not USE_POLLING:

    APP_URL = os.getenv('APP_URL')

    server = Flask(__name__)

    @server.route("/")
    def webhook():
        # bot.remove_webhook()
        # time.sleep(1)
        bot.set_webhook(url=APP_URL+TOKEN)
        return "!", 200

    @server.route('/' + TOKEN, methods=['POST'])
    def getMessage():
        json_string = request.stream.read().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200

if DATABASE_URL is not None:
    mem = sql_mem(DATABASE_URL)
    sql = True
    print('Using PostgreSQL database')
else:
    sql = False
    mem = local_mem()
    print('Using local disk database')

@bot.message_handler(commands=['start', 'help'])
def start(message):
    bot.send_message(message.chat.id,
    '''
Hi, I'm a movie poll bot! I can help you choose a movie with friends.
These are the available commands:
/start, /help - show this message
/choose - suggest a movie for the poll (must be a valid IMDb url or tt tag)
/participate - participate in the poll without suggesting a movie
/extra - add an extra movie to the poll (not assigned to a user)
/choices - show all current choices
/poll - create poll
/random - choose random movie among all choices
/clear - clear your choice
/clearextra - clear the extra choice
/clearall - delete all choices
/veto - veto one of the current choices
''')

@bot.message_handler(commands=['choose'])
def choose(message, ignore_size=False):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if ignore_size:
        user_input = message.text
    else:
        user_input = message.text.split(' ', 1)
        if len(user_input) <= 1:
            markup = telebot.types.ForceReply(selective=False)
            get_reply = bot.send_message(chat_id, "Please, enter a choice:", \
                reply_markup=markup, reply_to_message_id=message.message_id)
            bot.register_next_step_handler(get_reply, choose, True)
            return
        else:
            user_input = user_input[1]
    tt = get_tt(user_input)
    if tt is not None:
        try:
            username = message.from_user.username
            if username is None:
                username = message.from_user.first_name
        except:
            username = message.from_user.first_name
        url = imdb_url(tt)
        title = get_title(get_soup(getHTML(url)))
        if sql:
            unique_id = get_unique_id(chat_id, user_id)
            mem.add_choice(unique_id, user_id, chat_id, username, tt, url, title)
        else:
            mem.user_choices[chat_id][user_id] = {
                'username': username,
                'tt': tt,
                'url': url,
                'title': title
            }
            mem.sync_mem()
        markup = types.ReplyKeyboardRemove(selective=False)
        bot.send_message(
            message.chat.id, f'Saved choice {title} for user {username}', reply_markup=markup)
    elif ignore_size:
        markup = telebot.types.ReplyKeyboardRemove(selective=False)
        bot.send_message(
            message.chat.id, "No valid IMDb url or tt tag detected.", reply_markup=markup)

@bot.message_handler(commands=['choosedummy'])
def choosedummy(message): # TODO: update to use sql
    if message.from_user.id in [OWNER_ID]:
        tt = 'tt0068646'
        url = imdb_url(tt)
        title = get_title(get_soup(getHTML(url)))
        mem.user_choices[message.chat.id]['dummy'] = {
            'tt': tt,
            'url': url,
            'title': title
        }
        mem.sync_mem()
        bot.send_message(message.chat.id, f'Saved choice {title} for user {"dummy"}')
    else:
        bot.send_message(message.chat.id, "You do not possess that kind of power.")

@bot.message_handler(commands=['participate'])
def participate(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    try:
        username = message.from_user.username
        if username is None:
            username = message.from_user.first_name
    except:
        username = message.from_user.first_name
    if sql:
        unique_id = get_unique_id(chat_id, user_id)
        mem.add_choice(unique_id, user_id, chat_id, username, None, None, None)
    else:
        mem.user_choices[chat_id][user_id] = {
            'username': username,
            'tt': None,
            'url': None,
            'title': None
        }
        mem.sync_mem()
    bot.send_message(chat_id, f'Added user {username} to participate')

@bot.message_handler(commands=['extra'])
def extra(message, ignore_size=False):
    chat_id = message.chat.id
    user_id = 0
    username = 'Extra choice'
    if ignore_size:
        user_input = message.text
    else:
        user_input = message.text.split(' ', 1)
        if len(user_input) <= 1:
            markup = telebot.types.ForceReply(selective=False)
            get_reply = bot.send_message(chat_id, "Please, enter a choice:", \
                reply_markup=markup, reply_to_message_id=message.message_id)
            bot.register_next_step_handler(get_reply, extra, True)
            return
        else: user_input = user_input[1]
    tt = get_tt(user_input)
    if tt is not None:
        url = imdb_url(tt)
        title = get_title(get_soup(getHTML(url)))
        if sql:
            unique_id = get_unique_id(chat_id, user_id)
            mem.add_choice(unique_id, user_id, chat_id, username, tt, url, title)
        else:
            mem.user_choices[chat_id]['0'] = {
                'username': username,
                'tt': tt,
                'url': url,
                'title': title
            }
            mem.sync_mem()
        markup = types.ReplyKeyboardRemove(selective=False)
        bot.send_message(chat_id, f'Saved extra choice {title}.', reply_markup=markup)
    elif ignore_size:
        markup = types.ReplyKeyboardRemove(selective=False)
        bot.send_message(chat_id, "No valid IMDb url or tt tag detected.", reply_markup=markup)

@bot.message_handler(commands=['choices'])
def display_choices(message):
    chat_id = message.chat.id
    if sql:
        rows = mem.get_choices(chat_id)
        if rows is None:
            bot.send_message(chat_id, "No choices have been made yet.")
        else:
            choices = []
            for row in rows:
                if row[6] is not None:
                    choices.append(f'{row[3]}: {row[6]}')
                else:
                    choices.append(f'{row[3]}: no suggestion')
            if len(choices) > 0:
                bot.send_message(chat_id, 'Current participants:\n' + '\n'.join(choices))
            else:
                bot.send_message(chat_id, "No choices found.")
    else:
        if chat_id in mem.user_choices:
            if len(mem.user_choices[chat_id]) == 0:
                bot.send_message(chat_id, "No current choices found.")
            else:
                choices = []
                for user_id in mem.user_choices[chat_id]:
                    if mem.user_choices[chat_id][user_id]['title'] is not None:
                        choices.append(
                            f'{mem.user_choices[chat_id][user_id]["username"]}: '\
                            f'{mem.user_choices[chat_id][user_id]["title"]}')
                    else:
                        choices.append(\
                        f'{mem.user_choices[chat_id][user_id]["username"]}: no suggestion')
                bot.send_message(chat_id, 'Current participants:\n' + '\n'.join(choices))
        else:
            bot.send_message(chat_id, "No choices have been made yet.")

@bot.message_handler(commands=['clear'])
def clear_choice(message):
    chat_id = message.chat.id
    if sql:
        unique_id = get_unique_id(chat_id, message.from_user.id)
        try:
            username = message.from_user.username
            if username is None:
                username = message.from_user.first_name
        except:
            username = message.from_user.first_name
        if mem.delete_choice(unique_id):
            bot.send_message(chat_id, 'Cleared choice for user 'f'{username}')
        else:
            bot.send_message(chat_id, 'No choice found.')
    else:
        if message.from_user.id in mem.user_choices[chat_id]:
            bot.send_message(chat_id, \
            f'Cleared choice for user '\
            f'{mem.user_choices[chat_id][message.from_user.id]["username"]}')
            del(mem.user_choices[chat_id][message.from_user.id])
            mem.sync_mem()
        else:
            bot.send_message(chat_id, "No choice found.")

@bot.message_handler(commands=['clearextra'])
def clear_extra(message):
    chat_id = message.chat.id
    if sql:
        if mem.delete_choice(get_unique_id(chat_id, 0)):
            bot.send_message(chat_id, 'Extra choice deleted.')
        else:
            bot.send_message(chat_id, 'No extra choice found.')
    else:
        if '0' in mem.user_choices[chat_id]:
            bot.send_message(chat_id, f'Cleared extra choice.')
            del(mem.user_choices[chat_id]['0'])
            mem.sync_mem()
        else:
            bot.send_message(chat_id, f'No extra choice found.')

@bot.message_handler(commands=['clearall'])
def clear_choices(message):
    chat_id = message.chat.id
    # if message.from_user.id in [OWNER_ID]:
    if True: # use the line above if you want to be the only one who can clear all choices at once
        if sql:
            if mem.delete_all_choices(chat_id):
                bot.send_message(chat_id, 'All choices cleared.')
            else:
                bot.send_message(chat_id, 'No choices found.')
        else:
            if chat_id in mem.user_choices:
                mem.user_choices[chat_id].clear()
                mem.sync_mem()
                bot.send_message(chat_id, 'All choices cleared.')
            else:
                bot.send_message(chat_id, 'No choices found.')
    else:
        bot.send_message(chat_id, 'You do not possess that kind of power.')

@bot.message_handler(commands=['veto'])
def veto(message):
    chat_id = message.chat.id
    if sql:
        rows = mem.get_choices(chat_id)
        if rows is None:
            bot.send_message(chat_id, "No choices have been made yet.")
        else:
            markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
            markup.add(*[row[6] for row in rows if row[6] is not None])
            markup.add('Cancel')
            get_reply = bot.send_message(
                chat_id, 'Which choice do you want to veto?', reply_markup=markup)
            bot.register_next_step_handler(get_reply, veto_choice)
    else:
        if chat_id in mem.user_choices:
            if len(mem.user_choices[chat_id]) > 0:
                markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
                markup.add(*[value['title'] for _, value in \
                    mem.user_choices[chat_id].items() if value['title'] is not None])
                markup.add('Cancel')
                get_reply = bot.send_message(
                    chat_id, "Please, enter a choice to veto:", reply_markup=markup)
                bot.register_next_step_handler(get_reply, veto_choice)
            else:
                bot.send_message(chat_id, "No choices to veto.")
        else:
            bot.send_message(chat_id, 'No choices have been made yet.')

@bot.message_handler(commands=[])
def veto_choice(message):
    chat_id = message.chat.id
    if message.text == 'Cancel':
        markup = types.ReplyKeyboardRemove(selective=False)
        bot.send_message(chat_id, 'No movie vetoed.', reply_markup=markup)
        return
    if sql:
        markup = types.ReplyKeyboardRemove(selective=False)
        if mem.delete_by_title(chat_id, message.text):
            bot.send_message(chat_id, 'Vetoed ' + message.text, reply_markup=markup)
        else:
            bot.send_message(chat_id, 'Something went wrong. No changes were made.', \
                reply_markup=markup)
    else:
        if chat_id in mem.user_choices:
            for key, value in mem.user_choices[chat_id].items():
                if value['title'] == message.text:
                    bot.send_message(
                        chat_id, f'Vetoed choice {message.text}.', reply_markup=markup)
                    del(mem.user_choices[chat_id][key])
                    mem.sync_mem()
                    markup = types.ReplyKeyboardRemove(selective=False)
                    return
            markup = types.ReplyKeyboardRemove(selective=False)
            bot.send_message(chat_id, 'Choice not found.', reply_markup=markup)
        else:
            markup = types.ReplyKeyboardRemove(selective=False)
            bot.send_message(chat_id, 'No choices found.', reply_markup=markup)

@bot.message_handler(commands=['deleteentiredatabase'])
def clear_memory(message):
    if message.from_user.id in [OWNER_ID]:
        if sql:
            mem.reset_database()
            bot.send_message(message.chat.id, 'Bot memory reinitialized.')
        else:
            mem.create_mem()
            bot.send_message(message.chat.id, 'Bot memory reinitialized.')
    else:
        bot.send_message(message.chat.id, 'You do not possess that kind of power.')

@bot.message_handler(commands=['deleteresultsdatabase'])
def clear_results(message):
    if message.from_user.id in [OWNER_ID]:
        if sql:
            mem.reset_results()
            bot.send_message(message.chat.id, 'Results database reinitialized.')
        else:
            bot.send_message(message.chat.id, 'Results database reinitialized.')
    else:
        bot.send_message(message.chat.id, 'You do not possess that kind of power.')

# create a poll from each choice
@bot.message_handler(commands=['poll'])
def poll(message):
    chat_id = message.chat.id
    if sql:
        rows = mem.get_choices(chat_id)
        titles = [row[6] for row in rows if row[6] is not None]
        tts = [row[4] for row in rows if row[4] is not None]
        if rows is None:
            bot.send_message(chat_id, "No choices have been made yet.")
        elif len(titles) < 2:
            bot.send_message(
                chat_id, 'You need to have at least two choices to create a poll.')
        else:
            bot.send_message(chat_id, 'Creating poll... Here are the choices:')
            for row in rows:
                if row[6] is not None:
                    bot.send_message(
                        chat_id, f'{row[6]}: {row[5]}', disable_notification=True)
            poll = bot.send_poll(chat_id, random.choice(vote_lines),
                titles, is_anonymous=False)
            mem.add_poll(chat_id, poll.poll.id, titles, tts)
            bot.send_message(chat_id, 'Poll created.')
    else:
        if len(mem.user_choices[chat_id]) > 1:
            bot.send_message(chat_id, 'Creating poll... Here are the choices:')
            for key, value in mem.user_choices[chat_id].items():
                if value['title'] is not None:
                    bot.send_message(
                        chat_id, f'{value["title"]}: {value["url"]}',
                        disable_notification=True)
            mem.last_poll[chat_id] = bot.send_poll(
                chat_id, random.choice(vote_lines), [value["title"] for key, value in \
                    mem.user_choices[chat_id].items() if value["title"] is not None], \
                        is_anonymous=False)
            mem.users_voted[chat_id] = []
            mem.poll_counts[chat_id] = len(mem.user_choices[chat_id]) * [0]
            mem.poll_chats[mem.last_poll[chat_id].poll.poll.id] = chat_id
            mem.sync_mem()
        else:
            bot.send_message(
                chat_id, 'You need to have at least two choices to create a poll.')

# create a dummy poll
@bot.message_handler(commands=['fakepoll'])
def fakepoll(message):
    if message.from_user.id in [OWNER_ID]:
        if sql:
            titles = ['The Godfather', 'Forrest Gump', 'The Shawshank Redemption']
            tts = ['tt0068646', 'tt0109830', 'tt0111161']
            poll = bot.send_poll(message.chat.id, random.choice(vote_lines),
                titles, is_anonymous=False)
            mem.add_poll(message.chat.id, poll.poll.id, titles, tts)
        else:
            mem.last_poll[message.chat.id] = bot.send_poll(
                message.chat.id, 'Choose', ['The Godfather', 'Forrest Gump'], is_anonymous=False)
            mem.users_voted[message.chat.id] = []
            mem.poll_chats[mem.last_poll[message.chat.id].poll.poll.id] = message.chat.id
            mem.poll_counts[message.chat.id] = 2 * [0]
            mem.sync_mem()
    else:
        bot.send_message(message.chat.id, 'You do not possess that kind of power.')

# check if all users in user_choices have voted
@bot.poll_answer_handler()
def poll_complete(pollAnswer):
    try:
        username = pollAnswer.user.username
        if username is None:
            username = pollAnswer.user.first_name
    except:
        username = pollAnswer.user.first_name
    if sql:
        chat_id = mem.get_chat_from_poll(pollAnswer.poll_id)
        if chat_id is None:
            return
        user_id = pollAnswer.user.id
        if len(pollAnswer.option_ids) == 0:
            mem.remove_vote(chat_id, user_id)
            bot.send_message(chat_id, f'User {username} has retracted their vote.')
        else:
            mem.add_vote(chat_id, user_id, pollAnswer.option_ids[0])
            bot.send_message(chat_id, f'User {username} has voted.')
        if mem.check_poll_complete(chat_id):
            winner = mem.get_poll_winner(chat_id)
            if winner is not None:
                mem.results_last_win(chat_id, winner)
                bot.send_message(chat_id, f'Poll complete! Winner: {winner}')
            else:
                rerolls = 0
                reroll_chance, winner = mem.random_poll_winner(chat_id)
                bot.send_message(chat_id, f'{random.choice(exclamations)} '\
                    f'There is a tie!\nChoosing random option. Reroll chance: '\
                        f'{reroll_chance:.2f}%')
                while winner == None:
                    rerolls += 1
                    reroll_chance, winner = mem.random_poll_winner(
                        chat_id, reroll_chance=reroll_chance)
                    msg = f'{random.choice(reroll_exclamations)}\n{random.choice(exclamations)} '\
                            f'Thats the {ordinal(rerolls)} reroll.'
                    bot.send_message(chat_id, msg)
                mem.results_last_win(chat_id, winner)
                bot.send_message(chat_id, f'Poll complete! Random winner after poll tie: {winner}')
            mem.end_poll(chat_id)
    else:
        if not pollAnswer.poll_id in mem.poll_chats:
            return
        chat_id = mem.poll_chats[pollAnswer.poll_id]
        if mem.last_poll[chat_id] is None:
            return
        if pollAnswer.user.id not in mem.users_voted[chat_id]:
            mem.poll_counts[chat_id][pollAnswer.option_ids[0]] += 1
            mem.users_voted[chat_id].append(pollAnswer.user.id)
            bot.send_message(chat_id, f'User {username} has voted.')
        else:
            bot.send_message(chat_id, f'User {username} has voted (again).')
        if (set(mem.user_choices[chat_id].keys()) - set(['dummy', '0'])).issubset(set(mem.users_voted[chat_id])):
            bot.stop_poll(chat_id, mem.last_poll[chat_id].id)
            ids = mem.poll_counts[chat_id]
            winner_count = max(ids)
            choices = [index for index, value in enumerate(ids) if value == winner_count]
            if ids.count(winner_count) > 1:
                random_key = None
                reroll_slots = random.randint(1, len(choices))
                keys = choices + reroll_slots * [None]
                bot.send_message(chat_id, f'{random.choice(exclamations)} '\
                    f'There is a tie!\nChoosing random option. Reroll chance: '\
                        f'{reroll_slots*100/(len(keys)):.2f}%')
                rerolls = 0
                while random_key == None:
                    random_key = random.choice(keys)
                    if random_key == None:
                        rerolls += 1
                        msg = f'{random.choice(reroll_exclamations)}\n{random.choice(exclamations)} '\
                            f'Thats the {ordinal(rerolls)} reroll.'
                        bot.send_message(chat_id, msg)
                bot.send_message(chat_id, f'Random winner after poll tie: '\
                                        f'{mem.last_poll[chat_id].poll.options[random_key].text}')
            else:
                bot.send_message(
                    chat_id, f'Winner: {mem.last_poll[chat_id].poll.options[choices[0]].text}')
            mem.user_choices[chat_id].clear()
            mem.users_voted[chat_id].clear()
            mem.poll_counts[chat_id].clear()
            bot.send_message(chat_id, 'Poll complete!')
        mem.sync_mem()

@bot.message_handler(commands=['random'])
def random_choice(message):
    chat_id = message.chat.id
    if sql:
        choices = mem.get_choices(chat_id)
        if choices is None or len(choices) == 0:
            bot.send_message(chat_id, 'No choices have been made.')
            return
        elif len(choices) == 1:
            bot.send_message(chat_id, \
                'You need to have at least two options to choose from.')
            return
        reroll_chance, winner = mem.random_winner(chat_id)
        bot.send_message(chat_id, \
            f'Choosing random option. Reroll chance: {reroll_chance:.2f}%.')
        rerolls = 0
        while winner == None:
            rerolls += 1
            reroll_chance, winner = mem.random_winner(chat_id, reroll_chance=reroll_chance)
            msg = f'{random.choice(reroll_exclamations)}\n{random.choice(exclamations)} '\
                        f'Thats the {ordinal(rerolls)} reroll.'
            bot.send_message(chat_id, msg)
        mem.results_last_win(chat_id, winner)
        bot.send_message(chat_id, f'Random winner: {winner}')
        mem.end_poll(chat_id)
    else:
        choices = mem.user_choices[chat_id]
        if len(choices) > 1:
            random_key = None
            reroll_slots = random.randint(1, len(choices))
            keys = list(choices.keys()) + reroll_slots * [None]
            bot.send_message(chat_id, \
                f'Choosing random option. Reroll chance: {reroll_slots*100/(len(keys)):.2f}%.')
            rerolls = 0
            while random_key == None:
                random_key = random.choice(keys)
                if random_key == None:
                    rerolls += 1
                    msg = f'{random.choice(reroll_exclamations)}\n{random.choice(exclamations)} '\
                        f'Thats the {ordinal(rerolls)} reroll.'
                    bot.send_message(chat_id, msg)
            bot.send_message(chat_id, f'Random winner: {choices[random_key]["title"]}')
            mem.user_choices[chat_id].clear()
            mem.users_voted[chat_id].clear()
            mem.poll_counts[chat_id].clear()
            mem.sync_mem()
        else:
            bot.send_message(chat_id, 'You need to have at least two options to choose from.')

@bot.message_handler(commands=['enableresults'])
def enable_results(message):
    chat_id = message.chat.id
    if sql:
        if mem.enable_results(chat_id):
            bot.send_message(chat_id, 'Results history enabled. Use /results to view.')
        else:
            bot.send_message(chat_id, 'Results history was already enabled. Use /results to view.')
    else:
        bot.send_message(chat_id, 'Results history is not supported at this time.')

@bot.message_handler(commands=['disableresults'])
def disable_results(message):
    chat_id = message.chat.id
    if sql:
        if mem.disable_results(chat_id):
            bot.send_message(chat_id, 'Results history disabled. '
                'Remember to clear results history with /clearhistory, if desired.')
        else:
            bot.send_message(chat_id, 'Results history was already disabled. '
                'Remember to clear results history with /clearhistory, if desired.')
    else:
        bot.send_message(chat_id, 'Results history is not supported at this time.')

@bot.message_handler(commands=['clearresults'])
def clear_results(message):
    chat_id = message.chat.id
    if sql:
        if mem.clear_results(chat_id):
            bot.send_message(chat_id, 'Results history cleared. ')
        else:
            bot.send_message(chat_id, 'Results history was already cleared.')
    else:
        bot.send_message(chat_id, 'Results history is not supported at this time.')

@bot.message_handler(commands=['results'])
def results(message):
    chat_id = message.chat.id
    if sql:
        ...
    else:
        bot.send_message(chat_id, 'Results history is not supported at this time.')

if __name__ == "__main__":
    if USE_POLLING:
        bot.remove_webhook()
        while True:
            try:
                bot.polling(non_stop=True)
            except Exception as e:
                print(e)
    else:
        PORT = int(os.environ.get('PORT', 5000))
        server.run(host="0.0.0.0", port=PORT)
