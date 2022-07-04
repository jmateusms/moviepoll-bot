# moviepoll-bot

This is a telegram bot for choosing movies to watch with friends. It allows each participant to suggest a movie. The bot can create a poll with all answers or choose one at random.

This is currently a work in progress, with some functions still being implemented. An instance of this bot is currently running. You can use it by adding the Telegram bot [@MoviePoll_bot](http://t.me/MoviePoll_bot) to a group in Telegram. This bot has privacy mode enabled, which means that the bot will only receive messages that start with the '/' symbol or mention the bot by username (see more details in [Telegram's bots introduction page](https://core.telegram.org/bots#privacy-mode)). In any case, use it at your own risk.

If you prefer, just run your own instance of the bot, by following the instructions below.

## Setup instructions

### Environment variables

In order to run the bot, you need to define the variables `TOKEN` and `OWNER_ID` as well as either `USE_POLLING` or `APP_URL`. Also, `DATABASE_URL` is an optional variable. These can be added to an .env file in the root directory of the project.

- To get a `TOKEN`, you can use the [Telegram Botfather](https://telegram.me/botfather) to create your bot.
- Your `OWNER_ID` can be found by:
  - Creating an environment variable `OWNER_NAME`, which is your first name, as in Telegram.
  - Running `get_user_id.py` and sending the command `/userid` to your bot.
- You can also set a `DATABASE_URL` to use a PostgreSQL database as bot memory. If this is not provided, the bot will sync to local files in disk.
- If you host your instance at a service like Heroku, you can set `APP_URL` to user webhooks. This will allow the app to be put to sleep after no interactions are made with the bot.
- If you want to use the bot in polling mode, set `USE_POLLING` to `yes`.

### Dependencies

The bot was tested in Python 3.8 and 3.10. It should work in other versions, but it's not guaranteed. To install the needed packages run:

```bash
pip install -r requirements.txt
```

### Running the bot

```bash
python moviepoll-bot.py
```

## Usage

Each user should suggest a movie for the poll with the command `/choose TAG_or_LINK`, where `TAG_or_LINK` is an IMDb "tt" tag (e.g., tt0068646) or the link to a movie in IMDb (which contains the "tt" tag).

If a user wants to vote but not suggest a movie, the command `/participate` can be used. If a (single) extra movie needs to be added to the poll (not linked to any user), the command `/extra` can be used.

Each user can clear their choice with the `/clear` command. The extra movie can be removed with the `/clearextra` command. It is also possible to clear all choices with the `/clearall` command.

The `/choices` command shows what each user has suggested. The `/poll` command  creates a poll with all choices. The `/random` command chooses a movie at random (with a chance of rerolling, I know it makes little sense, but this is an internal "joke" from my group of friends). If there is a tie in the poll, a random winner is chosen among the tied movies, following the same rules of the `/random` option.

```plaintext
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
```

## To do

- Convert dummy debug commands to use PostgreSQL database.
- Add inline functionality to search for movies in IMDb.
- Save movie winners to history (if user enables this).
