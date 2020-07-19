#!/usr/bin/python3

SCRIPT_NAME = 'reddiator.py'
VERSION = '0.5'

#== Description:	A Discord Bot to post reddit content automatically to channels
#
#
#== Available commands:
#
#= r! rand $subreddit
#- Responds with a random post from the specified subreddit
###
#
#= r! top $subreddit [N] [period]
#- Responds with a random post from the top posts of the specified subreddit.
#
#- Optional parameter [N] can be used to specify how many top posts must be loaded.
#- Default value is 50.
#
#- Optional paramerer [period] can be used to specify the top posts period. Supported value are all, year, month, week, day/today, hour/now.
#- Default value is all.
###
#
#= r! list $category
#- Responds with a random post taken from a list of pre-defined subreddits mapped to the specified category.
#- Subreddits categories and corresponding subreddits are loaded from a file during script startup.
#
#= r! list $category -subs
#- Responds with the list of subreddits mapped to the specified category.
#
#= r! list $string -search
#- Responds with the list of categories mapped to a subreddit containg the specified string in its name.
#
#= r! list $string -cat_search
#- Responds with the list of categories with a name containing the specified string in its name.
#
#= r! list -all
#- Responds with the full list of available categories.
#
#= r! list $category -e $sub1,$sub2...
#- Same behaviour as normal command, but excluded the specified subreddits from the ones mapped with the specified category.
###
#
#= r! vote $subreddit [N] [period] [type]
#- Responds with N posts from $subreddit and adds up and down arrow as reactions to let people vote.
#
#- Optional parameter [N] can be used to specify how many posts must be posted.
#  Default is 3, limit is 5.
#
#- Optional parameter [period] work like the same parameter for the 'top' command.
#  Will be ignored if 'random' type is specified.
#
#- Optional parameter [type] can be set to 'random' or 'top' to get posts either completely at random or from top of [period].
###
#
#- r! help [command]
# Responds with a help menu detailing the correct syntax for the specified command.
# If no command is specified, the bot will display the general help menu, with the available commands


import os, sys, getopt, psutil, logging

import discord
client = discord.Client()

from dotenv import load_dotenv

import json

from random import randint

from time import time

from utils.reddit import *

def custom_info_log(msg):
	logger = logging.getLogger('root')
	logger.log(21, '\t\t' + msg)

def load_categories(filename):
	with open(filename, 'r') as f:
		categories = {}
		for line in f.readlines():
			line_split = line.split(':')
			categories[line_split[0].replace('','').lower()] = {'name' : line_split[0], 'subreddits' : [a.replace('\n','') for a in line_split[1].split(',')]}
	return categories

async def respond(msg, link, permalink, subreddit, type = ''):
	#TODO update to use embeds to send more beautiful content

	prefix = 'https://www.reddit.com'

	if link[-4:] == '.gif' or 'gfycat.com' in link or 'gif' in link:
		message = f'Here is the link to a random gif from /r/{subreddit}: {link}\nLink to the original reddit post <'+ prefix + f'{permalink}'+'>'
	elif link[-4:] in ['.jpg','.png'] or link[-5:] == '.jpeg' or 'imgur.com' in link:
		message = f' Here is the link to a random picture from /r/{subreddit}: {link}\nLink to the original reddit post <'+ prefix + f'{permalink}'+'>'
	elif 'reddit.com' in link:
		message = f' Here is the link to a random post from /r/{subreddit}: {link}'
	else:
		message = f' Here is the link to a random post from /r/{subreddit}: {link}\nLink to the original reddit post <'+ prefix + f'{permalink}'+'>'

	await msg.channel.send(message)

async def respond_vote(msg, links, subreddit):

	await msg.channel.send(f'Here are {len(links)} links from /r/{subreddit}. Vote for your favourite!\n')
	for link in links.keys():
		r = await msg.channel.send(link + '\n')
		custom_info_log(f'Got back message with id {r.id}, attempting to add reactions...')
		await r.add_reaction('\U00002B06')
		await r.add_reaction('\U00002B07')


async def print_help_menu(msg, type = 'general'):
	custom_info_log(f'Help menu requested (type = {type})')
	if type == 'top':
		message = """The `top` command displays a random post in the top posts of the specified subreddit.\nYou can use arguments to specify how many top posts the bot should look at, and the period from which the top posts must be extracted.\nThe command is: `r! top $subreddit [N] [period]` \n\nDefault value for the period is 'all', possible values are all, year, month, week, day|today, hour|now.\nThe default value for N is 10, maximum value is 100. If you get the same post twice, try increasing this parameter!\nAll parameters are optionnal but must be specified in the correct order."""
	elif type == 'list':
		message = """The `list` command displays a random post from a list of predefined subreddits (called a category).\nThe following commands are also available:\n `r! list $category -subs`                          Lists the subreddits mapped to the specified category.\n `r! list $string -cat_search`                 Lists the available categories with a name containing the specified string.\n `r! list $string -search`                          Lists the available categories mapped to at least one subreddits with a name containg the specified string.\n `r! list $category -e $sub1,...`          Exclude the subreddits specified from the list mapped to the category. Subreddits to exclude must be seperated by a comma.\n `r! list -all`                                                   Lists all the available categories."""
	elif type == 'vote':
		message = """The `vote` command displays several posts from the same specified subreddit and let you vote for your favourite!\nYou can use arguments to specify how many posts the bot should display, as well as the time period from which the posts should be extracted.\nThe command is `r! vote $subreddit [N] [period] [random|top]`\n\nYou can use the 'random' or 'top' options to specify if you want to posts to come from the top of the period (default is top of all time) or completely randomly (in which case the period will be ignored, if specified).\nAll parameters are optionnal but must be specified in the correct order."""
	else:
		message = f"""Thank you for use Reddiator v{VERSION}!\nThe bot responds to the following commands:\n `r! rand $subreddit`          Displays a random post from the specified subreddit.\n `r! top $subreddit`            Displays a random post from the top posts of the specified subreddit.\n `r! list $category`            Displays a random post from a selection of subreddits mapped to a category (or list).\n `r! vote $subreddit`          Let's you vote for your favourite post!\n `r! help $command`              Displays the help menu for the specified command."""


	await msg.channel.send(message)

async def print_post_in_list(msg, listname, excluded_subs = []):
	custom_info_log(f'Received list command from user {msg.author.name} for {listname}')
	listname = listname.lower()

	if listname not in CATEGORIES.keys():
		logging.warning('Requested list does not exist in the loaded categories.')
		await handle_error(msg, 8)
	else:
		subreddits = CATEGORIES[listname]['subreddits']
		custom_info_log(f'Got {len(subreddits)} subreddits matching the category {listname}')

		filtered_subreddits = []
		if len(excluded_subs) > 0:
			custom_info_log(f'Received a list of subreddits to exclude: {excluded_subs}')
			excluded_subs_list = [sub.lower() for sub in excluded_subs.split(',')]
			for sub in subreddits:
				if sub.lower() in excluded_subs_list:
					custom_info_log(f'Excluding subreddit {sub} from the request')
				else:
					filtered_subreddits.append(sub)
		else:
			filtered_subreddits = subreddits

		if len(filtered_subreddits) > 0:
			custom_info_log(f'Got {len(filtered_subreddits)} subreddits to search through...')
		else:
			await handle_error(msg, 7)
			return

		found = False
		loop_check = 0

		while not found:
			random_index = randint(0, len(filtered_subreddits) - 1)
			sub = filtered_subreddits[random_index]
			custom_info_log(f'Link #{random_index} was chosen: {sub}')
			loop_check = loop_check + 1

			try:
				link, permalink = get_random_post_from_subreddit(sub)
				found = True
			except RequestException as e:
				if e.code < 6 and e.code > 0:
					custom_info_log('Retrying...')
				else:
					await handle_error(msg, e.code)

			if loop_check > len(subreddits):
				logging.warning('More failed requests than subreddits in the category: stopping here to avoid infine loop. Reddit may be down.')
				await handle_error(msg, 6)
				return

		await respond(msg, link, permalink, sub)


async def print_top_post_from_subreddit(msg, subreddit, number = 50, timespan = 'all'):
	custom_info_log(f'Top post request for subreddit {subreddit}, with pool size = {number} and timespan = {timespan}')

	if check_not_nsfw(msg, subreddit):
		try:
			link, permalink = get_top_post_from_subreddit(subreddit, number, timespan)
			await respond(msg, link, permalink, subreddit)
		except RequestException as e:
			await handle_error(msg, e.code)
	else:
		raise RequestException(9)

async def print_random_post_from_subreddit(msg, subreddit):
	custom_info_log(f'Received random post command for {subreddit} from user {msg.author.name}')

	if check_not_nsfw(msg, subreddit):
		try:
			post_link, perma_link = get_random_post_from_subreddit(subreddit)
			await respond(msg, post_link, perma_link, subreddit)
		except RequestException as e:
			await handle_error(msg, e.code)
	else:
		await handle_error(msg, 9)

async def print_vote_posts_from_subreddit(msg, subreddit, N = 3, type = 'top', timespan = 'all'):

	custom_info_log(f'Received vote request command for {subreddit} from user {msg.author.name} asking for {N} {type} posts')

	results = {}
	while len(results) < N:
		try:
			if type == 'top':
				link, permalink = get_top_post_from_subreddit(subreddit, 50, timespan)
			elif type == 'random':
				link, permalink = get_random_post_from_subreddit(subreddit)

			if link not in results.keys():
				results[link] = permalink
		except RequestException as e:
			await handle_error(msg, e.code)
			return

	await respond_vote(msg, results, subreddit)


async def print_penelope_post(msg):
	custom_info_log('Received a request for a Penelope post !')
	penelope_subreddits = os.getenv('PENELOPE').split(',')
	random_index = randint(0, len(penelope_subreddits) - 1)
	await print_random_post_from_subreddit(msg, penelope_subreddits[random_index])


def check_not_nsfw(msg, subreddit):
	custom_info_log(f'Received a request to check NSFW status of subreddit {subreddit} for channel {msg.channel}')
	if msg.channel.is_nsfw():
		custom_info_log('Channel is marked NSFW, no need to check anything')
		return True
	else:
		if get_nsfw_status(subreddit):
			custom_info_log('Subreddit is NFSW, aborting...')
			return False
		else:
			custom_info_log('Subreddit is SFW, continuing...')
			return True

async def handle_error(msg, code):
# Error codes :
# 0 = Other error
# 1 = Problem finding the requested subreddit (404, subreddit not found, redirected to search, etc.)
# 2 = Requested subreddit is private
# 3 = Requested subreddit is banned
# 4 = Requested subreddit is quarantined
# 5 = Problem with the Access Token
# 6 = Too many failed request for category, reddit may be down
# 7 = All subreddits filtered
# 8 = Category not found
# 9 = Post from a NSFW subreddit requested on a channel not marked NSFW
	if code == 0:
		message = """Sorry, something went wrong, please reach out to us (nicely)!"""
	elif code == 1:
		message = """Sorry, it seems that this subreddit doesn't exist (anymore?)."""
	elif code == 2:
		message = """Sorry, it seems that this subreddit is private."""
	elif code == 3:
		message = """Sorry, it seems that this subreddit has been banned."""
	elif code == 4:
		message = """Sorry, it seems that this subreddit has been quarantined."""
	elif code == 5:
		message = """Sorry, there's been a technical problem with the authentification to Reddit's API."""
	elif code == 6:
		message = """Sorry, something went very wrong and we didn't manage to get a link from *any* of the subreddits mapped to this category.\nReddit may be down, in which case... good luck in the outside..."""
	elif code == 7:
		message = """Sorry, all the subreddits were filtered from the request."""
	elif code == 8:
		message = """Sorry, the category you requested does not exist. Try `r! help list` to see the help menu for the 'list' command."""
	elif code == 9:
		message = """Sorry, it appears that this Discord channel is not tagged NSFW but the requested subreddit is."""

	await msg.channel.send(message)


@client.event
async def on_ready():
	custom_info_log(f'{client.user} is now connected to the Discord server!')

@client.event
async def on_message(message):
	if message.author == client.user:
		return

	message_chunks = message.content.split(' ')

	if message_chunks[0] == 'r!' and len(message_chunks) > 1:
		custom_info_log(f'Received a message for the bot: {message.content}')

		if message_chunks[1].lower() == 'help':
			if len(message_chunks) == 3:
				await print_help_menu(message, type = message_chunks[2])
			else:
				await print_help_menu(message)

		elif message_chunks[1].lower() in ['penelope','pénélope','pénelope']:
			await print_penelope_post(message)


		elif message_chunks[1].lower() == 'top':
			if len(message_chunks) == 2:
				await print_help_menu(message, 'top')

			if len(message_chunks) == 3:
				await print_top_post_from_subreddit(message, message_chunks[2])

			if len(message_chunks) == 4:
				if message_chunks[3].isdigit():
					await print_top_post_from_subreddit(message, message_chunks[2], number=message_chunks[3])

				elif message_chunks[3] in PERIODS:
					await print_top_post_from_subreddit(message, message_chunks[2], timespan=message_chunks[3])
				else:
					logging.warning(f'Received a top command from user {message.author.name} with wrong parameters. (1)')
					response = """Bad command! Type `r! help` for the general help menu, and `r! help top` for the help menu for the 'top' command."""
					await message.channel.send(response)

			if len(message_chunks) == 5:
				if message_chunks[3].isdigit() and message_chunks[4] in PERIODS:
					await print_top_post_from_subreddit(message, message_chunks[2], message_chunks[3], message_chunks[4])
				else:
					logging.warning(f'Received a top command from user {message.author.name} with wrong parameters. (2)')
					response = """Bad command! Type `r! help` for the general help menu, and `r! help top` for the help menu for the 'top' command."""
					await message.channel.send(response)

		elif message_chunks[1].lower() == 'list':
			if len(message_chunks) > 3:

				listname = message_chunks[2].lower()

				if message_chunks[3].lower() == '-subs':
					if listname not in CATEGORIES.keys():
						logging.warning('Requested list {listname} does not exist in the loaded categories.')
						response = """Sorry, the category you requested does not exist. Try `r! help list` to see the help menu for the 'list' command."""
					else:
						subreddits = CATEGORIES[listname]['subreddits']
						response = 'The following subreddits are in the category \'' + listname + '\': ' +  ', '.join(subreddits)

					await message.channel.send(response)

				elif message_chunks[3].lower() in ['-category_search','-cat_search','-catsearch','-csearch']:

					search_results = []

					for cat in CATEGORIES.keys():
						if listname in cat:
							search_results.append(cat)

					if len(search_results) > 1:
						response = 'The following categories contain the string \'' + listname + '\': ' + ', '.join(search_results)
					elif len(search_results) == 1:
						response = 'Only one category contains the string \'' + listname + '\': ' + search_results[0]
					else:
						response = 'Sorry, there are no categories with a name containing the string \'' + listname + '\''

					await message.channel.send(response)

				elif message_chunks[3].lower() == '-search':

					search_results = []

					for cat in CATEGORIES.keys():
						if any([listname in sub.lower() for sub in CATEGORIES[cat]['subreddits']]):
							search_results.append(cat)

					if len(search_results) > 1:
						response = 'The following categories contain a subreddit with a name containg the string \'' + listname + '\': ' + ', '.join(search_results)
					elif len(search_results) == 1:
						response = 'Only one category contains a subreddit with a name containing the string \'' + listname + '\': ' + search_results[0]
					else:
						response = 'Sorry, there are no categories with at least a subreddit with a name containing the string \'' + listname + '\''

					await message.channel.send(response)

				elif message_chunks[3] in ['-e', '-exclude', '-ex']:

					await print_post_in_list(message, message_chunks[2], message_chunks[4])

			elif message_chunks[2].lower() == '-all':
				response = 'The following categories are available: ' + ', '.join(CATEGORIES.keys())
				await message.channel.send(response)
			elif len(message_chunks) == 2:
				await print_help_menu(message, 'list')
			else:
				await print_post_in_list(message, message_chunks[2])

		elif message_chunks[1].lower() == 'rand':
			await print_random_post_from_subreddit(message, message_chunks[2])


		elif message_chunks[1].lower() == 'vote':
			if len(message_chunks) < 3:
				await print_help_menu(message, 'vote')
			else:
				if len(message_chunks) == 3:
					await print_vote_posts_from_subreddit(message, message_chunks[2])

				elif len(message_chunks) == 4:
					if message_chunks[3].isdigit():
						await print_vote_posts_from_subreddit(message, message_chunks[2], N=message_chunks[3])

					elif message_chunks[3] in PERIODS:
						await print_vote_posts_from_subreddit(message, message_chunks[2], timespan=message_chunks[3])
					elif message_chunks[3] in ['random', 'top']:
						await print_vote_posts_from_subreddit(message, message_chunks[2], type=message_chunks[3])
					else:
						logging.warning(f'Received a vote command from user {message.author.name} with wrong parameters. (1)')
						response = """Bad command! Type `r! help` for the general help menu, and `r! help vote` for the help menu for the 'vote' command."""
						await message.channel.send(response)

				elif len(message_chunks) == 5:
					if message_chunks[3].isdigit() and message_chunks[4] in PERIODS:
						await print_top_post_from_subreddit(message, message_chunks[2], N=message_chunks[3], timespan=message_chunks[4])
					elif message_chunks[3].isdigit() and message_chunks[4] in ['random', 'top']:
						await print_top_post_from_subreddit(message, message_chunks[2], N=message_chunks[3], type=message_chunks[4])
					elif message_chunks[3] in PERIODS and messages_chunks[4] in ['random', 'top']:
						await print_top_post_from_subreddit(message, message_chunks[2], timespan=message_chunks[3], type=message_chunks[4])

					else:
						logging.warning(f'Received a vote command from user {message.author.name} with wrong parameters. (2)')
						response = """Bad command! Type `r! help` for the general help menu, and `r! help vote` for the help menu for the 'vote' command."""
						await message.channel.send(response)
				elif len(message_chunks) == 6:
					if message_chunks[3].isdigit() and message_chunks[4] in PERIODS and message_chunks[5] in ['random', 'top']:
						await print_top_post_from_subreddit(message, message_chunks[2], N=message_chunks[3], timespan=message_chunks[4], type=message_chunks[5])
					else:
						logging.warning(f'Received a vote command from user {message.author.name} with wrong parameters. (3)')
						response = """Bad command! Type `r! help` for the general help menu, and `r! help vote` for the help menu for the 'vote' command."""
						await message.channel.send(response)
				else:
					logging.warning(f'Received a vote command from user {message.author.name} with wrong parameters (4).')
					response = """Bad command! Type `r! help` for the general help menu, and `r! help vote` for the help menu for the 'vote' command."""
					await message.channel.send(response)

		else:
			logging.warning('Bad command, responding with help menu hint.')
			response = """Bad command! Type `r! help` for the general help menu!"""
			await message.channel.send(response)


if __name__ == '__main__':

	try:
		opts, args = getopt.getopt(sys.argv[1:],"hf:l:",["logfile=","loglevel="])
	except getopt.GetoptError:
		print("""Invalid options. Available options are:\n\n -h \t\t\t\t\t\tDisplays this help menu\n -f <filename>, --logfile=<filename> \t\tSets the logfilename.\n -l <level>, loglevel=<level>\t\t\tSets the log level. Available values are info, warn and error.""")
		sys.exit(2)

	logfilename = ''
	loglevel = 21

	for opt, arg in opts:
		if opt in ('-h', '--help'):
			print(f"""Reddiator Bot version {VERSION}\nAvailable options are:\n\n -h \t\t\t\t\t\tDisplays this help menu\n -f <filename>, --logfile=<filename> \t\tSets the logfilename.\n -l <level>, loglevel=<level>\t\t\tSets the log level. Available values are info, warn and error.""")
			sys.exit()
		elif opt in ('-f', '--logfile'):
			logfilename = arg
		elif opt in ('-l', '--loglevel'):
			if arg == 'info':
				loglevel = 21
			elif arg == 'warn':
				loglevel = 30
			elif arg == 'error':
				loglevel = 40
			else:
				#defaulting to info
				loglevel = 21

	if len(logfilename) == 0:
		#defaulting to timestamped logfile
		logfilename = 'reddiator.' + str(int(time())) + '.log'

	logging.addLevelName(21, 'INFO')
	logging.basicConfig(filename=logfilename,
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s\t %(message)s',
                            level=loglevel)

	custom_info_log(f'Starting Reddiator Bot version {VERSION}')


	#killing running instance of the process if any is already running
	for proc in psutil.process_iter():
		if proc.name() == SCRIPT_NAME and proc.pid != os.getpid():
			logging.warning(f'Killing already running reddiator process with pid = {proc.pid}')
			proc.kill()

	custom_info_log(f'Bot initiation completed, process pid = {proc.pid}')

	load_dotenv()
	TOKEN = os.getenv('DISCORD_TOKEN')

	CATEGORIES_FILENAME = os.getenv('CATEGORIES_FILENAME')
	if len(CATEGORIES_FILENAME) > 0:
		CATEGORIES = load_categories(CATEGORIES_FILENAME)
		custom_info_log(f'Successfully loaded subreddits for {len(CATEGORIES)} categories.')
	else:
        	logging.warning('No category file found in environnement variables, skipped category loading.')
        	CATEGORIES = {}

	PERIODS = ['hour','hours','now','day','days','today','week','weeks','month','months','year','years','all']

	client.run(TOKEN)
