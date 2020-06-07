#!/usr/bin/python3

#== Name:		reddiator.py
#== Version:		v0.1
#== Description:	A Discord Bot to post reddit content automatically to channels
#
#
#== Available commands:
#
#= r! $subreddit
#- Responds with a random post from the specified subreddit
###
#
#= r! top $subreddit [N] [period]
#- Responds with a random post from the top posts of the specified subreddit.
#
#- Optionnal parameter [N] can be used to specify how many top posts must be loaded.
#- Default value is 25.
###
#
#- Optionnal paramerer [period] can be used to specify the top posts period. Supported value are all, year, month, week, day/today, hour/now.
#- Default value is all.
#
#= r! list $category
#- Responds with a random post taken from a list of pre-defined subreddits mapped to the specified category.
#- Subreddits categories and corresponding subreddits are loaded from a file during script startup.
#= r! list_subs $category
#- Responds with the list of subreddits mapped to the specified category.
#TODO	=> possible add-in: exclude a list of subreddits from pre-defined list for $category: r!list $category -e sub1,sub2,sub3...
###
#
#- r! help [command]
# Responds with a help menu detailing the correct syntax for the specified command.
# If no command is specified, the bot will display the general help menu, with the available commands


#TODO: implement correct logging instead of print
#https://docs.python.org/3/howto/logging.html

import os

import discord
from dotenv import load_dotenv

import requests
from requests.auth import HTTPBasicAuth
import logging

import json

from random import randint

client = discord.Client()


def load_categories(filename):
	with open(filename, 'r') as f:
		categories = {}
		for line in f.readlines():
			line_split = line.split(':')
			categories[line_split[0]] = line_split[1].split(',')
	return categories


def get_access_token():
	token_req = requests.post('https://www.reddit.com/api/v1/access_token', auth = HTTPBasicAuth(os.getenv('REDDIT_CLIENT_ID'), os.getenv('REDDIT_CLIENT_SECRET')), data = 'grant_type=refresh_token&refresh_token=' + os.getenv('REDDIT_REFRESH_TOKEN'), headers = {'User-Agent' : os.getenv('REDDIT_USER_AGENT')})
	at = json.loads(token_req.text)['access_token']
	print('Retrieved Reddit AT : ' + at)
	return at

def make_request(method, url, allow_redirects = False):
	# TODO : implement proper HTTP request/error and response handling
	# this methods either returns the body and headers of response, or handles errors (404, 403, 401, 500) graciously)
	print('')

async def respond(msg,link):
	# TODO implement option to beautify response sent to server, to format it correctly
	# could also keep the option of sending the raw post to avoid spoiler and blur nsfw content (only providing the link)
	await msg.channel.send(link)

async def print_top_post(msg, subreddit, number = 25, timespan = 'all'):
	print('print_top_post')
	at = get_access_token()
	headers = {'Authorization' : 'Bearer ' + at, 'User-Agent' : os.getenv('REDDIT_USER_AGENT')}
	post_req = requests.get('https://oauth.reddit.com/r/' + subreddit + '/top?t=' + timespan + '&limit=' + str(number), headers = headers, allow_redirects = False)
	print(post_req.status_code)
	print(post_req.headers)
	links = [items['data']['url'] for items in json.loads(post_req.text)['data']['children']]

	print('## Fetched ' + str(len(links)) + ' links\n')

	random_index = randint(0, len(links) - 1)

	await respond(msg, links[random_index])


async def print_help_menu(msg, type = 'general'):
	print('help menu requested')
	if type == 'general' or type not in ['general', 'top', 'list']:
		print('general help menu')
	if type == 'top':
		print('top help menu')
	if type == 'list':
		print('list help menu')

async def print_post_in_list(msg, listname):
	print('print_post_in_list')
	if listname not in CATEGORIES.keys():
		print('Requested category not in list of categories loaded.')
	else:
		subreddits = CATEGORIES[listname]
		print('Got ' + str(len(subreddits)) + ' subreddits matching category')
		links = {}
		for sub in subreddits:
			print(sub)
			links[sub] = get_random_post_from_subreddit(sub)

		print('## Fetched ' + str(len(links)) + ' links\n')

		random_index = randint(0, len(links) - 1)
		print(random_index)

		await respond(msg, links[list(links.keys())[random_index]])


def get_random_post_from_subreddit(subreddit):
	print('get_post_from_subreddit')
	at = get_access_token()
	headers = {'Authorization' : 'Bearer ' + at, 'User-Agent' : os.getenv('REDDIT_USER_AGENT')}
	post_req = requests.get('https://oauth.reddit.com/r/' + subreddit + '/random', headers = headers, allow_redirects = True)
	print(post_req.headers)
	print(post_req.text)
	if post_req.status_code == 200:
		print('ok got a post')
		post_link = json.loads(post_req.text)[0]['data']['children'][0]['data']['url']
		print('## Fetched ' + str(len(post_link)) + ' links\n')
		return post_link
	elif post_req.status_code == 404:
		print('Subreddit not found')
		return ''
	else:
		print('Other error : ' + str(post_req.status_code))
		print('RESPONSE HEADERS:\n')
		print(post_req.headers)
		print('\n\n RESPONSE BODY:\n')
		print(post_req.text)
		return ''

async def print_post_from_subreddit(msg, subreddit):
	print('print_post_from_subreddit')
	post_link = get_random_post_from_subreddit(subreddit)
	if len(post_link) > 0:
		await respond(msg, post_link)

@client.event
async def on_ready():
	print(f'{client.user} is now connect to the Discord server!')

@client.event
async def on_message(message):
	if message.author == client.user:
		return

	message_chunks = message.content.split(' ')

	if message_chunks[0] == 'r!' and len(message_chunks) > 1:
		print(f'Received a message for the bot: {message.content}')


		if message_chunks[1] == 'help':
			print('Help menu requested by user')
			await print_help_menu(message)

		elif message_chunks[1] == 'top':
			print('Top post of a subreddit requested by user')
			if len(message_chunks) == 3:
				print('defaulting to 25 top posts of all time')
				await print_top_post(message, message_chunks[2])
			if len(message_chunks) == 4:
				print('received either number or timespan')
				if message_chunks[3].isdigit():
					print('number: ' + str(message_chunks[3]))
					await print_top_post(message, message_chunks[2], number=message_chunks[3])
				elif message_chunks[3] in ['hour','now','day','today','week','month','year','all']:
					print('timespan: ' + str(message_chunks[3]))
					await print_top_post(message, message_chunks[2], timespan=message_chunks[3])
				else:
					print('wrong parameter')
					response = """Bad command! Type 'r! help' for the help menu, and 'r! help top' for the top command help menu"""
					await message.channel.send(response)
			if len(message_chunks) == 5:
				print('received both number ('+str(message_chunks[3])+') and timespan ('+str(message_chunks[4])+')')
				if message_chunks[3].isdigit() and message_chunks[4] in ['hour','now','day','today','week','month','year','all']:
					print('command ok')
					await print_top_post(message, message_chunks[2], message_chunks[3], message_chunks[4])
				else:
					print('wrong parameter')
					response = """Bad command! Type 'r! help' for the help menu, and 'r! help top' for the top command help menu"""
					await message.channel.send(response)

		elif message_chunks[1] == 'list':
			print('random post from list of subreddits requested')
			await print_post_in_list(message, message_chunks[2])

		else:
			print('random post in a subreddit requested')
			await print_post_from_subreddit(message, message_chunks[1])

	else:
		print('Bad command or no command received, responding with help menu hint.')
		response = """Bad command! Type 'r! help' for the help menu!"""
		await message.channel.send(response)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

CATEGORIES_FILENAME = os.getenv('CATEGORIES_FILENAME')
if len(CATEGORIES_FILENAME) > 0:
        CATEGORIES = load_categories(CATEGORIES_FILENAME)
else:
        print("Skipped categories loading.")
        CATEGORIES = {}

client.run(TOKEN)
