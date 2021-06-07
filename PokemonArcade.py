#!/usr/bin/env python3

# Pokémon Arcade, by 0xDEADCADE#9950
# Pokémon Arcade is a Discord bot to play Pokemon using embeds and reactions
#  #        ##
# #0#      #0##
# ###      ####
#  #        ##
#     #
#
#  #  ##   #
#   ##  ###

# Builtins
import os
import sys
import time
import datetime
import asyncio
import json
import hashlib

# External dependencies
import discord
from pyboy import PyBoy, WindowEvent
from PIL import Image
import PIL.ImageOps
from pyboy.logger import log_level

# Set log level to warning as to not receive messages every frame
log_level("WARNING")

# Windows compatibility is not ok because of os.system calls:
# - mv command in PA!Singleplayer Custom
# - ln -sf command in PA!Singleplayer
# These are absolutely vital to the bots functioning
# There is another check in the PA!Singleplayer command
# To ensure users don't get confused with broken functionality, we throw a generic error
if sys.platform == "win32":
    print("Pokemon Arcade was not made with Windows in mind, some important functions regarding singleplayer do not work. Singleplayer has been disabled.")

# Check for and open settings
if os.path.exists("./PokemonArcade_Settings.json"):
    with open("./PokemonArcade_Settings.json") as f:
        Settings = json.load(f)
else:
    print("Please create and fill the PokemonArcade_Settings.json file.\nThe template file is available in the repo.")
    exit()

# Make sure we don't get errors from directories that don't exist later
for dir in ["./CustomRoms", "./SinglePlayerSaves", "./screenshots"]:
    if not os.path.exists(dir):
        print("Creating directory: " + dir)
        os.mkdir(dir)

# Bot Settings
IconURL = Settings["IconURL"]
SupportServerURL = Settings["SupportServerURL"]
ImageChannelID = int(Settings["ImageChannelID"])
RomLocations = Settings["RomLocations"]

# We define startPyBoy before setting ChannelInfo with an instance of the game
# Starts and returns a pyboy instance
def startPyBoy(rom):
    pyboy = PyBoy(rom, window_type="headless", debug=False, game_wrapper=False, sound=False)
    pyboy.set_emulation_speed(0)
    for i in range(2000):
        pyboy.tick()
    return pyboy

# StartNewGameDisabled is a bool to indicate if a new game can be started
StartNewGameDisabled = False
ChannelInfo = {"global": {"type": "global", "instance": startPyBoy("./pokemonred.gb"), "message": None, "removecounter": -1, "permanent": True, "filepath": "./pokemonred.gb", "sessionid": "global", "refer": "global", "playercount": 0, "TimerActive": False, "UsersReacted": {}, "VoteCounts": {"🅰": 0, "🅱": 0, "⬆": 0, "⬇": 0, "⬅": 0, "➡": 0, "▶": 0, "🟦": 0, "🕐": 0}}}
# Maps emojis to buttons and the pressed (button) text
emojiToButtonMap = {"🅰": [WindowEvent.PRESS_BUTTON_A, WindowEvent.RELEASE_BUTTON_A, "Pressed A"], "🅱": [WindowEvent.PRESS_BUTTON_B, WindowEvent.RELEASE_BUTTON_B, "Pressed B"], "⬆": [WindowEvent.PRESS_ARROW_UP, WindowEvent.RELEASE_ARROW_UP, "Pressed Up"], "⬇": [WindowEvent.PRESS_ARROW_DOWN, WindowEvent.RELEASE_ARROW_DOWN, "Pressed Down"], "⬅": [WindowEvent.PRESS_ARROW_LEFT, WindowEvent.RELEASE_ARROW_LEFT, "Pressed Left"], "➡": [WindowEvent.PRESS_ARROW_RIGHT, WindowEvent.RELEASE_ARROW_RIGHT, "Pressed Right"], "🟦": [WindowEvent.PRESS_BUTTON_SELECT, WindowEvent.RELEASE_BUTTON_SELECT, "Pressed Select"], "▶": [WindowEvent.PRESS_BUTTON_START, WindowEvent.RELEASE_BUTTON_START, "Pressed Start"]}
# Nintendo Logo for "DRM" checking
NintendoLogo = "CEED6666CC0D000B03730083000C000D0008111F8889000EDCCC6EE6DDDDD999BBBB67636E0EECCCDDDC999FBBB9333E"

# Screenshot Cache database
with open("ScreenshotCache.json", "r") as f:
    ScreenshotCache = json.loads(f.read())

# Standardized Embed Code
def GetEmbed(text):
    return discord.Embed(title="", type="rich", description=text, color=discord.colour.Color.from_rgb(255, 214, 34)).set_author(name="Pokémon Arcade", icon_url=IconURL, url=SupportServerURL)

# Pushes a button on a pyboy instance
def PressButton(pyboy, buttonPress, buttonRelease):
    pyboy.send_input(buttonPress)
    for i in range(15):
        pyboy.tick()
    pyboy.send_input(buttonRelease)
    pyboy.tick()

# Instruct a pyboy instance to press a button, and return status text
def DoActionOnEmoji(pyboy, Emoji):
    EmbedText = ""
    if Emoji == "🕐":
        for i in range(105):
            pyboy.tick()
        EmbedText = "Waited 2 seconds"
    else:
        PressButton(pyboy, emojiToButtonMap[Emoji][0], emojiToButtonMap[Emoji][1])
        EmbedText = emojiToButtonMap[Emoji][2]
    for i in range(15):
        pyboy.tick()
    return EmbedText

# Make a screenshot
def screenshot(pyboy):
    try:
        # Remove potential previous screenshot
        os.remove("./ScreenshotResized.png")
    except:
        pass
    # Remove possible older leftover screenshots
    try:
        [os.remove("./screenshots/" + file) for file in os.listdir("./screenshots/")]
    except:
        pass
    # Screenshot pyboy instance
    pyboy.send_input(WindowEvent.SCREENSHOT_RECORD)
    pyboy.tick()
    # Open the image
    img = Image.open(f"./screenshots/{os.listdir('./screenshots/')[0]}")
    # Resize 3x, nearest neighbor
    img = img.resize((img.size[0] * 3, img.size[1] * 3), 0)
    img.save("ScreenshotResized.png")
    # Return the screenshot path.
    return "ScreenshotResized.png"

# Upload a screenshot to discord for embedding
async def uploadScreenshot(fp):
    global ImageChannelID
    global ScreenshotCache
    if fp == "":
        return ""
    # Hash the screenshot
    with open(fp,"rb") as f:
        dump = f.read()
        readable_hash = hashlib.sha512(dump).hexdigest()
    # Check if we've seen this screenshot before
    if readable_hash in ScreenshotCache.keys():
        # File was found in cache
        url = ScreenshotCache[readable_hash]
    else:
        try:
            # The image was not found in cache
            # Send the image
            msg = await client.get_channel(ImageChannelID).send("", file=discord.File(fp, filename=readable_hash[10:] + ".png"))
            url = msg.attachments[0].url
            # Add the image to cache
            ScreenshotCache[readable_hash] = url
            with open("ScreenshotCache.json", "w") as f:
                f.write(json.dumps(ScreenshotCache))
        except:
            return ""
    return url


class MyClient(discord.Client):

    async def on_ready(self):
        print("Logged in as", str(client.user))
        # Playing Pokemon | PA!Help
        # Easy for users to understand what's going on, and help command
        await client.change_presence(activity=discord.Game(name=f"Pokémon | PA!Help"))

    async def on_message(self, message):
        global ChannelInfo
        global NintendoLogo
        global RomLocations
        # Don't respond to bots
        if message.author.bot:
            return
        # If it's not a command being sent, don't respond
        if not message.content.lower().startswith("pa!"):
            return
        # If we're in DMs
        if str(message.channel.type) == "private":
            # Send a message saying DMs are not allowed
            await message.channel.send("DM Channels are disabled, please use a channel in a server instead!")
            return

        # Help message
        if message.content.lower() == "pa!help":
            try:
                # Try to delete the message
                await message.delete()
            except:
                try:
                    # If deleting message failed, send this
                    await message.channel.send("I don't have `Manage Messages` permission!\nI need this permission to automatically remove reactions!")
                    return
                except:
                    pass
            try:
                # Try to send embed
                await message.channel.send("", embed=GetEmbed(f"Pokémon Arcade is a Discord bot to play pokemon on Discord!\nPlay by voting on which action to take, or play your own way in singleplayer!\n\nCommands List:\n`PA!Join (Session ID)`: Joins a game\n`PA!Leave`: Leaves or stops the game\n`PA!Singleplayer`: Start a private game\n`PA!Singleplayer (yellow|blue|custom) (permanent)`: Start a different Pokémon game\n\nUse the reactions to interact\n:a: :b: :arrow_left: :arrow_up: :arrow_down: :arrow_right: - Press buttons\n:arrow_forward: - Start\n:blue_square: - Select\n:clock1: - Wait 2 in-game seconds\n\n[Support Server]({SupportServerURL})"))
            except discord.errors.Forbidden:
                try:
                    # If sending embed failed, send this
                    await message.channel.send("I don't have `Embed Links` permission!\nIt's needed for me to send game data!")
                except:
                    try:
                        # If sending message failed, DM the user calling help.
                        await message.author.send("I don't have `Send Messages` permission in that channel!")
                    except:
                        pass

        if message.content.lower().startswith("pa!join"):
            # If there's already a game in the channel
            if message.channel.id in ChannelInfo.keys():
                await message.channel.send("Only one game per channel!", delete_after=20)
                return
            # If a game code has been given
            if len(message.content.lower().split(" ")) > 1:
                # Try to get the channel with the correct sessionid
                referchannel = {}
                for channel in list(ChannelInfo.keys()):
                    channel = ChannelInfo[channel]
                    # Find any channel with the same session ID
                    if channel["sessionid"] == message.content.lower().split(" ")[1]:
                        # Set the referchannel, to be sure that we have the right starting channel for playercount
                        gametype = "single"
                        referchannel = ChannelInfo[channel["refer"]]
                        referchannelid = channel["refer"]
                        ChannelInfo[referchannelid]["playercount"] += 1
                        pyboy = referchannel["instance"]
                        permanent = referchannel["permanent"]
                        romlink = referchannel["filepath"]
                        sessionid = referchannel["sessionid"]
                        break
                # If no channel with that session id was found
                if referchannel == {}:
                    await message.channel.send("Invalid Session ID!")
                    return
            else:
                gametype = "global"
                referchannel = ChannelInfo["global"]
                referchannelid = "global"
                ChannelInfo[referchannelid]["playercount"] += 1
                pyboy = referchannel["instance"]
                permanent = False
                romlink = referchannel["filepath"]
                sessionid = referchannel["sessionid"]
            # Send the update message
            UpdateMessage = await message.channel.send("", embed=GetEmbed(f"Displaying Game!").set_image(url=await uploadScreenshot(screenshot(pyboy))))
            # Add the pyboy instance to the list
            ChannelInfo[message.channel.id] = {"type": gametype, "instance": pyboy, "message": UpdateMessage, "removecounter": int(datetime.datetime.now().timestamp()) + 1800, "permanent": permanent, "filepath": romlink, "sessionid": sessionid, "refer": referchannelid, "playercount": 1}
            # Add all control reactions
            for emoji in list("🅰🅱⬅⬆⬇➡▶🟦🕐"):
                await ChannelInfo[message.channel.id]["message"].add_reaction(emoji)

            if referchannelid == "global":
                # Get the current timestamp
                timenowunix = int(datetime.datetime.now().timestamp())
                try:
                    # While the set "go inactive" time is later than right now
                    while ChannelInfo[message.channel.id]["removecounter"] > timenowunix:
                        # Sleep untill the player should be kicked for inactivity if they don't press any buttons
                        await asyncio.sleep(ChannelInfo[message.channel.id]["removecounter"] - timenowunix + 1)
                        # Reset current time
                        timenowunix = int(datetime.datetime.now().timestamp())
                except KeyError:
                    # We except KeyError here because it's possible that ChannelInfo[message.channel.id] has been removed by PA!Leave
                    return
                # Leaves the current game
                info = ChannelInfo[message.channel.id]
                info["instance"].stop(save=True)
                try:
                    await info["message"].edit(embed=GetEmbed("Kicked due to inactivity!"))
                    await info["message"].clear_reactions()
                except:
                    pass
                ChannelInfo.pop(message.channel.id)

        if message.content.lower().startswith("pa!singleplayer"):
            if sys.platform == "win32":
                await message.channel.send("Singleplayer games are disabled!")
                return
            # If there's already a game in the channel
            if message.channel.id in ChannelInfo.keys():
                await message.channel.send("Only one game per channel!", delete_after=20)
                return
            # Set permanent to avoid unset variable
            permanent = False
            # If the caller wants the game to be permanent
            if message.content.lower().endswith(" permanent"):
                # Check if the guild has permissions
                if message.guild.large:
                    # If it's an administrator
                    if message.author.permissions_in(message.channel).administrator:
                        # Allow a permanent game
                        permanent = True
                    else:
                        await message.channel.send("Only server administrators can make permanent games!")
                        return
                else:
                    await message.channel.send("Only large servers can make permanent games!")
                    return

            # By default rom/romlink should be pokemon red
            rom = RomLocations["red"]
            romlink = f"./SinglePlayerSaves/red-{str(message.channel.id)}.gb"
            # If a custom game name is given
            if len(message.content.split(" ")) > 1:
                splitcontent = message.content.lower().split(" ")
                if splitcontent[1] in RomLocations:
                    rom = RomLocations[splitcontent[1]]
                    romlink = f"./SinglePlayerSaves/{splitcontent[1]}-{str(message.channel.id)}.gb"
                # If a custom game is selected
                elif splitcontent[1] == "custom":
                    # If an ID is given
                    if len(splitcontent) >= 3:
                        # If the ID isn't 5 characters long
                        if len(splitcontent[2]) != 5:
                            await message.channel.send("That's not a valid Game ID!")
                            return
                        # If the path exists
                        if os.path.isfile(f"./CustomRoms/{splitcontent[2]}.gb"):
                            # Set the rom to the custom one
                            rom = f"./CustomRoms/{splitcontent[2]}.gb"
                            romlink = f"./SinglePlayerSaves/pokemon{splitcontent[2]}-{str(message.channel.id)}.gb"
                        else:
                            await message.channel.send("That's not a valid Game ID!")
                            return
                    # If no ID is given, and an attachment is sent
                    elif len(message.attachments) > 0:
                        # Check if it's extension is .gb
                        if not message.attachments[0].filename.endswith(".gb"):
                            await message.channel.send("That is not a gameboy rom!")
                            return
                        # Download the attachment, not as the user submitted filename
                        await message.attachments[0].save(f"./NotHashed.gb")
                        # Hash the attachment
                        with open("./NotHashed.gb","rb") as f:
                            dump = f.read()
                            NintendoLogoCart = ""
                            for i in range(0x0104, 0x0134):
                                hexval = hex(int(dump[i])).split("x")[1].upper()
                                NintendoLogoCart += ("0" * (2 - len(hexval))) + hexval
                            readable_hash = hashlib.md5(dump).hexdigest()
                            readable_hash = readable_hash[0:5]
                        # Check if the cartride nintendo logo is the same as the official logo
                        # This is literally Nintendo's DRM
                        if NintendoLogo != NintendoLogoCart:
                            await message.channel.send("That is not a gameboy rom!\nIf this is a Gameboy rom, and it plays correctly on an emulator, please join the support server and ask for help.")
                            os.remove("./NotHashed.gb")
                            return
                        # Move the attachment to a set location by it's hash
                        # This is required for custom rom saves, and replaying games by ID
                        os.system(f"mv ./NotHashed.gb ./CustomRoms/{readable_hash}.gb")
                        rom = f"./CustomRoms/{readable_hash}.gb"
                        romlink = f"./SinglePlayerSaves/{readable_hash}-{str(message.channel.id)}.gb"
                        # Send the hash back to the uploader
                        await message.channel.send(f"Your custom rom ID is: `{readable_hash}`\nDo `PA!Singleplayer Custom {readable_hash}` to play this game again! (You can even share the ID with friends to have them try this game!)")
                    else:
                        # No attachment or gameid was sent, but "custom" argument was used
                        await message.channel.send("Please provide a game! (Send as attachment together with PA!Singleplayer Custom, or use the ID of an existing game with PA!Singleplayer Custom ID)")
                        return
                else:
                    # User specified wrong game type (red/blue/yellow/custom)
                    await message.channel.send(f"Unknown Game: `{splitcontent[1]}`\nDo `PA!Help` for a list of available games")
                    return

            # Get the session id
            sessionid = hashlib.md5(bytes(str(message.channel.id) + str(int(datetime.datetime.now().timestamp())), "utf-8")).hexdigest()[:5]
            # Start single player game
            await message.channel.send(f"Starting single-player game! Please Wait!\nSession ID: {sessionid}\n(Tip: Make sure to save before leaving!)", delete_after=60)
            # Link the rom to romlink (so that channelid is included for the save files)
            # This is required so that the emulator saves to the romlink path,
            # Allowing single player saves to work without copying the rom every time.
            os.system(f"ln -sf {rom} {romlink}")
            pyboy = startPyBoy(romlink)
            # Send the update message
            UpdateMessage = await message.channel.send("", embed=GetEmbed(f"Displaying Game!").set_image(url=await uploadScreenshot(screenshot(pyboy))))
            # Add the pyboy instance to the list
            ChannelInfo[message.channel.id] = {"type": "single", "instance": pyboy, "message": UpdateMessage, "removecounter": int(datetime.datetime.now().timestamp()) + 1800, "permanent": permanent, "filepath": romlink, "sessionid": sessionid, "refer": message.channel.id, "playercount": 1, "VoteCounts": {"🅰": 0, "🅱": 0, "⬆": 0, "⬇": 0, "⬅": 0, "➡": 0, "▶": 0, "🟦": 0, "🕐": 0}, "TimerActive": False, "UsersReacted": {}}
            # Add control emojis to the message
            for emoji in list("🅰🅱⬅⬆⬇➡▶🟦🕐"):
                await UpdateMessage.add_reaction(emoji)

            # If the game is supposed to not kick for inactivity
            if permanent:
                return
            # Get the current timestamp
            timenowunix = int(datetime.datetime.now().timestamp())
            try:
                # While the set "go inactive" time is later than right now
                while ChannelInfo[message.channel.id]["removecounter"] > timenowunix:
                    # Sleep untill the player should be kicked for inactivity if they don't press any buttons
                    await asyncio.sleep(ChannelInfo[message.channel.id]["removecounter"] - timenowunix + 1)
                    # Reset current time
                    timenowunix = int(datetime.datetime.now().timestamp())
            except KeyError:
                # We except KeyError here because it's possible that ChannelInfo[message.channel.id] has been removed by PA!Leave
                return
            # Leaves the current game
            info = ChannelInfo[message.channel.id]
            info["instance"].stop(save=True)
            try:
                for channelid in list(ChannelInfo.keys()):
                    channel = ChannelInfo[channelid]
                    if channel["refer"] == message.channel.id:
                        try:
                            await channel["message"].edit(embed=GetEmbed("Kicked due to inactivity!"))
                            await channel["message"].clear_reactions()
                        except:
                            pass
            except:
                pass
            ChannelInfo.pop(message.channel.id)

        if message.content.lower().startswith("pa!leave"):
            # Leaves the current game
            try:
                info = ChannelInfo[message.channel.id]
            except KeyError:
                await message.channel.send("There's no game active in the channel!")
                return
            # If it's a single player game, stop the instance
            if info["type"] == "single":
                if info["permanent"]:
                    if not message.author.permissions_in(message.channel).administrator:
                        await message.channel.send("Only administrators can close permanent games!")
                        return
                if info["refer"] == message.channel.id:
                    # This channel is the single player game host.
                    info["instance"].stop(save=True)
                    for channelid in list(ChannelInfo.keys()):
                        if ChannelInfo[channelid]["refer"] == message.channel.id and channelid != message.channel.id:
                            try:
                                await ChannelInfo[channelid]["message"].edit(embed=GetEmbed("Game host stopped playing!"))
                                await ChannelInfo[channelid]["message"].clear_reactions()
                                await asyncio.sleep(1)
                            except:
                                pass
                            ChannelInfo.pop(channelid)
                else:
                    ChannelInfo[info["refer"]]["playercount"] -= 1
            else:
                ChannelInfo[info["refer"]]["playercount"] -= 1
            try:
                await info["message"].edit(embed=GetEmbed("Stopped Playing!"))
                await info["message"].clear_reactions()
            except:
                pass
            ChannelInfo.pop(message.channel.id)


    async def on_raw_reaction_add(self, payload):
        # "🅰🅱⬆⬇⬅➡▶🟦🕐"
        # VoteCounts = {"🅰": 0, "🅱": 0, "⬆": 0, "⬇": 0, "⬅": 0, "➡": 0, "▶": 0, "🟦": 0, "🕐": 0}
        global ChannelInfo
        if payload.user_id == client.user.id:
            return
        if payload.channel_id in ChannelInfo.keys():
            info = ChannelInfo[payload.channel_id]
            if info["message"].id == payload.message_id:
                if payload.event_type == "REACTION_ADD":
                    if str(payload.emoji) in "🅰🅱⬆⬇⬅➡▶🟦🕐":
                        try:
                            await info["message"].remove_reaction(payload.emoji, payload.member)
                        except:
                            pass
                        if info["type"] == "single":
                            ChannelInfo[info["refer"]]["removecounter"] = max(int(datetime.datetime.now().timestamp()) + 1800, ChannelInfo[info["refer"]]["removecounter"])
                        else:
                            ChannelInfo[payload.channel_id]["removecounter"] = max(int(datetime.datetime.now().timestamp()) + 1800, info["removecounter"])
                        instance = info["instance"]
                        if ChannelInfo[info["refer"]]["playercount"] == 1:
                            EmbedText = DoActionOnEmoji(instance, str(payload.emoji))
                            try:
                                await info["message"].edit(embed=GetEmbed(EmbedText).set_image(url=await uploadScreenshot(screenshot(instance))))
                            except:
                                pass
                        else:
                            ChannelInfo[info["refer"]]["UsersReacted"][payload.user_id] = str(payload.emoji)
                            if not ChannelInfo[info["refer"]]["TimerActive"]:
                                ChannelInfo[info["refer"]]["TimerActive"] = True
                                playerCount = ChannelInfo[info["refer"]]["playercount"]
                                await asyncio.sleep(min(playerCount, 5))
                                ChannelInfo[info["refer"]]["VoteCounts"] = {"🅰": 0, "🅱": 0, "⬆": 0, "⬇": 0, "⬅": 0, "➡": 0, "▶": 0, "🟦": 0, "🕐": 0}
                                for user in list(ChannelInfo[info["refer"]]["UsersReacted"].keys()):
                                    emoji = ChannelInfo[info["refer"]]["UsersReacted"][user]
                                    ChannelInfo[info["refer"]]["VoteCounts"][emoji] += 1
                                FinalEmoji = sorted(ChannelInfo[info["refer"]]["VoteCounts"], key=ChannelInfo[info["refer"]]["VoteCounts"].get, reverse=True)[0]
                                ChannelInfo[info["refer"]]["TimerActive"] = False

                                EmbedText = DoActionOnEmoji(ChannelInfo[info["refer"]]["instance"], FinalEmoji)
                                EmbedText += f"\nPlayers: {playerCount}\n"
                                for emoji in list(ChannelInfo[info["refer"]]["VoteCounts"].keys()):
                                    EmbedText += f"{emoji}: {ChannelInfo[info['refer']]['VoteCounts'][emoji]} "
                                UsersReacted = {}
                                # Screenshot and upload
                                screenshoturl = await uploadScreenshot(screenshot(ChannelInfo[info["refer"]]["instance"]))
                                for channelid in list(ChannelInfo.keys()):
                                    channel = ChannelInfo[channelid]
                                    if channel["refer"] == info["refer"]:
                                        try:
                                            await channel["message"].edit(embed=GetEmbed(EmbedText).set_image(url=screenshoturl))
                                        except:
                                            pass

client = MyClient()
client.run(Settings["Token"])
