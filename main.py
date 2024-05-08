# mongodb imports
from pymongo import MongoClient 

# discord bot imports
import discord as discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio

# bot imports
from bot.playing.games.connect_four import ConnectFour
from bot.playing.players.montecarlo import MonteCarlo
from bot.playing.players.human import HumanPlayer
from time import sleep, time

# load TOKEN from .env file
load_dotenv()
TOKEN = os.getenv('TOKEN')

def get_mongo_db():
   
   # Provide the mongodb atlas url to connect python to mongodb using pymongo
   CONNECTION_STRING = os.getenv('CONNECTIONSTRING')
 
   # Create a connection using MongoClient. You can import MongoClient or use pymongo.MongoClient
   client = MongoClient(CONNECTION_STRING)
 
   # Create the database for our example (we will use the same database throughout the tutorial
   return client['connect_four']

dbname = get_mongo_db()
collection_name = dbname["connect_four_users"]

# define intents
intents = discord.Intents.default()
intents.message_content = True

# Create a new bot instance with a command prefix
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary to track users waiting for a response
waiting_for_response = {}

# get user with most wins
@bot.command(brief= "Gets user with most wins", description="Gets user with most wins")
async def top_wins(ctx):
 
    entry = collection_name.find_one(sort=[("wins", -1)])

    DM = await ctx.author.create_dm()

    if entry["wins"] == 0:
        embed = discord.Embed(title=f"no one has won yet...")
    else:
        embed = discord.Embed(title=f"user with most wins: {entry["username"]} | number of wins: {entry["wins"]}")

    await DM.send(embed=embed)

# get user with most losses
@bot.command(brief="Gets user with most losses", description="Gets user with most losses")
async def top_loss(ctx):
    entry = collection_name.find_one(sort=[("loss", -1)])

    DM = await ctx.author.create_dm()

    if entry["loss"] == 0:
        embed = discord.Embed(title=f"no one has lost yet..")
    else:
        embed = discord.Embed(title=f"user with most losses: {entry["username"]} | number of losses: {entry["loss"]}")

    await DM.send(embed=embed)

@bot.command(brief="Gets user with the fastest win", description="Get user with the fastest win")
async def fastest_win(ctx):
    entry = collection_name.find_one(sort=[("fwin", 1)])

    DM = await ctx.author.create_dm()

    if entry["fwin"] == 0:
        embed = discord.Embed(title=f"no one has been able to beat the bot yet...")
    else:
        embed = discord.Embed(title=f"user with fastest win: {entry["username"]} | time: {entry["fwin"]} seconds")

    await DM.send(embed=embed)      

# Command to start the chat loop
@bot.command(brief="Starts a game of connect four", description="Starts a game of connect four")
async def connect_four(ctx):

    DM = await ctx.author.create_dm()
    await DM.send("Game has started...")

    user_id = ctx.author.id
    user_name = ctx.author.name

    # check if user exists
    #if no then add to collection
    existing_user = check_user(user_name, collection_name)
    if existing_user is None:
        # user exists
        user = {
        "username" : user_name,
        "wins" : 0,
        "loss" : 0,
        "tie" : 0,
        "fwin" : 0,
        "floss" : 0,
        "ftie" : 0
        }

        existing_user = user
        collection_name.insert_one(user)
        print("user added to collection")
    else:
        print("user already in collection")

    waiting_for_response[user_id] = True

    human_player = HumanPlayer(True)
    monte_player = MonteCarlo(False)

    monte_player.assume(human_player)
    human_player.assume(monte_player)

    game = ConnectFour()
    
    # seconds per game loop - used to track seconds per turn/game
    interval = 1
    
    # count number of moves per game
    moves = 1

    # create initial connect four board
    board = game.display()

    # send initial board to user
    embed = discord.Embed(title=board)
    await DM.send(embed=embed)

    # set players
    player, opponent = human_player, monte_player

    # used to skip specific msgs
    skip = False

    # track seconds per game
    final_seconds = 0

    # Loop to wait for user responses
    while waiting_for_response.get(user_id, False):
        try:

            # track time per move
            start = time()

            # if game over detemine w/l/t
            if game.utility() is not None:

                if game.utility() == -1:
                    update_connect_four_users_loss(collection_name, existing_user, final_seconds)
                    print(f"updated loss {existing_user["username"]} in collection")
                    embed = discord.Embed(title=f"W/L: LOSS | No. of Moves: {moves} | TIME: {round(final_seconds,2)} seconds")
                    await DM.send(embed=embed)
                    break
                elif game.utility() == +1:
                    update_connect_four_users_win(collection_name, existing_user, final_seconds)
                    print(f"updated win {existing_user["username"]} in collection")
                    embed = discord.Embed(title=f"W/L: WIN | No. of Moves: {moves} | TIME: {round(final_seconds,2)} seconds")
                    await DM.send(embed=embed)
                    break
                else:
                    update_connect_four_users_tie(collection_name, existing_user, final_seconds)
                    print(f"updated tie {existing_user["username"]} in collection")
                    embed = discord.Embed(title=f"W/L: TIE | No. of Moves: {moves} | TIME: {round(final_seconds,2)} seconds")
                    await DM.send(embed=embed)
                    break

            # returns possible moves
            move_list = player.move(game)

            # calculate seconds per bot move
            bot_seconds = time() - start

            # if human player
            if player.maximizes():
                
                # skip shwoing possible moves if we are waiting for a move from the user (used if user enters invalid move)
                if skip != True:
                    await DM.send(f"possible moves (LEFT, TOP): {move_list} | example inputs: 5,0")

                # capture message from user
                message = await bot.wait_for('message', timeout=100.0, check=lambda m: m.author == ctx.author)
            
                # end game before finishing
                if message.content == 'quit':
                    await DM.send("Game has ended")
                    break

                else:

                    # could be a valid move
                    seconds = time() - start
                    final_seconds += seconds

                    skip = False
                    l = message.content.split(',')

                    move = ()

                    for x in l:
                        move += (int(x),)

                    if move not in move_list:
                        await DM.send("Invalid move")
                        continue
                    else:
                        await DM.send(f"PLAYER move after {round(seconds,2)} seconds: ")
                        game = game.child(move, player)

            else:
                final_seconds += seconds
                await DM.send(f"BOT move after {round(bot_seconds,2)} seconds: ")
                game = game.child(move_list, player)
            
            # display board after bot or player move
            board = game.display()
            embed = discord.Embed(title=board)
            await DM.send(embed=embed)
    
            if player.maximizes():
                await DM.send("Bot is thinking...")

            # increment moves
            moves += 1

            # used to track seconds
            sleep(interval)

            # swap players
            player, opponent = opponent, player

        # took to long to enter new move
        except asyncio.TimeoutError:
            del waiting_for_response[user_id]
            await DM.send("Game ended due to inactivity.")
            break
        
        # catch all
        except Exception as Argument:
            print(str(Argument))
            await DM.send("unexpected error...")

# Event: Bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

def update_connect_four_users_loss(collection_name, user, final_seconds):
    
    # if zero add automatically
    if float(user["floss"]) == 0:
        collection_name.update_one({"username": user['username']},
                                    {
                                        "$inc": {"loss": 1},
                                        "$set": {"floss": str(round(final_seconds,2))},
                                    }, 
                                    True
                                    )
    else:
        # if current floss time is greater than final_seconds than update floss with final seconds
        if float(user["floss"]) > final_seconds:
            collection_name.update_one({"username": user['username']},
                                    {
                                        "$inc": {"loss": 1},
                                        "$set": {"floss": str(round(final_seconds,2))},
                                    }, 
                                    True
                                    )
        else:
            pass

def update_connect_four_users_win(collection_name, user, final_seconds):
    # if zero add automatically
    if float(user["fwin"]) == 0:
        collection_name.update_one({"username": user['username']},
                                    {
                                        "$inc": {"win": 1},
                                        "$set": {"fwin": str(round(final_seconds,2))},
                                    }, 
                                    True
                                    )
    else:
        # if current fwin time is greater than final_seconds than update floss with final seconds
        if float(user["fwin"]) > final_seconds:
            collection_name.update_one({"username": user['username']},
                                    {
                                        "$inc": {"win": 1},
                                        "$set": {"fwin": str(round(final_seconds,2))},
                                    }, 
                                    True
                                    )
        else:
            pass

def update_connect_four_users_tie(collection_name, user, final_seconds):
    # if zero add automatically
    if float(user["ftie"]) == 0:
        collection_name.update_one({"username": user['username']},
                                    {
                                        "$inc": {"tie": 1},
                                        "$set": {"tie": str(round(final_seconds,2))},
                                    }, 
                                    True
                                    )
    else:
        # if current ftie time is greater than final_seconds than update floss with final seconds
        if float(user["ftie"]) > final_seconds:
            collection_name.update_one({"username": user['username']},
                                    {
                                        "$inc": {"tie": 1},
                                        "$set": {"tie": str(round(final_seconds,2))},
                                    }, 
                                    True
                                    )
        else:
            pass

def check_user(username, collection_name):
    return collection_name.find_one({"username": username})    

# Run the bot with your token
bot.run(TOKEN)
