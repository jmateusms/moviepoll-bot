import os
import re
import bs4
import requests
import pickle
import psycopg2
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
    response = requests.get(url, headers = {"Accept-Language": "en-US"})
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
            "(unique_id TEXT PRIMARY KEY, user_id INT, chat_id INT, username TEXT, "\
                "tt TEXT, url TEXT, title TEXT);")
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS users_voted "\
            "(chat_id INT PRIMARY KEY, user_id INT, option_id INT);")
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS polls "\
            "(chat_id INT PRIMARY KEY, poll_id INT, poll_active BOOLEAN);")
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS poll_counts "\
            "(unique_title TEXT PRIMARY KEY, chat_id INT, poll_id INT, "\
                "option_id INT, title TEXT, count INT);")
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS enable_results "\
            "(chat_id INT PRIMARY KEY, enable_results BOOLEAN);")
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS results "\
            "(unique_tt TEXT PRIMARY KEY, chat_id INT, "\
                "tt TEXT, url TEXT, title TEXT, type TEXT, date DATE);")
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
                WHERE unique_id = %s;""", (user_id, chat_id, username, tt, url, title, unique_id))
        else:
            self.cursor.execute(
                """INSERT INTO user_choices
                (unique_id, user_id, chat_id, username, tt, url, title)
                VALUES (%s, %s, %s, %s, %s, %s, %s);""",
                (unique_id, user_id, chat_id, username, tt, url, title))
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
                "DELETE FROM user_choices WHERE chat_id = %s AND title = %s;", (chat_id, title))
        self.connection.commit()
        if self.cursor.rowcount > 0:
            return True
        else:
            return False
    
    def delete_all_choices(self, chat_id):
        '''
        Delete all choices from memory. Returns True if successful, False otherwise.
        '''
        self.cursor.execute("DELETE FROM user_choices WHERE chat_id = %s;", (chat_id,))
        self.connection.commit()
        if self.cursor.rowcount > 0:
            return True
        else:
            return False
    
    def get_choices(self, chat_id):
        '''
        Get choices for a chat.
        '''
        self.cursor.execute(
            "SELECT * FROM user_choices WHERE chat_id = %s;", (chat_id,))
        try:
            return self.cursor.fetchall()
        except:
            return None
    
    def add_poll(self, chat_id, poll_id, titles):
        '''
        Add poll to memory.
        '''
        unique_titles = [get_unique_id(chat_id, i) for i in range(len(titles))]
        
        self.cursor.execute("SELECT * FROM polls WHERE chat_id = %s", (chat_id,))
        if self.cursor.rowcount > 0:
            self.cursor.execute(
                """UPDATE polls
                SET poll_id = %s, poll_active = %s
                WHERE chat_id = %s;""", (poll_id, True, chat_id))
        else:
            self.cursor.execute(
                """INSERT INTO polls
                (chat_id, poll_id, poll_active)
                VALUES (%s, %s, %s);""", (chat_id, poll_id, True))
        
        for i in range(len(titles)):
            self.cursor.execute(
                "SELECT * FROM poll_counts WHERE unique_title = %s;", (unique_titles[i],))
            if self.cursor.rowcount > 0:
                self.cursor.execute(
                    "DELETE FROM poll_counts WHERE chat_id = %s AND unique_title = %s;",
                    (chat_id, unique_titles[i]))
            self.cursor.execute(
                """INSERT INTO poll_counts
                (unique_title, chat_id, poll_id, option_id, title, count)
                VALUES (%s, %s, %s, %s, %s, %s);""",
                (unique_titles[i], chat_id, poll_id, i, titles[i], 0))
        
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
    
    def add_vote(self, chat_id, user_id, option_id):
        '''
        Register vote. Save user to users_voted and choice to poll_counts.
        '''
        unique_title = get_unique_id(chat_id, option_id)

        self.cursor.execute(
            "SELECT * FROM users_voted WHERE user_id = %s AND chat_id = %s;", (user_id, chat_id))
        if self.cursor.rowcount > 0:
            self.cursor.execute(
                """UPDATE users_voted
                SET option_id = %s
                WHERE user_id = %s AND chat_id = %s;""", (option_id, user_id, chat_id))
        else:
            self.cursor.execute(
                """INSERT INTO users_voted
                (user_id, chat_id, option_id)
                VALUES (%s, %s, %s);""", (user_id, chat_id, option_id))
        self.cursor.execute(
            "UPDATE poll_counts SET count = count + 1 WHERE unique_title = %s;", (unique_title,))
        
        self.connection.commit()
    
    def remove_vote(self, chat_id, user_id, option_id):
        '''
        Recount vote for that user. If option_id differs from existing vote, delete old vote.
        '''
        unique_title = get_unique_id(chat_id, option_id)
        
        self.cursor.execute(
            "SELECT option_id FROM users_voted WHERE user_id = %s AND chat_id = %s;",
            (user_id, chat_id))
        if self.cursor.rowcount > 0:
            old_option_id = self.cursor.fetchone()[0]
            self.cursor.execute(
                "DELETE FROM users_voted WHERE user_id = %s AND chat_id = %s;",
                (user_id, chat_id))
            self.cursor.execute(
                "UPDATE poll_counts SET count = count - 1 WHERE unique_title = %s;",
                (unique_title,))
            self.connection.commit()
        
    def check_user_vote(self, chat_id, user_id):
        '''
        Check if user has voted.
        '''
        self.cursor.execute(
            "SELECT * FROM users_voted WHERE chat_id = %s AND user_id = %s;", (chat_id, user_id))
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
            "SELECT user_id FROM users_voted WHERE chat_id = %s;", (chat_id,))
        users_voted = self.cursor.fetchall()
        self.cursor.execute(
            "SELECT user_id FROM user_choices WHERE chat_id = %s;", (chat_id,))
        users_choices = self.cursor.fetchall()
        # check if all users in user_choices are present in users_voted
        for user in users_choices:
            if user not in users_voted and user[0] != 0:
                return False
        return True
    
    def get_poll_winner(self, chat_id):
        '''
        Check which option has the most votes.
        Return movie title if there is a single winner.
        If there is a tie, return None.
        '''
        self.cursor.execute(
            "SELECT option_id, count, title FROM poll_counts WHERE chat_id = %s;", (chat_id,))
        
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
            "SELECT option_id, count, title FROM poll_counts WHERE chat_id = %s;", (chat_id,))
        
        counts = self.cursor.fetchall()
        max_votes = max([i[1] for i in counts])
        winners = [i[2] for i in counts if i[1] == max_votes]
        
        if len(winners) > 1:
            if reroll_chance is None:
                reroll_slots = list(range(1, len(winners) + 1))
            else:
                reroll_slots = int(len(winners) * reroll_chance / (1 - reroll_chance))
            choices = winners + [None] * reroll_slots
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
            "UPDATE polls SET poll_active = %s WHERE chat_id = %s;", (False, chat_id))
        self.cursor.execute(
            "DELETE FROM user_choices WHERE chat_id = %s;", (chat_id,))
        self.cursor.execute(
            "DELETE FROM users_voted WHERE chat_id = %s;", (chat_id,))
        self.cursor.execute(
            "DELETE FROM poll_counts WHERE chat_id = %s;", (chat_id,))
        
        self.connection.commit()
    
    def random_winner(self, chat_id, reroll_chance=None):
        '''
        Randomly select a winner from current choices.
        '''
        self.cursor.execute(
            "SELECT option_id, title FROM user_choices WHERE chat_id = %s;", (chat_id,))
        choices = self.cursor.fetchall()
        
        if len(choices) == 0:
            return None

        if reroll_chance is None:
            reroll_slots = list(range(1, len(choices) + 1))
        else:
            reroll_slots = int(len(choices) * reroll_chance / (1 - reroll_chance))
        
        choices = choices + [None] * reroll_slots
        winner = random.choice(choices)
        
        return reroll_chance, winner

    def reset_database(self):
        '''
        Reset database.
        '''
        self.cursor.execute("DELETE FROM user_choices;")
        self.cursor.execute("DELETE FROM users_voted;")
        self.cursor.execute("DELETE FROM polls;")
        self.cursor.execute("DELETE FROM poll_counts;")
        self.cursor.execute("DELETE FROM enable_results;")
        self.cursor.execute("DELETE FROM results;")
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
