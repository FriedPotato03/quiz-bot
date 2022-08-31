import discord, json
from asyncio import sleep
from datetime import datetime
from discord.ext import commands
from os import chdir

chdir('\\'.join(__file__.split('\\')[:-1]))		#Changing path to keep files in same folder
quizbot= commands.Bot(command_prefix= '0> ', intents= discord.Intents.all(), help_command= None)
quiz_progress= {}			#For storing the progress of the quiz in a global scale
loaded_quizzes= {}			#To store the quizzes loaded from the JSON files
responses= {}				#To store the responses of the participants for the quizzes
moderation_roles= {}		#Need to be added to prevent misuse of some commands.

#Note: Save the bot token and the bot owner ID in the 'moderation' folder in token.txt and owner.txt
with open('moderation/token.txt') as file: token= file.read()
with open('moderation/owner.txt') as file: owner= int(file.read())
with open('quizzes/descriptions.json') as file: descriptions= json.load(file)['quizzes']

#Helper Functions.

def format_question(guild_id: int, question: dict):
	'''Makes a string based on the question dict for the DM message.'''
	return f"**Quiz ID:** {guild_id} | {quiz_progress[guild_id]['quiz_id']}\n__**Sauce:**__ {question['sauce']}\n__**Text:**__ {question['text']}\n"+'\n'.join([f"{i} {question['options'][i]}" for i in question['options']])

def calculate_result(quiz: list, response: list):
	'''Calculates the result based on the quiz and responses.'''
	return sum([1 for i in range(len(quiz)) if quiz[i]['correct_option'] == response[i] ])

def format_results(results: list):
	'''Makes a string based on the sorted results for the message.'''
	output= "__**Result:**__\n"
	i= 1
	for j in range(len(results)):
		if j:
			if results[j]['marks'] != results[j-1]['marks']: i= j+1
		output += f"**{i}:** <@{results[j]['user'].id}> ({results[j]['marks']} pts)\n" 
	return output

async def quiz_refresh(guild_id):
	'''Main quiz work is done here.'''
	#Loads Quiz from JSON file into storage
	with open(f'quizzes/{quiz_progress[guild_id]["quiz_id"]}.json', encoding= 'utf-16') as file:
		loaded_quizzes[guild_id]= json.load(file)
	#Checks if no participants are there
	if len(quiz_progress[guild_id]['participants'])==0:
		await quiz_progress[guild_id]['channel'].send("Uh oh. Nobody's participating. Try again later")
		quiz_progress.pop(guild_id)
		return None
	#Registers participants for the quiz and sends them a message
	for user in quiz_progress[guild_id]['participants']:
		print(user)
		if user in responses:
			await user.send(f"You are already registered in the quiz in server **{quizbot.get_guild(responses[user]['guild_id'])}**")
			continue
		responses[user]= {'guild_id' : guild_id, 'response' : [None for i in range(loaded_quizzes[guild_id]['quiz_length'])] }
		await user.send(f"You have been registered for **Quiz {quiz_progress[guild_id]['quiz_id']}** in server **{quizbot.get_guild(guild_id)}**")
	#Sends a message to the channel where the quiz was started.
	await quiz_progress[guild_id]['channel'].send("**Participants of the quiz:\n**" + '\n'.join([f'<@{user.id}>' for user in quiz_progress[guild_id]['participants']])+"\nQuiz will start in 5 seconds.")
	await sleep(5)
	#Sends questions one by one to each participant.
	quiz_progress[guild_id]['status']= 1
	while quiz_progress[guild_id]['status'] <= loaded_quizzes[guild_id]['quiz_length']:
		#Checking for text question or pictorial question
		if 'text' in loaded_quizzes[guild_id]['quiz'][quiz_progress[guild_id]['status']-1]:
			message_string= format_question(guild_id, loaded_quizzes[guild_id]['quiz'][quiz_progress[guild_id]['status']-1])
			await user.send(message_string)
		else:
			message_string= f"**Quiz ID:** {guild_id} | {quiz_progress[guild_id]['quiz_id']}"
			for user in quiz_progress[guild_id]['participants']:
				with open(loaded_quizzes[guild_id]['quiz'][quiz_progress[guild_id]['status']-1]['image'], 'rb') as f:
					img= discord.File(f)
					await user.send(message_string, file=img)
		#Sleep for 17.5 seconds before sending next question. The reaction calculation will be done by on_reaction_add/remove
		await sleep(17.5)
		quiz_progress[guild_id]['status'] += 1
	else:
		#Calculates the result from the bot's response.
		results= []
		for user in quiz_progress[guild_id]['participants']:
			print(f"Responses of [{user}]: {responses[user]['response']}")
			results.append( {'user': user, 'marks': calculate_result(loaded_quizzes[guild_id]['quiz'], responses[user]['response'] ) })
			responses.pop(user)
		#Sort results according to points and sending it.
		results= sorted(results, key= lambda x: x['marks'], reverse= True)
		await quiz_progress[guild_id]['channel'].send(format_results(results))
		#Deleting the records.
		for i in list(quiz_progress[guild_id].keys()): del quiz_progress[guild_id][i] 
		quiz_progress[guild_id]= None
		del loaded_quizzes[(guild_id)]

def check_perms(guild_id: int, author: discord.Member):
	if moderation_roles[guild_id]:
		if quizbot.get_guild(guild_id).get_role(moderation_roles[guild_id]) not in author.roles:
			if author.id != owner:
				return False
	return True

#Quizbot events: General events like message add, reaction add/remove, message sent, etc.

@quizbot.event
async def on_ready():
	'''Filler command to tell me that the bot is up.'''
	global moderation_roles
	print(f"Wake up time: {datetime.now()}")
	with open('moderation/roles.json') as file: moderation_roles= dict([(int(i), j) for i, j in json.load(file).items()])
	if 0 in moderation_roles: moderation_roles.pop(0)
	for guild in quizbot.guilds: 
		print(f"Up and running in server [{guild}]")
		quiz_progress[guild.id]= None
		if guild.id not in moderation_roles:
			moderation_roles[guild.id] = 0
			print(f"Warning: Need to add Organizer role for server {guild}")
		elif not moderation_roles[guild.id]:
			print(f"Warning: Need to add Organizer role for server {guild}")
	print()

@quizbot.event
async def on_guild_join(guild):
	print(f"Joined server [{guild}].\nNote: Organizer role needed for the guild")
	quiz_progress[guild.id] = None
	moderation_roles[guild.id] = 0
	with open("moderation/roles.json", "w") as file: 
		file.write("{\n")
		for guild in moderation_roles: file.write(f'\t"{guild}": {moderation_roles[guild]}, \n')
		file.write('\t"0": 0\n}')

@quizbot.event
async def on_reaction_add(reaction, user):
	'''On reaction add event. Here, it is mainly used to register options, partiipation vote, etc.'''
	#Note: The bot doesn't care if you react anything to other messages. Also, it doesn't care about its first reactions.
	if reaction.message.author == quizbot.user and user != quizbot.user:
		#Message in DMs. Used for checking reactions to quiz messages.
		if reaction.message.guild == None:
			#Checks if the message is a quiz message and the emoji reacted is an option.
			guild_id= responses[user]['guild_id']
			if reaction.message.content.startswith("**Quiz ID:**") and reaction.emoji in loaded_quizzes[guild_id]['quiz'][quiz_progress[guild_id]['status']-1]['options']:
				#Note: Old response will be overwritten. And since the bot can't remove reactions in DMs, you'll have to DIY.
				responses[user]['response'][quiz_progress[guild_id]['status']-1]= reaction.emoji
				#Log statement just for reference.
				print(f"{user} reacted {reaction.emoji} to question {quiz_progress[guild_id]['status']}")
		else:
			#Checks if the message is a quiz register message
			if reaction.message.content.startswith("**Starting Quiz ID:**"):
				#Checks if the reaction is the emoji [Y] and is reacted before the quiz starts. (Originally not disappearing message, so extra check.)
				if reaction.emoji == '🇾' and quiz_progress[reaction.message.guild.id]['status']==0 and reaction.message.id == quiz_progress[reaction.message.guild.id]['message_id']:
					quiz_progress[reaction.message.guild.id]['participants'].append(user)
					print(f"Participant added: {user.name}")

@quizbot.event
async def on_reaction_remove(reaction, user):
	'''On reaction add event. Here, it is mainly used to register options, partiipation vote, etc. similar to its add counterpart.'''
	#I hope no comment is fine considering the details are more or less the same fro
	if reaction.message.author == quizbot.user and quizbot.user != user:
		if reaction.message.guild == None:
			guild_id= responses[user]['guild_id']
			if reaction.message.content.startswith("**Quiz ID:**") and user != quizbot.user and reaction.emoji == responses[user]['response'][quiz_progress[guild_id]['status']-1]:
				responses[user]['response'][quiz_progress[guild_id]['status']-1]= None
				print(f"{user} withdrew his reaction to question {quiz_progress[guild_id]['status']}")
		else:
			if reaction.message.content.startswith("**Starting Quiz ID:**"):
				if user != quizbot.user and reaction.emoji == '🇾' and quiz_progress[reaction.message.guild.id]['status']==0 and reaction.message.id == quiz_progress[reaction.message.guild.id]['message_id']:
					quiz_progress[reaction.message.guild.id]['participants'].remove(user)
					print(f"Participant removed: {user.name}")

@quizbot.event
async def on_message(message):
	'''The core of user interface of the bot. If this fails, it's as good as bot being dead. It. Has. Everything.'''
	#Bot command checks (Ignores all unnecessary messages.)
	if message.author != quizbot.user and message.content.startswith(quizbot.command_prefix):
		await quizbot.process_commands(message)
	#QuizBot messages. Reaction addition, awaiting, deleting, you name it. It's all here.
	elif message.author == quizbot.user:
		#No need to explain. If it's a quiz registry message, add a reaction, wait a few seconds, delete the message and start it.
		if message.content.startswith("**Starting Quiz ID:**"):
			quiz_progress[message.guild.id]['message_id']= message.id
			await message.add_reaction('🇾')
			await sleep(15)
			await message.delete()
			await quiz_refresh(message.guild.id)
		#If it's a quiz question, get the quiz, add the option reactions, wait a few seconds and delete.
		if message.content.startswith("**Quiz ID:**"):
			guild_id= int(message.content.split('\n')[0].split()[2])
			for i in loaded_quizzes[guild_id]['quiz'][quiz_progress[guild_id]['status']-1]['options']: await message.add_reaction(i)
			await sleep(15)
			await message.delete()
		#Generic delete message command to remove cluster of messages (especially annoying when the bot is being tested.)
		if message.content.startswith("You have been registered") or message.content.startswith("The quiz will be stopped"):
			await sleep(5)
			await message.delete()

@quizbot.event
async def on_command_error(ctx, error):
	'''For the instance of false commands or permission restriction'''
	if isinstance(error, commands.CommandNotFound):
		await ctx.send("No command like what you're looking for :-!")
	elif isinstance(error, discord.Forbidden):
		await ctx.send("Looks like I don't have the permission to perform it. ")

#QuizBot Commands: Specific commands which can be called using the command prefix.

@quizbot.command(name= 'help', description= "Help Command. Lists the list of commands and the details of commands too.")
async def help(ctx, cmd: str= "", *args):
	'''Please don't booli me.'''
	#await ctx.send("Hello. Goose is lazy so hasn't made a help command yet. Blame him for this :skull: \nMeanwhile, check the README link in the repository. At least he has done some stuff there (*\*sigh\**) \nClick here:https://github.com/Goose-Of-War/quiz-bot/blob/main/README.md")
	if not cmd:
		await ctx.send(f"Hello. \nHere's the list of all commands in the bot (you can check each individual command details using `{quizbot.command_prefix}help command`): \n\n**__Common commands:__** \n> `available`: This is used to list all available commands in the bot. \n> `describe`: This is used to get info of a command. \n> `ping`: Shows the latency of the bot. \n\n**__Organizer Commands:__** \n> `organizer`: Used to set or get the organizer role who can perform admin functions. \n> `start_quiz`: Used to start a quiz in the server. \n> `terminate`: Used to stop a quiz in the server. \n\nThere are some other functions too. I'll let you find them out. Until then. \nHonk!")
		return 
	try: 
		command= quizbot.get_command(cmd)
		await ctx.send("**Command:** [ "+f"{command.name}"+ (" | " if command.aliases else "")+ " | ".join(command.aliases)+ f" ]\nDescription: {command.description}")
	except:
		await ctx.send("Command not found :-!")

@quizbot.command(name= 'exit', aliases= ['kill', 'off', 'disconnect'], description= "Owner only command. Makes bot go to sleep.")
async def exit(ctx):
	'''To turn off bot. Mainly for dev purposes. Won't be present in final one.'''
	if ctx.message.author.id != owner:
		await ctx.send("You don't have the rights to tell me to go kill myself. Sus.")
		print(f"[{ctx.message.author}|{ctx.guild}] asked me to go die. Boohoo.")
		return None
	print(f"Exit time: {datetime.now()}")
	await quizbot.close()

@quizbot.command(name= 'start_quiz', aliases= ['start', 'begin', 'begin_quiz'], description= f"Starts a quiz in the server. Syntax: {quizbot.command_prefix}start_quiz *quiz_id*")
async def start_quiz(ctx, quiz_id: int):
	'''Starts the quiz. Afterwards, another async function will be used to run the quiz'''
	#Not in server, no quiz for you. Imagine farming experience using this mechanism once the quizzes are released lol.
	if check_perms(ctx.guild.id, ctx.message.author) == False:
		await ctx.send("You do not have the permission to call this command. :(")
		print(f"[{ctx.message.author}|{ctx.guild}] tried to cross the perms XD")
		return 
	if ctx.guild == None:
		await ctx.send("This command is supported only in servers. Please don't use this command in DMs. ")
		return None
	#Testing if the file is present. If not, send a message saying no quiz of said name exists.
	try: open(f'quizzes/{quiz_id}.json', encoding= 'utf-16').close()
	except:
		await ctx.send("Quiz ID does not exist. Please check the quiz ID or contact Goos.")
		return None
	#Check if the server already has an ongoing quiz registered in it.
	if quiz_progress[ctx.message.guild.id]: 
		await ctx.send("A quiz is already registered in this server. ")
		return None
	#If no error comes, register the server in the dict and send a message. Rest will be done by the om_message event.
	quiz_progress[ctx.message.guild.id]= {'quiz_id': quiz_id , 'participants' : [] , 'status' : 0, 'channel' : ctx.channel}
	await ctx.send(f"**Starting Quiz ID:** {quiz_id}. React with 🇾 to participate within 15 seconds.")

@quizbot.command(name= 'available_quizzes', aliases= ['available', 'list'], description="Lists all available quizzes as of the moment.")
async def available_quizzes(ctx):
	'''To check for all available quizzes as of now.'''
	await ctx.send("Available quiz codes:\n```\n"+"\n".join([f"{i['quiz_id']}: {i['quiz_name']}" for i in descriptions])+'\n```')

@quizbot.command(name= 'terminate_quiz', aliases= ['stop','stop_quiz', 'terminate'], description="Stop a quiz in a guild.")
async def terminate_quiz(ctx):
	'''To terminate the currently running quiz.'''
	#Note: Currently, any participant and the bot owner can stop any quizzes.
	if ctx.guild:
		if check_perms(ctx.guild.id, ctx.message.author) == False:
			await ctx.send("You do not have the permission to call this command. :(")
			print(f"[{ctx.message.author}|{ctx.guild}] tried to cross the perms XD")
			return
		print(f"Terminate called by {ctx.message.author}")
		if ctx.guild.id in quiz_progress and ctx.message.author in quiz_progress[ctx.guild.id]['participants']+[quizbot.get_user(owner)]: 
			await ctx.send("The quiz will be stopped in a few seconds. Please ignore the next quiz message, if any.")
			for i in list(quiz_progress[ctx.guild.id].keys()): del quiz_progress[ctx.guild.id][i] 
			quiz_progress[ctx.guild.id]= None
			loaded_quizzes.pop(ctx.guild.id)
			for user in responses:
				if responses[user]['guild_id'] == ctx.guild.id: responses.pop(user);
		else:
			await ctx.send("There are no quizzes registered in this server as of now.")
	else:
		if ctx.message.author in responses:
			if check_perms(responses[ctx.message.author]['guild_id'], ctx.message.author) == False:
				await ctx.send("You do not have the permission to call this command. :(")
				print(f"[{ctx.message.author}|{ctx.guild}] tried to cross the perms XD")
				return
			print(f"Terminate called by {ctx.message.author}")
			guild_id= responses[ctx.message.author]['guild_id']
			await ctx.send("The quiz will be stopped in a few seconds. Please ignore the next quiz message, if any.")
			await quiz_progress[guild_id]['channel'].send(f"The quiz will be stopped in a few seconds. Please ignore the next quiz message, if any. (stopped by {ctx.message.author}")
			for i in list(quiz_progress[guild_id].keys()): del quiz_progress[guild_id][i] 
			quiz_progress[guild_id]= None
			loaded_quizzes.pop(guild_id)
			for user in responses:
				if responses[user]['guild_id'] == guild_id: responses.pop(user);
		else:
			await ctx.send("You are not registered in any quizzes.")

@quizbot.command(name= 'describe', aliases= ['desc', 'info', 'deets'], description= "Gives the description of a quiz.")
async def quiz_info(ctx, quiz_id: int):
	'''Sends the quiz details to the user.'''
	for quiz in descriptions:
		if quiz['quiz_id'] == quiz_id:
			await ctx.send("\n".join([f"**{i.replace('_',' ').capitalize()}**: {quiz[i]}" for i in quiz]))
			return
	else:
		await ctx.send(f"Quiz **{quiz_id}** does not exist. Use `{quizbot.command_prefix}available` to check available quizzes.")


@quizbot.command(name= 'organizer', aliases= ['mod'], description= 'To get/set the organizer role')
async def mod_role(ctx, role = "", *args):
	'''Gets/Sets an organizer role for the server.'''
	#Checks if it's in a server
	if ctx.guild == None: 
		await ctx.send("Not in server. No work to be done.")
		return 
	#Check if the user has permission to call this command
	if check_perms(ctx.guild.id, ctx.message.author) == False:
		await ctx.send("You do not have the permission to call this command. :(")
		print(f"[{ctx.message.author}|{ctx.guild}] tried to cross the perms XD")
		return 
	if not role:
		await ctx.send(f"**Organizer role:** {ctx.guild.get_role(moderation_roles[ctx.guild.id]) if moderation_roles[ctx.guild.id] else None}")
	else:
		moderation_roles[ctx.guild.id] = int(role[3:][:-1]) if role != "None" else 0
		await ctx.send(f"The role **{ctx.guild.get_role(moderation_roles[ctx.guild.id]) if moderation_roles[ctx.guild.id] else None}** is now set as an organizer role in server {ctx.guild}")
	with open("moderation/roles.json", "w") as file: 
		file.write("{\n")
		for guild in moderation_roles: file.write(f'\t"{guild}": {moderation_roles[guild]}, \n')
		file.write('\t"0": 0\n}')

@quizbot.command(name= 'ping', description= "Sends the latency of the bot in ms.")
async def ping(ctx):
	await ctx.send(f"Pong! \n**Latency:** {quizbot.latency*1000: .2f}ms")

@quizbot.command(name= "quack", description= "Don't!")
async def quack(ctx):
	await ctx.send("*No*, **Quack you!**")

@quizbot.command(name= "honk", description= "Honk!")
async def honk(ctx):
	await ctx.send("Yeah!!! My man! A **Honk** especially for you. ")

@quizbot.command(name= "eval", description= "Evaluates something for you.")
async def bot_eval(ctx, expr: str, *args):
	if ctx.guild:
		if check_perms(ctx.guild.id, ctx.message.author) == False:
			await ctx.send("You do not have the permission to call this command. :(")
			print(f"[{ctx.message.author}|{ctx.guild}] tried to cross the perms XD")
			return
	await ctx.send("```\n"+str(eval(expr))+"\n```")

quizbot.run(token)
#Honk