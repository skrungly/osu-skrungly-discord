# osu!skrungly discord bot

this is our little discord bot for interacting with the osu!skrungly [server](https://github.com/skrungly/bancho.py/) and [api](https://github.com/skrungly/osu-skrungly-api) services!

## setup and deployment

to run your own instance of this bot, start by cloning the repository:

```sh
$ git clone https://github.com/skrungly/osu-skrungly-discord.git
$ cd osu-skrungly-discord
```

then make a copy of the `.env.example` config and set variables as needed:

```sh
$ cp .env.example .env
$ nano .env  # use any editor you like!
```

you can now choose to launch the bot manually or using `docker compose`.

### automatic setup using `docker compose`

with docker installed, you can launch the discord bot using `compose`:

```sh
$ docker compose up --build -d
```

### manual setup using `venv`

ensure that you have python 3.13 installed:

```sh
$ python -V
```

then use the `venv` module to create a virtual environment:

```sh
$ python -m venv .venv
$ source .venv/bin/activate  # whenever you want to use the venv
$ pip install -r requirements.txt
```

you're now ready to launch the discord bot! it's as simple as

```sh
$ python -m bot
```

## contributing

if you'd like to make a contribution, the only expectation currently is that your code should conform to [PEP 8](https://peps.python.org/pep-0008/) styling. you can check this by running (from the project root directory):

```sh
$ flake8 bot/
```

if `flake8` didn't produce any complaints then you're good to go! however, it's very easy to forget this check before committing so you should also set up the automatic pre-commit hook like so:

```sh
$ pre-commit install
```

now your code must pass the `flake8` check before being committed to this repository :D
