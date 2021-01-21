# Reddiator bot module file
# Module name: utils-reddit
# Version: 1.0

# Description: This module deals with everything related to Reddit

import reddiator

import os, logging

import requests
from requests.auth import HTTPBasicAuth

from dotenv import load_dotenv

import json

from random import randint

from time import time


class RequestException(Exception):
# Error codes :
# 0 = Other error
# 1 = Problem finding the requested subreddit (404, subreddit not found, redirected to search, etc.)
# 2 = Requested subreddit is private
# 3 = Requested subreddit is banned
# 4 = Requested subreddit is quarantined
# 5 = Problem with the Access Token

	def __init__(self, code):
		super().__init__(code)
		self.code = code

def custom_info_log(msg):
	logger = logging.getLogger('utils.reddit')
	logger.log(21, '\t' + msg)

def get_nsfw_status(subreddit):
	headers = {'User-Agent' : os.getenv('REDDIT_USER_AGENT')}

	post_req = requests.get('https://www.reddit.com/r/'+subreddit+'/about.json', headers=headers, allow_redirects = True)

	content = json.loads(post_req.text)
	if content['data']['over18']:
		custom_info_log('NSFW subreddit!')
		return True
	else:
		custom_info_log('Subreddit is SFW :)')
		return False

# This function is responsible for fetching a new OAuth access token when necessary.
def get_access_token():

	global ACCESS_TOKEN

	if len(ACCESS_TOKEN['AT']) == 0 or ACCESS_TOKEN['EXPIRES'] < int(time()):
		custom_info_log('No AT currently registered, or current AT expired, requesting a new one')
		token_req = requests.post('https://www.reddit.com/api/v1/access_token', auth = HTTPBasicAuth(os.getenv('REDDIT_CLIENT_ID'), os.getenv('REDDIT_CLIENT_SECRET')), data = 'grant_type=refresh_token&refresh_token=' + os.getenv('REDDIT_REFRESH_TOKEN'), headers = {'User-Agent' : os.getenv('REDDIT_USER_AGENT')})

		try:
			response_json = json.loads(token_req.text)
		except:
			logging.error('Error making the request for an AT (or parsing the response). Reddit may be down, or something may be wrong with the bot account (RT revoked?)')
			print(token_req.status_code)
			print(token_req.text)

		try:
			expires = int(time()) + response_json['expires_in']
			at = response_json['access_token']
			custom_info_log(f'Retrieved Reddit AT : {at}')
		except:
			logging.error(f'Error parsing the response from the AT request, no AT and expires attribute found in JSON. RT may be invalid?\nJSON response value: {response_json}')
			raise RequestException(5)

		ACCESS_TOKEN = {'AT': at, 'EXPIRES': expires}
		return at

	else:
		custom_info_log('Looks like our access token is still valid, let\'s reuse it')
		return ACCESS_TOKEN['AT']


# This function is responsible for making the actual request to Reddit's API.
# It will simply take an url as parameter, and perform a get on the page.
def make_request(url, allow_redirects = False):
	at = get_access_token()
	headers = {'Authorization' : 'Bearer ' + at, 'User-Agent' : os.getenv('REDDIT_USER_AGENT')}

	post_req = requests.get(url, headers=headers, allow_redirects = allow_redirects)

	if post_req.status_code == 200 and post_req.text != '{"kind": "Listing", "data": {"modhash": null, "dist": 0, "children": [], "after": null, "before": null}}':
		return post_req
	elif post_req.status_code == 404:
		if 'banned' in post_req.text:
			logging.warning('Request to get a random post from specified subreddit failed with a HTTP 404 error: the subreddit has been banned.')
			raise RequestException(3)
		else:
			logging.warning('Request to get a random post from specified subreddit failed with a HTTP 404 error. The subreddit may not exist anymore.')
			raise RequestException(1)
	elif post_req.status_code == 302 and 'search?q=' in post_req.text:
		logging.warning('Request to get a random post from specified subreddit returned with a HTTP 302 error redirecting to the search page: the subreddit probably doesn\'t exist.')
		raise RequestException(1)
	elif post_req.status_code == 403:
		if 'private' in post_req.text:
			logging.error('Request to get a random post from specified subreddit failed with a HTTP 403 code, the subreddit is private.')
			raise RequestException(2)
		elif 'quarantined' in post_req.text:
			logging.error('Request to get a random post from specified subreddit failed with a HTTP 403 code, the subreddit is quarantined.')
			raise RequestException(4)
		else:
			logging.error('Request to get a random post from specified subreddit failed with a HTTP 403 code, but the subreddit does not seem private or quarantined.')
			raise RequestException(0)
	elif post_req.status_code == 200:
		logging.warning('Request to get a random post from specified subreddit failed with a HTTP 200 error but an empty body. The subreddit may not exist anymore.')
		raise RequestException(1)
	else:
		logging.error(f'Request to get a random post from specified subreddit failed with a HTTP {post_req.status_code} error.\nThe response headers are:\n{post_req.headers}\nThe response body is:\n{post_req.text}')
		raise RequestException(0)


# This function is repsonsible for fetching a single random post from Reddit's API.
def get_random_post_from_subreddit(subreddit):

	url = 'https://oauth.reddit.com/r/' + subreddit + '/random'

	try:
		post_req = make_request(url, allow_redirects = True)
#                       print(json.loads(post_req.text)[0]['data']['children'])
#                       post_link = json.loads(post_req.text)[0]['data']['children']['url']
#                       perma_link = json.loads(post_req.text)[0]['data']['children']['permalink']

		try:
			response_json = json.loads(post_req.text)
			try:
				post_link = response_json[0]['data']['children'][0]['data']['url']
				perma_link = response_json[0]['data']['children'][0]['data']['permalink']
			except Exception as e:
				logging.error('Error reading the JSON data returned by Reddit API')
				logging.error(f'JSON data: {response_json}')
				raise RequestException(0)
		except:
			logging.error('Error parsing the JSON returned by Reddit API')
			logging.error(f'Response headers: {post_req.headers}')
			logging.error(f'Response body: {post_req.text}')
			raise RequestException(0)

		custom_info_log(f'Successfully got random post from {subreddit}')
		return post_link, perma_link
	except RequestException as e:
		raise RequestException(e.code)


def get_top_post_from_subreddit(subreddit, number, timespan):

	url = 'https://oauth.reddit.com/r/' + subreddit + '/top?t=' + timespan + '&limit=' + str(number)

	try:
		post_req = make_request(url, allow_redirects = False)
		links = [items['data']['url'] for items in json.loads(post_req.text)['data']['children']]
		permalinks = [items['data']['permalink'] for items in json.loads(post_req.text)['data']['children']]

		custom_info_log(f'Successfully fetched {str(len(links))} links frop top posts')

		random_index = randint(0, len(links) - 1)
		custom_info_log(f'Link #{random_index} was chosen')

		return links[random_index], permalinks[random_index]
	except RequestException as e:
		raise RequestException(e.code)


global ACCESS_TOKEN
ACCESS_TOKEN = {'AT': '', 'EXPIRES': int(time())}
load_dotenv()
