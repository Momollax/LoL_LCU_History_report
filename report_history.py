import sys
import requests
import json
from time import sleep
import platform
import psutil
import base64
from os import system, name
from lcu_driver import Connector
from riotwatcher import LolWatcher, ApiError
import warnings
import asyncio

warnings.filterwarnings('ignore')
# variables

app_port = None
auth_token = None
riotclient_auth_token = None
riotclient_app_port = None
region = None
lcu_name = None   # LeagueClientUx executable name
showNotInChampSelect = True
# functions


def getLCUName():
    '''
    Get LeagueClient executable name depending on platform.
    '''
    global lcu_name
    if platform.system() == 'Windows':
        lcu_name = 'LeagueClientUx.exe'
    elif platform.system() == 'Darwin':
        lcu_name = 'LeagueClientUx'
    elif platform.system() == 'Linux':
        lcu_name = 'LeagueClientUx'


def LCUAvailable():
    '''
    Check whether a client is available.
    '''
    return lcu_name in (p.name() for p in psutil.process_iter())


def getLCUArguments():
    global auth_token, app_port, region, riotclient_auth_token, riotclient_app_port
    '''
    Get region, remoting-auth-token and app-port for LeagueClientUx.
    '''
    if not LCUAvailable():
        sys.exit('No ' + lcu_name + ' found. Login to an account and try again.')

    for p in psutil.process_iter():
        if p.name() == lcu_name:
            args = p.cmdline()

            for a in args:
                if '--region=' in a:
                    region = a.split('--region=', 1)[1].lower()
                if '--remoting-auth-token=' in a:
                    auth_token = a.split('--remoting-auth-token=', 1)[1]
                if '--app-port' in a:
                    app_port = a.split('--app-port=', 1)[1]
                if '--riotclient-auth-token=' in a:
                    riotclient_auth_token = a.split('--riotclient-auth-token=', 1)[1]
                if '--riotclient-app-port=' in a:
                    riotclient_app_port = a.split('--riotclient-app-port=', 1)[1]

                    
def clear():
    # for windows
    if name == 'nt':
        _ = system('cls')
    # for mac and linux(here, os.name is 'posix')
    else:
        _ = system('clear')



connector = Connector()
@connector.ready



async def setup_client(connection):
        
    global showNotInChampSelect

    getLCUName()

    getLCUArguments()

    lcu_api = 'https://127.0.0.1:' + app_port
    riotclient_api = 'https://127.0.0.1:' + riotclient_app_port

    lcu_session_token = base64.b64encode(
        ('riot:' + auth_token).encode('ascii')).decode('ascii')

    riotclient_session_token = base64.b64encode(
        ('riot:' + riotclient_auth_token).encode('ascii')).decode('ascii')

    lcu_headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Basic ' + lcu_session_token
    }

    riotclient_headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'LeagueOfLegendsClient',
        'Authorization': 'Basic ' + riotclient_session_token
    }
    
    get_current_summoner = lcu_api + '/lol-summoner/v1/current-summoner'
    headers = {'Content-type': 'application/json'}
    r = requests.get(get_current_summoner, headers=lcu_headers, verify=False)
    r = json.loads(r.text)
    print("Welcome to the League of Legends swap bot :)!")
    print('Connected: ' + r['displayName'])
    myself=r['displayName']
    getMatchId = lcu_api + '/lol-match-history/v1/products/lol/current-summoner/matches'
    r = requests.get(getMatchId, headers=lcu_headers, verify=False)
    r = json.loads(r.text)
    tmp = await connection.request('get', '/lol-chat/v1/friends')
    tmp = await tmp.json()
    friends = [entry["gameName"] for entry in tmp]
    games_list = r["games"]["games"]
    game_ids = [game["gameId"] for game in games_list]
    for game_id in game_ids:
        get_match_history = lcu_api + '/lol-match-history/v1/games/' + str(game_id)
        r = requests.get(get_match_history, headers=lcu_headers, verify=False)
        r = json.loads(r.text)
        with open("sample.json", "w") as outfile: 
            json.dump(r, outfile) 
        participant_identities = r["participantIdentities"]
        summoner_info = [{"summonerName": participant["player"]["summonerName"],
                          "puuid": participant["player"]["puuid"],
                          "summonerId": participant["player"]["summonerId"]}
                         for participant in participant_identities]
        for info in summoner_info:
            if myself == info["summonerName"]:
                continue
            if info["summonerName"] in friends:
                continue
            _report = {
                "comment": "trash talk, toxic, racist",
                "gameId": game_id,
                "categories": ["NEGATIVE_ATTITUDE", "VERBAL_ABUSE", "LEAVING_AFK", "ASSISTING_ENEMY_TEAM", "HATE_SPEECH"],
                "offenderPuuid": info["puuid"],
                "reportedSummonerId": info["summonerId"]
            }
            response = await connection.request('post', "/lol-player-report-sender/v1/end-of-game-reports", data=_report)
            response = await response.json()

            print(info["summonerName"], "have been reported")

connector.start()