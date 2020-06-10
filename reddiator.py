#!/usr/bin/python3

SCRIPT_NAME = 'reddiator.py'
VERSION = '0.2'

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
#- Optionnal parameter [N] can be used to specify how many top posts must be loaded.
#- Default value is 10.
###
#
#- Optionnal paramerer [period] can be used to specify the top posts period. Supported value are all, year, month, week, day/today, hour/now.
#- Default value is all.
#
#= r! list $category
#- Responds with a random post taken from a list of pre-defined subreddits mapped to the specified category.
#- Subreddits categories and corresponding subreddits are loaded from a file during script startup.
#= r! list $category -subs
#- Responds with the list of subreddits mapped to the specified category.
#TODO	=> possible add-in: exclude a list of subreddits from pre-defined list for $category: r!list $category -e sub1,sub2,sub3...
###
#
#- r! help [command]
# Responds with a help menu detailing the correct syntax for the specified command.
# If no command is specified, the bot will display the general help menu, with the available commands


import os, sys, getopt, psutil, logging

import discord
client = discord.Client()

from dotenv import load_dotenv

import requests
from requests.auth import HTTPBasicAuth

import json

from random import randint

from time import time

def custom_info_log(msg):
	logging.log(21, '\t' + msg)

class RequestException(Exception):
	def __init__(self, code):
		super().__init__(code)
		self.code = code

def load_categories(filename):
	with open(filename, 'r') as f:
		categories = {}
		for line in f.readlines():
			line_split = line.split(':')
			categories[line_split[0]] = [a.replace('\n','') for a in line_split[1].split(',')]
	return categories


def get_access_token():
	token_req = requests.post('https://www.reddit.com/api/v1/access_token', auth = HTTPBasicAuth(os.getenv('REDDIT_CLIENT_ID'), os.getenv('REDDIT_CLIENT_SECRET')), data = 'grant_type=refresh_token&refresh_token=' + os.getenv('REDDIT_REFRESH_TOKEN'), headers = {'User-Agent' : os.getenv('REDDIT_USER_AGENT')})
	at = json.loads(token_req.text)['access_token']
	custom_info_log(f'Retrieved Reddit AT : {at}')
	return at

def make_request(url, allow_redirects = False):
	at = get_access_token()
	headers = {'Authorization' : 'Bearer ' + at, 'User-Agent' : os.getenv('REDDIT_USER_AGENT')}

	post_req = requests.get(url, headers=headers, allow_redirects = allow_redirects)

	if post_req.status_code == 200:
		return post_req
	elif post_req.status_code == 404:
		logging.warning(f'Request to get a random post from specified subreddit failed with a HTTP 404 error. The subreddit may not exist anymore.')
		raise RequestException(404)
	elif post_req.status_code == 302 and 'search?q=' in post_req.text:
		logging.warning("""Request to get a random post from specified subreddit returned with a HTTP 302 error redirecting to the search page: the subreddit probably doesn't exist.""")
		raise RequestException(302)
	else:
		logging.error(f'Request to get a random post from specified subreddit failed with a HTTP {post_req.status_code} error.\nThe response headers are:\n{post_req.headers}\nThe response body is:\n{post_req.text}')
		raise RequestException(1)

async def respond(msg, link):
	# TODO implement option to beautify response sent to server, to format it correctly
	# could also keep the option of sending the raw post to avoid spoiler and blur nsfw content (only providing the link)
	await msg.channel.send(link)

async def print_top_post(msg, subreddit, number = 10, timespan = 'all'):
	custom_info_log(f'Top post request for subreddit {subreddit}, with pool size = {number} and timespan = {timespan}')

	url = 'https://oauth.reddit.com/r/' + subreddit + '/top?t=' + timespan + '&limit=' + str(number)

	try:
		post_req = make_request(url, allow_redirects = False)
		links = [items['data']['url'] for items in json.loads(post_req.text)['data']['children']]

		custom_info_log(f'Successfully fetched {str(len(links))} links')

		random_index = randint(0, len(links) - 1)

		await respond(msg, links[random_index])
	except RequestException as e:
		await handle_error(msg, e.code)

async def print_help_menu(msg, type = 'general'):
	custom_info_log(f'Help menu requested (type = {type})')
	if type == 'general' or type not in ['general', 'top', 'list']:
		print('general help menu')
	if type == 'top':
		print('top help menu')
	if type == 'list':
		print('list help menu')

async def print_post_in_list(msg, listname):
	custom_info_log(f'Received list command from user {msg.author.name} for {listname}')
	if listname not in CATEGORIES.keys():
		logging.warning('Requested list does not exist in the loaded categories.')
		response = """Sorry, the category you requested does not exist. Try "r! help list" to see the help menu."""
		await msg.channel.send(response)
	else:
		subreddits = CATEGORIES[listname]
		custom_info_log(f'Got {str(len(subreddits))} subreddits matching the category {listname}')
		links = {}
		for sub in subreddits:
			try:
				links[sub] = get_random_post_from_subreddit(sub)
			except:
				pass

		if len(links) == 0:
			logging.warning('Fetch zero link, printing an error message to the user, something is probably wrong or reddit may be down...')
			await handle_error(msg, 0)

		custom_info_log(f'Successfully fetched {str(len(links))} links')
		if len(links) != len(subreddits):
			logging.warning('Reddiator failed to fetch a post from all subreddits specified in the list of this category. List update may be required')

		random_index = randint(0, len(links) - 1)
		custom_info_log(f'Link number {random_index} was chosen')

		await respond(msg, links[list(links.keys())[random_index]])


def get_random_post_from_subreddit(subreddit):

	url = 'https://oauth.reddit.com/r/' + subreddit + '/random'

	try:
		post_req = make_request(url, allow_redirects = True)
		if post_req.status_code == 200:
			custom_info_log(f'Successfully got random post from {subreddit}')
			post_link = json.loads(post_req.text)[0]['data']['children'][0]['data']['url']
			return post_link
	except RequestException as e:
		raise RequestException(e.code)

async def print_post_from_subreddit(msg, subreddit):
	custom_info_log(f'Received random post command for {subreddit} from user {msg.author.name}')

	try:
		post_link = get_random_post_from_subreddit(subreddit)
		await respond(msg, post_link)
	except RequestException as e:
		await handle_error(msg, e.code)


async def handle_error(msg, code):
	if code in [404, 302]:
		message = """Sorry, it seems that this subreddit doesn't exist (anymore?)."""
	elif code == 0:
		message = """Sorry, something went very wrong and we didn't manage to get a link from any of the subreddits mapped to this category. Reddit may be down, in which case... good luck in the outside..."""
	elif code == 1:
		message = """Sorry, something went wrong, please reach out to us (nicely)!"""

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

		if message_chunks[1] == 'help':
			await print_help_menu(message)

		elif message_chunks[1] == 'top':
			if len(message_chunks) == 3:
				await print_top_post(message, message_chunks[2])

			if len(message_chunks) == 4:
				if message_chunks[3].isdigit():
					await print_top_post(message, message_chunks[2], number=message_chunks[3])

				elif message_chunks[3] in ['hour','now','day','today','week','month','year','all']:
					await print_top_post(message, message_chunks[2], timespan=message_chunks[3])
				else:
					logging.warning(f'Received a top command from user {message.author.name} with wrong parameters.')
					response = """Bad command! Type 'r! help' for the help menu, and 'r! help top' for the top command help menu"""
					await message.channel.send(response)

			if len(message_chunks) == 5:
				if message_chunks[3].isdigit() and message_chunks[4] in ['hour','now','day','today','week','month','year','all']:
					await print_top_post(message, message_chunks[2], message_chunks[3], message_chunks[4])
				else:
					logging.warning(f'Received a top command from user {message.author.name} with wrong parameters.')
					response = """Bad command! Type 'r! help' for the help menu, and 'r! help top' for the top command help menu"""
					await message.channel.send(response)

		elif message_chunks[1] == 'list':
			if len(message_chunks) > 3:
				if message_chunks[3] == '-subs':
					listname = message_chunks[2]
					if listname not in CATEGORIES.keys():
						logging.warning('Requested list {listname} does not exist in the loaded categories.')
						response = """Sorry, the category you requested does not exist. Try "r! help list" to see the help menu."""
					else:
						subreddits = CATEGORIES[listname]
						response = 'The following subreddits are in the category \'' + listname + '\': ' +  ', '.join(subreddits)
					await message.channel.send(response)
			else:
				await print_post_in_list(message, message_chunks[2])

		elif message_chunks[1] == 'rand':
			await print_post_from_subreddit(message, message_chunks[2])


		else:
			logging.warning('Bad command, responding with help menu hint.')
			response = """Bad command! Type 'r! help' for the help menu!"""
			await message.channel.send(response)



if __name__ == '__main__':

	#kill existing script process if any is running
	for proc in psutil.process_iter():
		if proc.name() == f'/usr/bin/python3 {SCRIPT_NAME}':
			print('Killing process {proc.pid()}')
			proc.kill()

	try:
		opts, args = getopt.getopt(sys.argv[1:],"hf:l:",["logfile=","loglevel="])
	except getopt.GetoptError:
		print("""Invalid options. Available options are:\n\n -h \t\t\t\t\t\tDisplays this help menu\n -f <filename>, --logfile=<filename> \t\tSets the logfilename.\n -l <level>, loglevel=<level>\t\t\tSets the log level. Available values are info, warn and error.""")
		sys.exit(2)

	logfilename = ''
	loglevel = 21

	for opt, arg in opts:
		if opt in ('-h', '--help'):
			print('Help message')
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
                            filemode='w',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s\t %(message)s',
                            level=loglevel)
	custom_info_log(f'Starting Reddiator Bot version {VERSION}')


	load_dotenv()
	TOKEN = os.getenv('DISCORD_TOKEN')

	CATEGORIES_FILENAME = os.getenv('CATEGORIES_FILENAME')
	if len(CATEGORIES_FILENAME) > 0:
		CATEGORIES = load_categories(CATEGORIES_FILENAME)
		custom_info_log(f'Successfully loaded subreddits for {len(CATEGORIES)} categories.')
	else:
        	logging.warning('No category file found in environnement variables, skipped category loading.')
        	CATEGORIES = {}

	client.run(TOKEN)
