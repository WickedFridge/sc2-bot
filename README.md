<<<<<<< HEAD
# probots-sc2-bot-template

Use this template to start a new Starcraft 2 bot using the [python-sc2](https://github.com/BurnySc2/python-sc2) framework.  
Then, if you need, follow the tutorial below.  

# Tutorial: Starting a python-sc2 bot

## Preparing your environment

First you will need to prepare your environment.

### Prerequisites

##### Python

This tutorial recommends you use Python version 3.8.X.
However, newer Python versions should also work with this tutorial.
[Python downloads page](https://www.python.org/downloads/)

##### Git

This tutorial will use git for version control.  
[Git downloads page](https://git-scm.com/downloads)

##### Starcraft 2

On Windows SC2 is installed through the Battle.net app.  
Linux users can either download the Blizzard SC2 Linux package [here](https://github.com/Blizzard/s2client-proto#linux-packages) or, alternatively, set up Battle.net via WINE using this [lutris script](https://lutris.net/games/battlenet/).

SC2 should be installed in the default location. Otherwise (and for Linux) you might need to create the SC2PATH environment variable to point to the SC2 install location.

## Environment Setup for Linux (Lutris)

If you've installed StarCraft II using Lutris on Linux, you'll need to set some environment variables so that the `python-sc2` library can correctly interact with the game.

### Setting Environment Variables Temporarily

Open a terminal and enter the following commands, replacing `(username)` with your actual Linux username and `(version of wine)` with the version of Wine that Lutris is using:

```bash
export SC2PF=WineLinux
export SC2PATH="/home/`(username)`/Games/battlenet/drive_c/Program Files (x86)/StarCraft II/"
export WINE="/home/`(username)`/.local/share/lutris/runners/wine/`(version of wine)`/bin/wine" 
```

##### Starcraft 2 Maps

Download the Starcraft 2 Maps from [here](https://github.com/Blizzard/s2client-proto#map-packs).   For this tutorial you will at least need the 'Melee' pack.  
The maps must be copied into the **root** of the Starcraft 2 maps folder - default location: `C:\Program Files (x86)\StarCraft II\Maps`.

## Creating your bot
### Setup
Click the green `Use this template` button above to create your own copy of this bot.  
Now clone your new repository to your local computer using git:
```bash
git clone <your_git_clone_repo_url_here>
```
cd into your bot directory:
```bash
cd <bot_folder_name_here>
```
Create and activate a virtual environment:
```bash
python -m venv venv
# and then...
venv\Scripts\activate # Windows CMD Prompt / PowerShell
source venv/bin/activate # Mac OS / Linux
```
Install our bot's Python requirements:
```bash
pip install -r requirements.txt
```
Test our bot is working by running it:
```bash
python ./run.py
```
If all is well, you should see SC2 load and your bot start mining minerals.  
You can close the SC2 window to stop your bot running. 

## Updating your bot

### Bot name and race

Now you will want to name your bot and select its race.
You can specify both of these in the [bot/bot.py](bot/bot.py) file, in the `CompetitiveBot` class.

### Adding new code

As you add features to your bot make sure all your new code files are in the `bot` folder. This folder is included when creating the ladder.zip for upload to the bot ladders.

## Upgrading to Ares Framework

Ares-sc2 is a library that extends python-sc2, offering advanced tools and functionalities to give you greater control over your bot's strategic decisions. If you want more sophisticated and nuanced gameplay tactics, upgrading to Ares-sc2 is the way to go.

### Running the Upgrade Script

Run the following command:
```bash
python upgrade_to_ares.py
```

### Code Changes

#### Updating the Bot Object

The main bot object should inherit from `ares-sc2` instead of `python-sc2`.

**python-sc2:**
```python
from sc2.bot_ai import BotAI

class MyBot(BotAI):
    pass
```

**ares-sc2:**
```python
from ares import AresBot

class MyBot(AresBot):
    pass
```

#### Adding Super Calls to Hook Methods

For any `python-sc2` hook methods you use, add a `super` call. Only convert the hooks you actually use.

**python-sc2:**
```python
class MyBot(AresBot):
    async def on_step(self, iteration: int) -> None:
        pass

    async def on_start(self, iteration: int) -> None:
        pass

    async def on_end(self, game_result: Result) -> None:
        pass

    async def on_building_construction_complete(self, unit: Unit) -> None:
        pass

    async def on_unit_created(self, unit: Unit) -> None:
        pass

    async def on_unit_destroyed(self, unit_tag: int) -> None:
        pass

    async def on_unit_took_damage(self, unit: Unit, amount_damage_taken: float) -> None:
        pass
```

**ares-sc2:**
```python
class MyBot(AresBot):
    async def on_step(self, iteration: int) -> None:
        await super(MyBot, self).on_step(iteration)
        # on_step logic here ...

    async def on_start(self, iteration: int) -> None:
        await super(MyBot, self).on_start(iteration)
        # on_start logic here ...

    async def on_end(self, game_result: Result) -> None:
        await super(MyBot, self).on_end(game_result)
        # custom on_end logic here ...

    async def on_building_construction_complete(self, unit: Unit) -> None:
        await super(MyBot, self).on_building_construction_complete(unit)
        # custom on_building_construction_complete logic here ...

    async def on_unit_created(self, unit: Unit) -> None:
        await super(MyBot, self).on_unit_created(unit)
        # custom on_unit_created logic here ...

    async def on_unit_destroyed(self, unit_tag: int) -> None:
        await super(MyBot, self).on_unit_destroyed(unit_tag)
        # custom on_unit_destroyed logic here ...

    async def on_unit_took_damage(self, unit: Unit, amount_damage_taken: float) -> None:
        await super(MyBot, self).on_unit_took_damage(unit, amount_damage_taken)
        # custom on_unit_took_damage logic here ...
```

## Competing with your bot

To compete with your bot, you will first need zip up your bot, ready for distribution.   
You can do this using the `create_ladder_zip.py` script like so:
```
python create_ladder_zip.py
```
This will create the zip file`publish\bot.zip`.
You can then distribute this zip file to competitions.
=======
[![Actions Status](https://github.com/BurnySc2/python-sc2/workflows/Tests/badge.svg)](https://github.com/BurnySc2/python-sc2/actions)
[![codecov](https://codecov.io/gh/BurnySc2/python-sc2/branch/develop/graph/badge.svg?token=Pq5XkKw5VC)](https://codecov.io/gh/BurnySc2/python-sc2)

# A StarCraft II API Client for Python 3

An easy-to-use library for writing AI Bots for StarCraft II in Python 3. The ultimate goal is simplicity and ease of use, while still preserving all functionality. A really simple worker rush bot should be no more than twenty lines of code, not two hundred. However, this library intends to provide both high and low level abstractions.

**This library (currently) covers only the raw scripted interface.** At this time I don't intend to add support for graphics-based interfaces.

The [documentation can be found here](https://burnysc2.github.io/python-sc2/index.html).
For bot authors, looking directly at the files in the [sc2 folder](/sc2) can also be of benefit: bot_ai.py, unit.py, units.py, client.py, game_info.py and game_state.py. Most functions in those files have docstrings, example usages and type hinting.

I am planning to change this fork more radically than the main repository, for bot performance benefits and to add functions to help new bot authors. This may break older bots in the future, however I try to add deprecation warnings to give a heads up notification. This means that the [video tutorial made by sentdex](https://pythonprogramming.net/starcraft-ii-ai-python-sc2-tutorial/) is outdated and does no longer directly work with this fork.

For a list of ongoing changes and differences to the main repository of Dentosal, [check here](https://github.com/BurnySc2/python-sc2/issues/4).

## Installation

By installing this library you agree to be bound by the terms of the [AI and Machine Learning License](http://blzdistsc2-a.akamaihd.net/AI_AND_MACHINE_LEARNING_LICENSE.html).

For this fork, you'll need Python 3.9 or newer.

Install the pypi package:
```
pip install --upgrade burnysc2
```
or directly from develop branch:
```
pip install --upgrade --force-reinstall https://github.com/BurnySc2/python-sc2/archive/develop.zip
```
Both commands will use the `sc2` library folder, so you will not be able to have Dentosal's and this fork installed at the same time, unless you use virtual environments.

## StarCraft II
You'll need a StarCraft II executable. If you are running Windows or macOS, just install SC2 from [blizzard app](https://starcraft2.com/).

### Linux installation

You can install StarCraft II on Linux with [Wine](https://www.winehq.org/), [Lutris](https://lutris.net/games/battlenet/) or even the [Linux binary](https://github.com/Blizzard/s2client-proto#downloads), but the latter is headless so you cannot actually see the game.
Starcraft II can be directly installed from Battlenet once it is downloaded with Lutris.
By default, it will be installed here:
```
/home/burny/Games/battlenet/drive_c/Program Files (x86)/StarCraft II/
```
Next, set the following environment variables (either globally or within your development environment, e.g. Pycharm: `Run -> Edit Configurations -> Environment Variables`):

```
SC2PF=WineLinux
WINE=/usr/bin/wine
# Or a wine binary from lutris:
# WINE=/home/burny/.local/share/lutris/runners/wine/lutris-4.20-x86_64/bin/wine64
# Default Lutris StarCraftII Installation path:
SC2PATH='/home/burny/Games/battlenet/drive_c/Program Files (x86)/StarCraft II/'
```

### WSL

When running WSL in Windows, python-sc2 detects WSL by default and starts Windows Starcraft 2 instead of Linux Starcraft 2.
If you wish to instead have the game played in Linux, you can disable this behavior by setting `SC2_WSL_DETECT`
environment variable to "0". You can do this inside python with the following code:
```py
import os
os.environ["SC2_WSL_DETECT"] = "0"
```  

WSL version 1 should not require any configuration. You may be asked to allow Python through your firewall.

When running WSL version 2 you need to supply the following environment variables so that your bot can connect:

```
SC2CLIENTHOST=<your windows IP>
SC2SERVERHOST=0.0.0.0
```

If you are adding these to your .bashrc, you may need to export your environment variables by adding:
```sh
export SC2CLIENTHOST
export SC2SERVERHOST
```

You can find your Windows IP using `ipconfig /all` from `PowerShell.exe` or `CMD.exe`.

## Maps
You will need maps to run the library.

#### Official maps
Official Blizzard map downloads are available from [Blizzard/s2client-proto](https://github.com/Blizzard/s2client-proto#downloads).  
Extract these maps into their respective *subdirectories* in the SC2 maps directory.  
e.g. `install-dir/Maps/Ladder2017Season1/`

#### Bot ladder maps
Maps that are run on the [SC2 AI Arena Ladder](https://aiarena.net/) can be downloaded [from the SC2 AI Arena Wiki](https://aiarena.net/wiki/bot-development/getting-started/#wiki-toc-maps).   
**Extract these maps into the *root* of the SC2 maps directory** (otherwise ladder replays won't work).  
e.g. `install-dir/Maps/AcropolisLE.SC2Map`

### Running

After installing the library, a StarCraft II executable, and some maps, you're ready to get started. Simply run a bot file to fire up an instance of StarCraft II with the bot running. For example:

```sh
python examples/protoss/cannon_rush.py
```

## Example

As promised, worker rush in less than twenty lines:

```python
from sc2 import maps
from sc2.player import Bot, Computer
from sc2.main import run_game
from sc2.data import Race, Difficulty
from sc2.bot_ai import BotAI

class WorkerRushBot(BotAI):
    async def on_step(self, iteration: int):
        if iteration == 0:
            for worker in self.workers:
                worker.attack(self.enemy_start_locations[0])

run_game(maps.get("Abyssal Reef LE"), [
    Bot(Race.Zerg, WorkerRushBot()),
    Computer(Race.Protoss, Difficulty.Medium)
], realtime=True)
```

This is probably the simplest bot that has any realistic chances of winning the game. I have ran it against the medium AI a few times, and once in a while, it wins.

You can find more examples in the [`examples/`](/examples) folder.

## API Configuration Options

The API supports a number of options for configuring how it operates.

### `unit_command_uses_self_do`
Set this to 'True' if your bot is issueing commands using `self.do(Unit(Ability, Target))` instead of `Unit(Ability, Target)`.
```python
class MyBot(BotAI):
    def __init__(self):
        self.unit_command_uses_self_do = True
```

### `raw_affects_selection`
Setting this to true improves bot performance by a little bit.
```python
class MyBot(BotAI):
    def __init__(self):
        self.raw_affects_selection = True
```

### `distance_calculation_method`
The distance calculation method:
- 0 for raw python
- 1 for scipy pdist
- 2 for scipy cdist
```python
class MyBot(BotAI):
    def __init__(self):
        self.distance_calculation_method: int = 2
```

### `game_step`
On game start or in any frame actually, you can set the game step. This controls how often your bot's `step` method is called.  
__Do not set this in the \_\_init\_\_ function as the client will not have been initialized yet!__
```python
class MyBot(BotAI):
    def __init__(self):
        pass  # don't set it here!

    async def on_start(self):
        self.client.game_step: int = 2
```

## Community - Help and support

You have questions but don't want to create an issue? Join the [SC2 AI Arena Discord server](https://discordapp.com/invite/zXHU4wM). Questions about this repository can be asked in text channel #python. There are discussions and questions about SC2 bot programming and this repository every day.

## Bug reports, feature requests and ideas

If you have any issues, ideas or feedback, please create [a new issue](https://github.com/BurnySc2/python-sc2/issues/new). Pull requests are also welcome!


## Contributing & style guidelines

Git commit messages use [imperative-style messages](https://stackoverflow.com/a/3580764/2867076), start with capital letter and do not have trailing commas.

To run pre-commit hooks (which run autoformatting and autosort imports) you can run
```sh
uv run pre-commit install
uv run pre-commit run --all-files --hook-stage pre-push
```
>>>>>>> upstream/develop
