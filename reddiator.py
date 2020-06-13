#!/usr/bin/python3

SCRIPT_NAME = 'reddiator.py'
VERSION = '0.3'

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
#- Default value is 10.
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
			categories[line_split[0].replace('','').lower()] = {'name' : line_split[0], 'subreddits' : [a.replace('\n','') for a in line_split[1].split(',')]}
	return categories

def get_access_token():

	global ACCESS_TOKEN

	if len(ACCESS_TOKEN['AT']) == 0 or ACCESS_TOKEN['EXPIRES'] < int(time()):
		custom_info_log('No AT currently registered, or current AT expired, requesting a new one')

		try:
			token_req = requests.post('https://www.reddit.com/api/v1/access_token', auth = HTTPBasicAuth(os.getenv('REDDIT_CLIENT_ID'), os.getenv('REDDIT_CLIENT_SECRET')), data = 'grant_type=refresh_token&refresh_token=' + os.getenv('REDDIT_REFRESH_TOKEN'), headers = {'User-Agent' : os.getenv('REDDIT_USER_AGENT')})
			response_json = json.loads(token_req.text)
		except:
			logging.error('Error making the request for an AT (or parsing the response). Reddit may be down, or something may be wrong with the bot account (RT revoked?)')

		try:
			expires = int(time()) + response_json['expires_in']
			at = response_json['access_token']
		except:
			logging.error('Error parsing the response from the AT request, no AT and expires attribute found in JSON. RT may be invalid?\nJSON response value: {response_json}')

		custom_info_log(f'Retrieved Reddit AT : {at}')

		ACCESS_TOKEN = {'AT': at, 'EXPIRES': expires}
		return at

	else:
		custom_info_log('Looks like our access token is still valid, let\'s reuse it')
		return ACCESS_TOKEN['AT']

def make_request(url, allow_redirects = False):
	at = get_access_token()
	headers = {'Authorization' : 'Bearer ' + at, 'User-Agent' : os.getenv('REDDIT_USER_AGENT')}

	post_req = requests.get(url, headers=headers, allow_redirects = allow_redirects)

	if post_req.status_code == 200 and post_req.text != '{"kind": "Listing", "data": {"modhash": null, "dist": 0, "children": [], "after": null, "before": null}}':
		return post_req
	elif post_req.status_code == 404 or post_req.text == '{"kind": "Listing", "data": {"modhash": null, "dist": 0, "children": [], "after": null, "before": null}}':
		logging.warning(f'Request to get a random post from specified subreddit failed with a HTTP 404 error. The subreddit may not exist anymore.')
		raise RequestException(404)
	elif post_req.status_code == 302 and 'search?q=' in post_req.text:
		logging.warning('Request to get a random post from specified subreddit returned with a HTTP 302 error redirecting to the search page: the subreddit probably doesn\'t exist.')
		raise RequestException(302)
	elif post_req.status_code == 403 and 'private' in post_req.text:
		logging.error(f'Request to get a random post from speficied subreddit failed with a HTTP 403 code, the subreddit is private.')
		raise RequestException(403)
	else:
		logging.error(f'Request to get a random post from specified subreddit failed with a HTTP {post_req.status_code} error.\nThe response headers are:\n{post_req.headers}\nThe response body is:\n{post_req.text}')
		raise RequestException(1)

async def respond(msg, link, permalink, subreddit):
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

async def print_top_post(msg, subreddit, number = 10, timespan = 'all'):
	custom_info_log(f'Top post request for subreddit {subreddit}, with pool size = {number} and timespan = {timespan}')

	url = 'https://oauth.reddit.com/r/' + subreddit + '/top?t=' + timespan + '&limit=' + str(number)

	try:
		post_req = make_request(url, allow_redirects = False)
		links = [items['data']['url'] for items in json.loads(post_req.text)['data']['children']]
		permalinks = [items['data']['permalink'] for items in json.loads(post_req.text)['data']['children']]

		custom_info_log(f'Successfully fetched {str(len(links))} links')

		random_index = randint(0, len(links) - 1)
		custom_info_log(f'Link #{random_index} was chosen')

		await respond(msg, links[random_index], permalinks[random_index], subreddit)
	except RequestException as e:
		await handle_error(msg, e.code)

async def print_help_menu(msg, type = 'general'):
	custom_info_log(f'Help menu requested (type = {type})')
	if type == 'general' or type not in ['general', 'top', 'list']:
		message = f"""Thank you for use Reddiator v{VERSION}!\nThe bot responds to the following commands:\n `r! rand $subreddit`          Displays a random post from the specified subreddit.\n `r! top $subreddit`            Displays a random post from the top posts of the specified subreddit.\n `r! list $category`            Displays a random post from a selection of subreddits mapped to a category (or list).\n `r! help $command`              Displays the help menu for the specified command."""
	if type == 'top':
		message = """The `top` command displays a random post in the top posts of the specified subreddit.\nYou can use arguments to specify how many top posts the bot should look at, and the period from which the top posts must be extracted.\nThe command is: `r! top $subreddit [N] [period]` \n\nDefault value for the period is 'all', possible values are all, year, month, week, day|today, hour|now.\nThe default value for N is 10, maximum value is 100. If you get the same post twice, try increasing this parameter!"""
	if type == 'list':
		message = """The `list` command displays a random post from a list of predefined subreddits (called a category).\nThe following commands are also available:\n `r! list $category -subs`                          Lists the subreddits mapped to the specified category.\n `r! list $string -cat_search`                 Lists the available categories with a name containing the specified string.\n `r! list $string -search`                          Lists the available categories mapped to at least one subreddits with a name containg the specified string.\n `r! list $category -e $sub1,...`          Exclude the subreddits specified from the list mapped to the category. Subreddits to exclude must be seperated by a comma.\n `r! list -all`                                                   Lists all the available categories."""

	await msg.channel.send(message)

async def print_post_in_list(msg, listname, excluded_subs = []):
	custom_info_log(f'Received list command from user {msg.author.name} for {listname}')
	listname = listname.lower()

	if listname not in CATEGORIES.keys():
		logging.warning('Requested list does not exist in the loaded categories.')
		response = """Sorry, the category you requested does not exist. Try `r! help list` to see the help menu for the 'list' command."""
		await msg.channel.send(response)
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
			await handle_error(msg, 2)
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
				if e.code in [404, 302, 403]:
					custom_info_log('Retrying...')
				else:
					await handle_error(msg, e.code)

			if loop_check > len(subreddits):
				logging.warning('More failed requests than subreddits in the category: stopping here to avoid infine loop. Reddit may be down.')
				await handle_error(msg, 0)
				return

		await respond(msg, link, permalink, sub)


def get_random_post_from_subreddit(subreddit):

	url = 'https://oauth.reddit.com/r/' + subreddit + '/random'

	try:
		post_req = make_request(url, allow_redirects = True)
		if post_req.status_code == 200:
#			print(json.loads(post_req.text)[0]['data']['children'])

#			post_link = json.loads(post_req.text)[0]['data']['children']['url']
#			perma_link = json.loads(post_req.text)[0]['data']['children']['permalink']

			try:
				response_json = json.loads(post_req.text)
				post_link = response_json[0]['data']['children'][0]['data']['url']
				perma_link = response_json[0]['data']['children'][0]['data']['permalink']
			except:
				print(json.loads(post_req.text))
				raise RequestException(1)

			custom_info_log(f'Successfully got random post from {subreddit}')
			return post_link, perma_link
	except RequestException as e:
		raise RequestException(e.code)

async def print_post_from_subreddit(msg, subreddit):
	custom_info_log(f'Received random post command for {subreddit} from user {msg.author.name}')

	try:
		post_link, perma_link = get_random_post_from_subreddit(subreddit)
		await respond(msg, post_link, perma_link, subreddit)
	except RequestException as e:
		await handle_error(msg, e.code)


async def handle_error(msg, code):
	if code in [404, 302, 403]:
		message = """Sorry, it seems that this subreddit doesn't exist (anymore?)."""
	elif code == 0:
		message = """Sorry, something went very wrong and we didn't manage to get a link from any of the subreddits mapped to this category. Reddit may be down, in which case... good luck in the outside..."""
	elif code == 1:
		message = """Sorry, something went wrong, please reach out to us (nicely)!"""
	elif code == 2:
		message = """All the subreddits were filtered from the request."""

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
			if len(message_chunks) == 3:
				await print_help_menu(message, type = message_chunks[2])
			else:
				await print_help_menu(message)

		elif message_chunks[1] == 'top':
			if len(message_chunks) == 2:
				await print_help_menu(message, 'top')

			if len(message_chunks) == 3:
				await print_top_post(message, message_chunks[2])

			if len(message_chunks) == 4:
				if message_chunks[3].isdigit():
					await print_top_post(message, message_chunks[2], number=message_chunks[3])

				elif message_chunks[3] in ['hour','now','day','today','week','month','year','all']:
					await print_top_post(message, message_chunks[2], timespan=message_chunks[3])
				else:
					logging.warning(f'Received a top command from user {message.author.name} with wrong parameters.')
					response = """Bad command! Type `r! help` for the general help menu, and `r! help top` for the help menu for the 'top' command."""
					await message.channel.send(response)

			if len(message_chunks) == 5:
				if message_chunks[3].isdigit() and message_chunks[4] in ['hour','now','day','today','week','month','year','all']:
					await print_top_post(message, message_chunks[2], message_chunks[3], message_chunks[4])
				else:
					logging.warning(f'Received a top command from user {message.author.name} with wrong parameters.')
					response = """Bad command! Type `r! help` for the general help menu, and `r! help top` for the help menu for the 'top' command."""
					await message.channel.send(response)

		elif message_chunks[1] == 'list':
			if len(message_chunks) > 3:

				listname = message_chunks[2].lower()

				if message_chunks[3] == '-subs':
					if listname not in CATEGORIES.keys():
						logging.warning('Requested list {listname} does not exist in the loaded categories.')
						response = """Sorry, the category you requested does not exist. Try `r! help list` to see the help menu for the 'list' command."""
					else:
						subreddits = CATEGORIES[listname]['subreddits']
						response = 'The following subreddits are in the category \'' + listname + '\': ' +  ', '.join(subreddits)

					await message.channel.send(response)

				elif message_chunks[3] in ['-category_search','-cat_search','-catsearch','-csearch']:

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

				elif message_chunks[3] == '-search':

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

			elif message_chunks[2] == '-all':
				response = 'The following categories are available: ' + ', '.join(CATEGORIES.keys())
				await message.channel.send(response)
			elif len(message_chunks) == 2:
				await print_help_menu(message, 'list')
			else:
				await print_post_in_list(message, message_chunks[2])

		elif message_chunks[1] == 'rand':
			await print_post_from_subreddit(message, message_chunks[2])


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

	global ACCESS_TOKEN
	ACCESS_TOKEN = {'AT': '', 'EXPIRES': int(time())}

	client.run(TOKEN)
