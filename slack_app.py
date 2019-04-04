import os
from slackclient import SlackClient
import time
from random import shuffle
import json
from flask import Flask, request, Response
import math
import threading

app = Flask(__name__)

slack_token = os.environ["SLACK_API_TOKEN"]

sc = SlackClient(slack_token)

teamSize = 5 # should be 5

SLEEP_TIME = 3600

threadMap = {}


@app.route('/teambandit', methods=['POST'])
def teambandit():
    channel_ID = request.form['channel_id']
    # Create a dict that we're passing along
    message = {'channel_id': channel_ID}
    thread1 = threading.Thread(target=launch_team_bandit, args=(message,))
    thread1.start()

    return Response('Team Bandit has entered the building...')


@app.route('/webhook', methods=['POST'])
def webhook():
    payload = json.loads(request.form["payload"])
    timestamp = payload['container']['message_ts']
    message = threadMap[timestamp]
    if (payload['actions'][0].get('action_id') == 'finalise'):
        update_message("Teams finalised! Bon apetit :shallow_pan_of_food:", message)
    if (payload['actions'][0].get('action_id') == 'regenerate'):
        teamMessageTime = generate_teams(threadMap[timestamp])
    return Response(status=200) 

def launch_team_bandit(message):
    timestamp = post_initial_message(message['channel_id'])
    message['initial_message'] = timestamp
    time.sleep(SLEEP_TIME/3) # sleeps for SLEEP_TIME/3 seconds
    sc.api_call(
          "chat.postMessage",
          text="Reminder to throw your hand up if you haven't yet! ^^ ",
          channel=message['channel_id']
        )
    time.sleep(SLEEP_TIME/3) # sleeps for SLEEP_TIME/3 seconds
    sc.api_call(
          "chat.postMessage",
          text="<!here> Final reminder - don't go lunchless!",
          channel=message['channel_id']
        )
    time.sleep(SLEEP_TIME/3) # sleeps for SLEEP_TIME/3 seconds
    message['lunchers'] = get_lunchers(message) # get the list of lunchers that reacted to the post at timestamp
    timestamp = generate_teams(message) # Print the teams, and return the time - updating the global teamMessageTime variable
    message['teamMessageTime'] = timestamp
    threadMap[timestamp] = message

def post_initial_message(channel_ID):
    res = sc.api_call(
      "chat.postMessage",
      text="<!here> Dearest hungry Raveliners, raise thy hand for lunch!",
      channel=channel_ID
    )
    timestamp = res['message']['ts']
    return timestamp

def update_message(upd, message):
    messageJSON = message['messageJSON'][0:-3]
    res = sc.api_call(
    "chat.update",
    ts = message['teamMessageTime'],
    channel=message['channel_id'],
    blocks=json.dumps(messageJSON)
    )

def get_lunchers(message):
    reactions = sc.api_call(
       "reactions.get",
       timestamp=message['initial_message'],
       channel=message['channel_id'],
       full=1
     )

    try:
        reactArray = reactions['message']['reactions']
    except KeyError:
        print ('sorry, no lunch')
        return []

    users = []

    for n in reactArray:
       users.append((n.get("users")))

    usersNoMatrix = []

    for row in users:
        for elem in row:
            usersNoMatrix.append(elem)

    return list(set(usersNoMatrix))


def generate_teams(message):
    #randomize the list
    
    shuffle(message['lunchers'])

    name_list = []
    # turn userID list into a list of names
    for user_ID in message['lunchers']:
        name_list.append(get_name_from_userid(user_ID))

    # teamList = samsSolution(name_list, teamSize)
    teamList = astridsSolution(name_list)


    messageJSON = 	[{
		"type": "section",
		"text": {
			"type": "mrkdwn",
			"text": "Teams are as follows:"
		}
	}]

    for team in teamList:
        messageJSON += displayTeam(team)

    messageJSON += [{
		"type": "divider"
	},{
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "Happy with the teams?:"
      }
    },{
		"type": "actions",
		"elements": [
			{
				"type": "button",
				"text": {
					"type": "plain_text",
					"emoji": True,
					"text": "Finalise selection"
				},
				"value": "finalise_button",
                "action_id": "finalise"
			},
			{
				"type": "button",
				"text": {
					"type": "plain_text",
					"emoji": True,
					"text": "Regenerate"
				},
				"value": "regenerate_button",
                "action_id": "regenerate"
			}
		]
	}]

    message['messageJSON'] = messageJSON

    if ('teamMessageTime' not in message):
        el = json.dumps(messageJSON)
        res = sc.api_call(
          "chat.postMessage",
          channel=message['channel_id'],
          blocks=json.dumps(messageJSON)
        )
        timestamp = res['message']['ts']
        return(timestamp)
    else:
        res = sc.api_call(
          "chat.update",
          channel=message['channel_id'],
          ts = message['teamMessageTime'],
          blocks=json.dumps(messageJSON)
        )
        timestamp = res['ts']
        return(timestamp)



def displayTeam(team):
    nameList = []
    for person in team:
        nameList.append({
				"type": "plain_text",
				"text": person,
				"emoji": True
			})
    return [{
		"type": "divider"
	},
	{
		"type": "section",
		"fields": nameList
	}]



def samsSolution(userList, teamSize):
    
    if (len(userList) <= teamSize): # if there's less than a single team, just return the list
        return [userList]
    else:
        overflowCount = len(userList)%teamSize

        if(overflowCount != 0): # if there's an overflow, increase the max team size to make space for the larger teams
            teamSize +=1 

        teamList = [[0 for x in range(teamSize)] for y in range(int(len(userList)/teamSize))] 
        # initialise empty teamlist

        teamCount = 0

        positionInTeamCount = 0
        
        for user in userList:
            if positionInTeamCount >= teamSize: # if there are the max amount of users in the team
                if overflowCount == 0:
                    positionInTeamCount = 0 # reset the position count to zero
                    teamCount +=1 # increment the teamcount
                else: # if there is an overflow, allow further entries into the first teams until we reach the end of the overflow
                    overflowCount -= 1 
            teamList[teamCount][positionInTeamCount] = user # insert into the team list matrix
            positionInTeamCount += 1 # increment the position in team count to insert the next user in the right slot

        return teamList

def astridsSolution(group_list):
    if (len(group_list) <= teamSize): # if there's less than a single team, just return the list
        return [group_list]
    else:

        group_size = len(group_list)

        team_number = math.ceil(group_size/teamSize) # We want that many teams

        teams = []
        for i in range(0, team_number):
            teams.append([])

        for i, luncher in enumerate(group_list):
            if i < team_number:
                teams[i].append(luncher)
            else:
                m = i % team_number
                teams[m].append(luncher)

        return teams

def get_name_from_userid(userID):
    userInfo = sc.api_call("users.info", user = userID)
    return  userInfo['user']['profile'].get('real_name')

if __name__ == '__main__':  
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)







