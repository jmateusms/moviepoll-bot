import os
import re
import bs4
import requests
import pickle
import psycopg2
import random
from urllib.parse import urlparse
from collections import defaultdict

# list of exclamations
exclamations = [
    "Mamma mia!", "Holy moly!", "Boo-yah!", "Hoo ah!", "Holy smokes!", "Zoinks!",
    "Bingo!", "Dang!", "Rosebud!", "It's alive!", "Hot damn!", "Cowabunga!",
    "D'oh!", "Yabba dabba doo!", "Holy cow!"
]
reroll_exclamations = [
    "This! Is! REROLL!!", "I am your reroll!",
    "Not the reroll! No, not the reroll!!", "Leave the gun. Take the reroll.",
    "No, it's a cardigan, but thanks for noticing!",
    "Gentlemen, you can't fight in here. This is the reroll room.",
    "Excuse me. I believe you have my reroll.",
    "It's not a man purse. It's called a reroll. Indiana Jones wears one.",
    "You sit on a throne of rerolls.", "So you're telling me there's a chance…",
    "Tina, you fat lard! Come get some reroll! Tina, eat. Reroll. Eat the reroll!",
    "Keep the reroll, ya filthy animal.", "Really, really ridiculously good-rerolling.",
    "That reroll really tied the room together, did it not?",
    "We get the warhead and we hold the world ransom for... One million rerolls.",
    "Very nice! Great reroll!",
    "I'm about to do to you what Limp Bizkit did to music in the late '90s."
]
vote_lines = [
    "The choice is an illusion. You already know what you have to do.",
    "Gods don't have to choose. We take.", "The hardest choices require the strongest wills.",
    "We must face the choice between what is right and what is easy.",
    "You always have a choice. You just happen to make the wrong f***ing one.",
    "We are who we choose to be. Now choose!", "I am made of bourbon and poor choices.",
    "Killing is making a choice.", "We don't choose the things we believe in, they choose us.",
    "Choice is an illusion, created between those with power and those without."
]

# functions
def ordinal(x):
    """
    Convert a number to its ordinal representation.
    """
    if x % 100 // 10 == 1:
        suffix = "th"
    else:
        suffix = ["th", "st", "nd", "rd", "th"][min(x % 10, 4)]
    return str(x) + suffix

def getHTML(url):
    '''
    Get HTML from url
    '''
    response = requests.get(url, headers = {"Accept-Language": "en-US", 'User-Agent': 'Mozilla/5.0'})
    return response.text

def get_soup(html):
    '''
    Get soup from html
    '''
    soup = bs4.BeautifulSoup(html, 'html.parser')
    return soup

def get_tt(string):
    '''
    Extract tt imdb tag from string.
    '''
    re_match = re.search("[t][t][0-9]{7,8}", string)
    if re_match is not None:
        return re_match.group(0)
    else:
        return None

def get_title(soup):
    '''
    Get title from soup
    '''
    title = soup.find('h1').text
    return title

def imdb_url(tt):
    '''
    Create imdb url from tt
    '''
    if get_tt(tt) is not None:
        return f"https://www.imdb.com/title/{tt}/"
    else:
        return None

def get_unique_id(chat_id, user_id):
    '''
    Get unique id from chat_id and user_id
    '''
    return f"{chat_id}_{user_id}"

class sql_mem:
    '''
    Bot "memory". Synced to SQL database.
    '''

    def __init__(self, DATABASE_URL):
        self.DATABASE_URL = DATABASE_URL
        self.get_database_connection()
        self.initialize_database()

    def get_database_connection(self):
        '''
        Get database connection.
        '''
        result = urlparse(self.DATABASE_URL)
        username = result.username
        password = result.password
        database = result.path[1:]
        hostname = result.hostname
        port = result.port
        
        self.connection = psycopg2.connect(
            database = database,
            user = username,
            password = password,
            host = hostname,
            port = port
        )
        self.cursor = self.connection.cursor()

    def initialize_database(self):
        '''
        Create tables for the bot in the database.
        '''
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS user_choices "\
            "(unique_id TEXT PRIMARY KEY, user_id TEXT, chat_id TEXT, username TEXT, "\
                "tt TEXT, url TEXT, title TEXT);")
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS users_voted "\
            "(unique_user_chat TEXT PRIMARY KEY, user_id TEXT, chat_id TEXT, option_id INT);")
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS polls "\
            "(chat_id TEXT PRIMARY KEY, poll_id TEXT, msg_id TEXT, poll_active BOOLEAN);")
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS poll_counts "\
            "(unique_title TEXT PRIMARY KEY, chat_id TEXT, poll_id TEXT, "\
                "option_id INT, title TEXT, count INT);")
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS enable_results "\
            "(chat_id TEXT PRIMARY KEY, enable_results BOOLEAN);")
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS results "\
            "(unique_tt TEXT PRIMARY KEY, chat_id TEXT, tt TEXT, url TEXT, title TEXT, "\
                "polls_count INT, votes_count INT, wins_count INT, last_poll DATE, last_win DATE);")
        self.connection.commit()
    
    def add_choice(self, unique_id, user_id, chat_id, username, tt, url, title):
        '''
        Add choice to memory.
        '''
        self.cursor.execute(
                "SELECT * FROM user_choices WHERE unique_id = %s", (unique_id,))
        if self.cursor.rowcount > 0:
            self.cursor.execute(
                """UPDATE user_choices
                SET user_id = %s, chat_id = %s, username = %s, tt = %s, url = %s, title = %s
                WHERE unique_id = %s;""", (str(user_id), str(chat_id), username, tt, url, title, unique_id))
        else:
            self.cursor.execute(
                """INSERT INTO user_choices
                (unique_id, user_id, chat_id, username, tt, url, title)
                VALUES (%s, %s, %s, %s, %s, %s, %s);""",
                (unique_id, str(user_id), str(chat_id), username, tt, url, title))
        self.connection.commit()
    
    def delete_choice(self, unique_id):
        '''
        Delete choice from memory. Returns True if successful, False otherwise.
        '''
        self.cursor.execute(
                "DELETE FROM user_choices WHERE unique_id = %s;", (unique_id,))
        self.connection.commit()
        if self.cursor.rowcount > 0:
            return True
        else:
            return False
    
    def delete_by_title(self, chat_id, title):
        '''
        Delete choice from memory. Returns True if successful, False otherwise.
        '''
        self.cursor.execute(
                "DELETE FROM user_choices WHERE chat_id = %s AND title = %s;", (str(chat_id), title))
        self.connection.commit()
        if self.cursor.rowcount > 0:
            return True
        else:
            return False
    
    def delete_all_choices(self, chat_id):
        '''
        Delete all choices from memory. Returns True if successful, False otherwise.
        '''
        result = False
        
        self.cursor.execute("DELETE FROM user_choices WHERE chat_id = %s;", (str(chat_id),))
        if self.cursor.rowcount > 0:
            result = True
        self.cursor.execute("DELETE FROM users_voted WHERE chat_id = %s;", (str(chat_id),))
        if self.cursor.rowcount > 0:
            result = True
        self.cursor.execute("DELETE FROM poll_counts WHERE chat_id = %s;", (str(chat_id),))
        if self.cursor.rowcount > 0:
            result = True
        self.cursor.execute("UPDATE polls SET poll_active = FALSE WHERE chat_id = %s;", (str(chat_id),))
        if self.cursor.rowcount > 0:
            result = True

        self.connection.commit()

        return result
    
    def get_choices(self, chat_id):
        '''
        Get choices for a chat.
        '''
        self.cursor.execute(
            "SELECT * FROM user_choices WHERE chat_id = %s;", (str(chat_id),))
        try:
            return self.cursor.fetchall()
        except:
            return None
    
    def add_poll(self, chat_id, poll_id, msg_id, titles, tts):
        '''
        Add poll to memory.
        '''
        unique_titles = [get_unique_id(str(chat_id), i) for i in range(len(titles))]
        unique_tts = [get_unique_id(str(chat_id), tt) for tt in tts]
        urls = [imdb_url(tt) for tt in tts]
        
        self.cursor.execute("SELECT * FROM polls WHERE chat_id = %s", (str(chat_id),))
        if self.cursor.rowcount > 0:
            self.cursor.execute(
                """UPDATE polls
                SET poll_id = %s, msg_id = %s, poll_active = %s
                WHERE chat_id = %s;""", (poll_id, msg_id, True, str(chat_id)))
        else:
            self.cursor.execute(
                """INSERT INTO polls
                (chat_id, poll_id, msg_id, poll_active)
                VALUES (%s, %s, %s, %s);""", (str(chat_id), poll_id, msg_id, True))
        
        self.cursor.execute(
            "DELETE FROM poll_counts WHERE chat_id = %s;", (str(chat_id),))
        for i in range(len(titles)):
            self.cursor.execute(
                """INSERT INTO poll_counts
                (unique_title, chat_id, poll_id, option_id, title, count)
                VALUES (%s, %s, %s, %s, %s, %s);""",
                (unique_titles[i], str(chat_id), poll_id, i, titles[i], 0))
        
            self.cursor.execute(
                "SELECT enable_results FROM enable_results WHERE chat_id = %s;", (str(chat_id),))
            if self.cursor.rowcount > 0:
                enable_results = self.cursor.fetchone()[0]
                if enable_results:
                    self.cursor.execute(
                        "SELECT * FROM results WHERE unique_tt = %s;", (unique_tts[i],))
                    if self.cursor.rowcount > 0:
                        self.cursor.execute(
                            """UPDATE results
                            SET polls_count = polls_count + 1, last_poll = CAST(CURRENT_TIMESTAMP AS DATE)
                            WHERE unique_tt = %s;""", (unique_tts[i],))
                    else:
                        self.cursor.execute(
                            """INSERT INTO results
                            (unique_tt, chat_id, tt, url, title, polls_count, votes_count, wins_count, last_poll, last_win)
                            VALUES (%s, %s, %s, %s, %s, 1, 0, 0, CAST(CURRENT_TIMESTAMP AS DATE), NULL);""",
                            (unique_tts[i], str(chat_id), tts[i], urls[i], titles[i]))
        
        self.connection.commit()
    
    def get_chat_from_poll(self, poll_id):
        '''
        Check if poll exists. Returns chat_id if exists, None otherwise.
        '''
        self.cursor.execute(
            "SELECT chat_id FROM polls WHERE poll_id = %s AND poll_active = %s;", (poll_id, True))
        try:
            return self.cursor.fetchone()[0]
        except:
            return None
    
    def get_msg_from_poll(self, poll_id):
        '''
        Check if poll exists. Returns msg_id if exists, None otherwise.
        '''
        self.cursor.execute(
            "SELECT msg_id FROM polls WHERE poll_id = %s AND poll_active = %s;", (poll_id, True))
        try:
            return self.cursor.fetchone()[0]
        except:
            return None
    
    def add_vote(self, chat_id, user_id, option_id):
        '''
        Register vote. Save user to users_voted and choice to poll_counts.
        '''
        unique_title = get_unique_id(str(chat_id), option_id)
        unique_user_chat = get_unique_id(str(user_id), str(chat_id))

        self.cursor.execute(
            "SELECT * FROM users_voted WHERE unique_user_chat = %s;", (unique_user_chat,))
        if self.cursor.rowcount > 0:
            self.cursor.execute(
                """UPDATE users_voted
                SET option_id = %s
                WHERE unique_user_chat = %s;""", (option_id, unique_user_chat))
        else:
            self.cursor.execute(
                """INSERT INTO users_voted
                (unique_user_chat, user_id, chat_id, option_id)
                VALUES (%s, %s, %s, %s);""", (unique_user_chat, str(user_id), str(chat_id), option_id))
        self.cursor.execute(
            "UPDATE poll_counts SET count = count + 1 WHERE unique_title = %s;", (unique_title,))
        
        self.cursor.execute(
            "SELECT enable_results FROM enable_results WHERE chat_id = %s;", (str(chat_id),))
        if self.cursor.rowcount > 0:
            enable_results = self.cursor.fetchone()[0]
            if enable_results:
                self.cursor.execute(
                    "SELECT title FROM poll_counts WHERE unique_title = %s;", (unique_title,))
                title = self.cursor.fetchone()[0]
                self.cursor.execute(
                    "SELECT tt FROM user_choices WHERE title = %s AND chat_id = %s;", (title, str(chat_id)))
                tt = self.cursor.fetchone()[0]
                unique_tt = get_unique_id(str(chat_id), tt)
                self.cursor.execute(
                    "UPDATE results SET votes_count = votes_count + 1 WHERE unique_tt = %s;", (unique_tt,))
        
        self.connection.commit()
    
    def remove_vote(self, chat_id, user_id):
        '''
        Recount vote for that user. If option_id differs from existing vote, delete old vote.
        '''
        unique_user_chat = get_unique_id(str(user_id), str(chat_id))
        
        self.cursor.execute(
            "SELECT option_id FROM users_voted WHERE unique_user_chat = %s;", (unique_user_chat,))
        if self.cursor.rowcount > 0:
            option_id = self.cursor.fetchone()[0]
            unique_title = get_unique_id(str(chat_id), option_id)
            self.cursor.execute(
                "DELETE FROM users_voted WHERE unique_user_chat = %s;", (unique_user_chat,))
            self.cursor.execute(
                "UPDATE poll_counts SET count = count - 1 WHERE unique_title = %s;",
                (unique_title,))

            self.cursor.execute(
                "SELECT enable_results FROM enable_results WHERE chat_id = %s;", (str(chat_id),))
            if self.cursor.rowcount > 0:
                enable_results = self.cursor.fetchone()[0]
                if enable_results:
                    self.cursor.execute(
                        "SELECT tt FROM user_choices WHERE unique_id = %s;", (unique_title,))
                    tt = self.cursor.fetchone()[0]
                    unique_tt = get_unique_id(str(chat_id), tt)
                    self.cursor.execute(
                        "UPDATE results SET votes_count = votes_count - 1 WHERE unique_tt = %s;",
                        (unique_tt,))
            
            self.connection.commit()
    
    def check_user_vote(self, chat_id, user_id):
        '''
        Check if user has voted.
        '''
        unique_user_chat = get_unique_id(str(user_id), str(chat_id))
        self.cursor.execute(
            "SELECT * FROM users_voted WHERE unique_user_chat = %s;", (unique_user_chat,))
        if self.cursor.rowcount > 0:
            return True
        else:
            return False
    
    def check_poll_complete(self, chat_id):
        '''
        Check if poll is complete.
        If all users in user_choices are present in users_voted, return True. False otherwise.
        '''
        self.cursor.execute(
            "SELECT user_id FROM users_voted WHERE chat_id = %s;", (str(chat_id),))
        users_voted = self.cursor.fetchall()
        self.cursor.execute(
            "SELECT user_id FROM user_choices WHERE chat_id = %s;", (str(chat_id),))
        users_choices = self.cursor.fetchall()
        # check if all users in user_choices are present in users_voted
        for user in users_choices:
            if user not in users_voted and user[0] != '0':
                return False
        return True
    
    def get_poll_winner(self, chat_id):
        '''
        Check which option has the most votes.
        Return movie title if there is a single winner.
        If there is a tie, return None.
        '''
        self.cursor.execute(
            "SELECT option_id, count, title FROM poll_counts WHERE chat_id = %s;", (str(chat_id),))
        
        counts = self.cursor.fetchall()
        max_votes = max([i[1] for i in counts])
        winners = [i[2] for i in counts if i[1] == max_votes]
        
        if len(winners) > 1:
            return None
        else:
            return winners[0]
    
    def random_poll_winner(self, chat_id, reroll_chance=None):
        '''
        If there is a tie, randomly select a winner.
        Returns a reroll_chance and winner movie title.
        Returns None if there is a reroll.
        '''
        self.cursor.execute(
            "SELECT option_id, count, title FROM poll_counts WHERE chat_id = %s;", (str(chat_id),))
        
        counts = self.cursor.fetchall()
        max_votes = max([i[1] for i in counts])
        winners = [i[2] for i in counts if i[1] == max_votes]
        
        if len(winners) > 1:
            if reroll_chance is None:
                reroll_slots = random.choice(list(range(1, len(winners) + 1)))
            else:
                reroll_slots = int(len(winners) * reroll_chance / (1 - reroll_chance))
            
            choices = winners + [None] * reroll_slots
            reroll_chance = 100 * reroll_slots / len(choices)

            winner = random.choice(choices)
        
        elif len(winners) == 1:
            winner = winners[0]
        else:
            return None
        
        return reroll_chance, winner
    
    def end_poll(self, chat_id):
        '''
        Disable poll and delete all choices, users_voted and poll_counts.
        '''
        self.cursor.execute(
            "UPDATE polls SET poll_active = %s WHERE chat_id = %s;", (False, str(chat_id)))
        self.cursor.execute(
            "DELETE FROM user_choices WHERE chat_id = %s;", (str(chat_id),))
        self.cursor.execute(
            "DELETE FROM users_voted WHERE chat_id = %s;", (str(chat_id),))
        self.cursor.execute(
            "DELETE FROM poll_counts WHERE chat_id = %s;", (str(chat_id),))
        
        self.connection.commit()
    
    def random_winner(self, chat_id, reroll_chance=None):
        '''
        Randomly select a winner from current choices.
        '''
        self.cursor.execute(
            "SELECT title FROM user_choices WHERE chat_id = %s;", (str(chat_id),))
        choices = self.cursor.fetchall()
        
        if len(choices) == 0:
            return None

        if reroll_chance is None:
            reroll_slots = random.choice(list(range(1, len(choices) + 1)))
        else:
            reroll_slots = int(len(choices) * reroll_chance / (1 - reroll_chance))
        
        choices = choices + [None] * reroll_slots
        reroll_chance = 100 * reroll_slots / len(choices)

        winner = random.choice(choices)[0]
        
        return reroll_chance, winner
    
    def results_win(self, chat_id, title):
        '''
        Register win for a movie.
        '''
        self.cursor.execute(
            "SELECT tt FROM user_choices WHERE chat_id = %s AND title = %s;", (str(chat_id), title))
        tt = self.cursor.fetchone()[0]
        unique_tt = get_unique_id(str(chat_id), tt)

        self.cursor.execute(
            """UPDATE results
            SET last_win = CAST(CURRENT_TIMESTAMP AS DATE), wins_count = wins_count + 1
            WHERE unique_tt = %s;"""
            , (unique_tt,))
        self.connection.commit()
    
    def enable_results(self, chat_id):
        '''
        Enable results for a chat. Returns True if successful.
        If results is already enabled, returns False.
        '''
        self.cursor.execute(
            "SELECT enable_results FROM enable_results WHERE chat_id = %s;", (str(chat_id),))
        if self.cursor.rowcount > 0:
            if self.cursor.fetchone()[0] == True:
                return False
            else:
                self.cursor.execute(
                    "UPDATE enable_results SET enable_results = %s WHERE chat_id = %s;", (True, str(chat_id)))
                self.connection.commit()
                return True
        else:
            self.cursor.execute(
                "INSERT INTO enable_results (chat_id, enable_results) VALUES (%s, %s);", (str(chat_id), True))
            self.connection.commit()
            return True
    
    def disable_results(self, chat_id):
        '''
        Disable results for a chat. Returns True if successful.
        If results is already disabled, returns False.
        '''
        self.cursor.execute(
            "SELECT enable_results FROM enable_results WHERE chat_id = %s;", (str(chat_id),))
        if self.cursor.rowcount > 0:
            if self.cursor.fetchone()[0] == False:
                return False
            else:
                self.cursor.execute(
                    "UPDATE enable_results SET enable_results = %s WHERE chat_id = %s;", (False, str(chat_id)))
                self.connection.commit()
                return True
        else:
            self.cursor.execute(
                "INSERT INTO enable_results (chat_id, enable_results) VALUES (%s, %s);", (str(chat_id), False))
            self.connection.commit()
            return True
    
    def results_enabled(self, chat_id):
        '''
        Check if results are enabled for a chat.
        '''
        self.cursor.execute(
            "SELECT enable_results FROM enable_results WHERE chat_id = %s;", (str(chat_id),))
        if self.cursor.rowcount > 0:
            return self.cursor.fetchone()[0]
        else:
            return False
    
    def get_results(self, chat_id):
        '''
        Get results for a chat.
        '''
        self.cursor.execute(
            "SELECT * FROM results WHERE chat_id = %s;", (str(chat_id),))
        return self.cursor.fetchall()
    
    def clear_results(self, chat_id):
        '''
        Remove all results from given chat.
        '''
        self.cursor.execute(
            "DELETE FROM results WHERE chat_id = %s;", (str(chat_id),))
        self.connection.commit()

    def reset_database(self):
        '''
        Reset database.
        '''
        self.cursor.execute("DROP TABLE user_choices;")
        self.cursor.execute("DROP TABLE users_voted;")
        self.cursor.execute("DROP TABLE polls;")
        self.cursor.execute("DROP TABLE poll_counts;")
        self.connection.commit()

        self.initialize_database()
    
    def reset_prefs(self):
        '''
        Reset enable_results table.
        '''
        self.cursor.execute("DROP TABLE enable_results;")
        self.connection.commit()

        self.initialize_database()

    def reset_results(self):
        '''
        Reset results database.
        '''
        self.cursor.execute("DROP TABLE results;")
        self.connection.commit()

        self.initialize_database()

# classes
class local_mem:
    '''
    Bot "memory". Synced to local files.
    '''
    def __init__(self):
        self.load_mem()
    
    def create_mem(self):
        '''
        Create memory. Objects are pickle files.
        '''
        if os.path.isdir('mem') == False:
            os.mkdir('mem')	
        self.user_choices = defaultdict(dict)
        self.users_voted = defaultdict(dict)
        self.last_poll = defaultdict(dict)
        self.poll_chats = {}
        self.poll_counts = defaultdict(dict)
        self.sync_mem()

    def load_mem(self):
        '''
        Load memory from mem folder. Objects are pickle files.
        '''
        if os.path.exists('mem/user_choices.pkl') and \
            os.path.exists('mem/users_voted.pkl') and \
                os.path.exists('mem/last_poll.pkl') and \
                    os.path.exists('mem/poll_chats.pkl') and \
                        os.path.exists('mem/poll_counts.pkl'):
            with open('mem/user_choices.pkl', 'rb') as f:
                self.user_choices = pickle.load(f)
            with open('mem/users_voted.pkl', 'rb') as f:
                self.users_voted = pickle.load(f)
            with open('mem/last_poll.pkl', 'rb') as f:
                self.last_poll = pickle.load(f)
            with open('mem/poll_chats.pkl', 'rb') as f:
                self.poll_chats = pickle.load(f)
            with open('mem/poll_counts.pkl', 'rb') as f:
                self.poll_counts = pickle.load(f)
        else:
            self.create_mem()

    def sync_mem(self):
        '''
        Sync memory with mem folder. Objects are pickle files.
        '''
        with open('mem/user_choices.pkl', 'wb') as f:
            pickle.dump(self.user_choices, f)
        with open('mem/users_voted.pkl', 'wb') as f:
            pickle.dump(self.users_voted, f)
        with open('mem/last_poll.pkl', 'wb') as f:
            pickle.dump(self.last_poll, f)
        with open('mem/poll_chats.pkl', 'wb') as f:
            pickle.dump(self.poll_chats, f)
        with open('mem/poll_counts.pkl', 'wb') as f:
            pickle.dump(self.poll_counts, f)
