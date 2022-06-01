# mikepapa-bot

Mike Papa is a bot for choosing movies to watch with friends. It allows each participant to suggest a movie. The bot can create a poll with all answers or choose one at random.

Why Mike Papa? When I started building this bot, I chose that as a placeholder name and never really changed it since, I guess. Mike Papa is the [NATO phonetic alphabet](https://en.wikipedia.org/wiki/NATO_phonetic_alphabet) words for MP (movie poll). My group of movie friends think the name is bad and that's enough reason for me to keep it. :)

This is currently a work in progress, with some functions still being implemented. An instance of this bot is currently running. You can use it by adding the Telegram bot [@MikePapa_bot](http://t.me/MikePapa_bot) to a group in Telegram. This bot has privacy mode enabled, which means that the bot will only receive messages that start with the '/' symbol or mention the bot by username (see more details in [Telegram's bots introduction page](https://core.telegram.org/bots#privacy-mode)). In any case, use it at your own risk.

If you prefer, just run your own instance of the bot, by following the instructions below.

## Setup instructions

### Environment variables

In order to run the bot, you need to define the variables `TOKEN` and `OWNER_ID`. These can be added to an .env file in the root directory of the project.

- To get a `TOKEN`, you can use the [Telegram Botfather](https://telegram.me/botfather) to create your bot.
- Your `OWNER_ID` can be found by:
  - Creating an environment variable `OWNER_NAME`, which is your first name, as in Telegram.
  - Running `get_user_id.py` and sending the command `/userid` to your bot.

### Dependencies

The bot was tested in Python 3.8 and 3.10. It should work in other versions, but it's not guaranteed. To install the needed packages run:

```bash
pip install -r requirements.txt
```

### Running the bot

```bash
python mikepapa_bot.py
```

## Usage

Each user should suggest a movie for the poll with the command `/choose TAG_or_LINK`, where `TAG_or_LINK` is an IMDb "tt" tag (e.g., tt0068646) or the link to a movie in IMDb (which contains the "tt" tag).

If a user wants to vote but not suggest a movie, the command `/participate` can be used. If a (single) extra movie needs to be added to the poll (not linked to any user), the command `/extra` can be used.

Each user can clear their choice with the `/clear` command. The extra movie can be removed with the `/clearextra` command. The bot owner (defined by `OWNER_ID`) can clear all choices with the `/clearall` command.

The `/choices` command shows what each user has suggested. The `/poll` command  creates a poll with all choices. The `/random` command chooses a movie at random (with a chance of rerolling, I know it makes little sense, but this is an internal "joke" from my group of friends). If there is a tie in the poll, a random winner is chosen among the tied movies, following the same rules of the `/random` option.

```plaintext
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
```
