# PokemonArcade
Discord Bot to play Pokemon on Discord, Written with PyBoy and Discord.py.

For the most part discontinued. I might fix an issue here or there but I am not going to change anything significantly. 

This is because of the following reasons:
- PyBoy is a blocking process, Pokemon Arcade does not take into consideration multiprocessing. This causes the bot to behave slowly even on capable hardware.
- Since buttons were released after this was developed it would require essentially a full rewrite to make that work.
- Others have developed similar bots after mine with tons better features and speed. I do not feel the need to keep developing this as there are better alternatives available.

Currently no singleplayer Windows compatibility, becuase of the use of os.system calls with mv and ln commands. (If you can find and make a working fix, please do a pull request. I will review them occasionally.)
