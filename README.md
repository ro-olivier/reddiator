# reddiator
A Discord Bot to automatically post Reddit content to Discord channels.

Written for Python 3, tested with Python 3.8.2

#### Dependencies:
- [python-dotenv](https://pypi.org/project/python-dotenv/)  
- [discord.py](https://pypi.org/project/discord.py/)  
- [requests](https://pypi.org/project/requests/)  

Calls to the Reddit API were implemented manually using `requests` and `json` because [PRAW](https://praw.readthedocs.io/en/latest/) was to heavy for the limited usage of this script. I recommand using PRAW instead for any project were complex Reddit API calls are necessary.

#### Bot commands (in Discord):
The bot responds to the following commands:  

| Command                        	| Description                                                                                                                                                                         	|
|-----------------------------------	|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------	|
| `r! rand $subreddit`             	   | Displays a random post from the specified subreddit.                                                                                                                                	|
| `r! top $subreddit [N] [period]` 	   | Displays a random post from the top posts of the specified subreddit.<br>By default will look into the top 10 post of all time.<br>Parameters N and period can be used to change that. 	|
| `r! list $category [-subs]`      	   | Displays a random post from a selection of subreddits mapped to a category.<br>The optional flag subs will list the subreddits linked to the specified category.                       	|
| `r! help $command`               	| Prints the help menu for the command specified.                                                                                                                                     	|


#### Script usage:
> ./reddiator -l info -f reddiator.log  
> -h : displays the help menu  
> -f \<logfile name\> --logfile=\<logfile name\> : specify the file where the logs should be recorded   
> -l \<level> --loglevel=\<level\> : specify the level of the logs you want the script to record (available values are 'info', 'warn' and 'error')  

## How to setup: 
1. Copy the script to your system.

2. Create a `.env` file in the same folder than the script, and copy the following content. Put your `REDDIT_CLIENT_ID` both in the variable with the same name and in the `REDDIT_USER_AGENT` variable.
>\# .env  
>DISCORD_TOKEN=''  
>REDDIT_CLIENT_ID=''  
>REDDIT_CLIENT_SECRET=''  
>REDDIT_REFRESH_TOKEN=''  
>REDDIT_USER_AGENT='Reddiator-bot-**REDDIT_CLIENT_ID**'  
>CATEGORIES_FILENAME=''  

3. Create a Discord Application and associated Bot (follow [this tutorial](https://realpython.com/how-to-make-a-discord-bot-python/#creating-a-discord-account)). Copy your Discord bot Token in the `.env` file.

4. Follow the direction on [this page](https://github.com/reddit-archive/reddit/wiki/OAuth2) to create a Reddit App, authorize it to use your Reddit account (or an account you've created specifically for this bot) and retrieve the `client_id`, `client_secret` and `refresh_token`. Copy these into the `.env` file.

5. If you want to, create a file with a name of your chosing (don't forget to copy it in the last property of the `.env` file) for the categories of subreddits that you want the bot to respond to with the list command. The file should have the following structure:  
>category_1:subreddit_1,subreddit_1,subreddit_3...  
>category_2:subreddit_4,subreddit_5,subreddit_6...  
>...

6. Make the script executable:  
> chmox +x ./reddiator.py

7. And run the script. To run it in the background and keep it running if you close the terminal, use the following command:
> nohup ./reddiator.py &

The script automatically kills any previously running instance when it is started.
