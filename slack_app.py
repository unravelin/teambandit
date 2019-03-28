import os
from slackclient import SlackClient
import time
from random import shuffle
import json
from flask import Flask, request, Response
import math
import threading
from datetime import datetime

app = Flask(__name__)

slack_token = os.environ["SLACK_API_TOKEN"]

sc = SlackClient(slack_token)

teamSize = 5 # should be 5

SLEEP_TIME = 600

threadMap = {}


@app.route('/teambandit', methods=['POST'])
def teambandit():
    channel_ID = request.form['channel_id']
    # Create a dict that we're passing along
    message = {'channel_id': channel_ID}
    thread1 = threading.Thread(target=launch_team_bandit, args=(message,))
    thread1.start()
    thread2 = threading.Thread(target=cleanupMap)
    thread2.start()

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
    time.sleep(SLEEP_TIME/2) # sleeps for SLEEP_TIME/2 seconds
    sc.api_call(
          "chat.postMessage",
          text="<!channel> Reminder to throw your hand up if you haven't yet! ^^ ",
          channel=message['channel_id']
        )
    time.sleep(SLEEP_TIME/2) # sleeps for SLEEP_TIME/2 seconds
    message['lunchers'] = get_lunchers(message) # get the list of lunchers that reacted to the post at timestamp
    timestamp = generate_teams(message) # Print the teams, and return the time - updating the global teamMessageTime variable
    message['teamMessageTime'] = timestamp
    threadMap[timestamp] = message

def post_initial_message(channel_ID):
    res = sc.api_call(
      "chat.postMessage",
      text="<!channel> Dearest hungry Raveliners, raise thy hand for lunch!",
      channel=channel_ID
    )
    timestamp = res['message']['ts']
    return timestamp

def update_message(upd, message):
    jsonList = [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "<!channel> Teams are as follows: "  + ", ".join(message['team_list'])
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ""  + upd
            }
        }]
    res = sc.api_call(
    "chat.update",
    ts = message['teamMessageTime'],
    channel=message['channel_id'],
    blocks=json.dumps(jsonList)
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

    stringTeamList = [str(teams) for teams in teamList]
    message['team_list'] = stringTeamList

    jsonList = [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Teams are as follows:"  + ", ".join(stringTeamList)
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Happy with the teams?" 
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Finalise selection",
                },
                "value": "finalise_button",
                "action_id": "finalise"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Teams not random enough?"
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Re-generate Teams!",
                },
                "value": "regenerate_button",
                "action_id": "regenerate"
            }
        }]

    if ('teamMessageTime' not in message):
        res = sc.api_call(
          "chat.postMessage",
          channel=message['channel_id'],
          blocks=json.dumps(jsonList)
        )
        timestamp = res['message']['ts']
        return(timestamp)
    else:
        res = sc.api_call(
          "chat.update",
          channel=message['channel_id'],
          ts = message['teamMessageTime'],
          blocks=json.dumps(jsonList)
        )
        timestamp = res['ts']
        return(timestamp)


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

        # This transitional number is important to work our how many teams will have fewer people
        top_group = team_number*teamSize
        # Now we know. there will be {smaller_teams} teams with fewer people
        smaller_teams = top_group - group_size

        # And the rest are normal teams
        normal_teams = team_number - smaller_teams

        # sanity check?
        is_that_the_total = smaller_teams*(teamSize-1)+ normal_teams*teamSize


        print("{} teams with {} members and {} teams with {} members = {}".format(normal_teams, teamSize, smaller_teams, teamSize-1, is_that_the_total))

        ##### Ok, how do we generate those teams?

        # here's what's going to be an list of lists
        teams = []
        j = 0

        if normal_teams > 0:
            # If there should be 4 teams of X, we do this 4 times
            for i in range(0, normal_teams):
                # We take a chunk of the main list
                team = group_list[j:j+teamSize]
                # append a list with that chunk to the list list
                teams.append(team)
                # increment j to take the next chunk
                j += teamSize

        if smaller_teams > 0:
            # If there should be 3 teams of X-1, we do this 3 times
            for i in range (0, smaller_teams):
                team = group_list[j:j+teamSize-1]
                teams.append(team)
                j += teamSize-1
            
        return teams

def cleanupMap():
    for ts in threadMap:
        dt = datetime.fromtimestamp(int(ts))
        if dt < datetime.now() - datetime.day:
            del threadMap[ts]

def get_name_from_userid(userID):
    userInfo = sc.api_call("users.info", user = userID)
    return  userInfo['user']['profile'].get('real_name')

def astridTestsThings():
    teams = [['cgark', 'bhavu', 'dawb'], ['sam', 'astrid', 'katrina'], ['alice', 'ji', 'mark']]

    dividerObject = {"type": "divider"}
    introObject = {"type": "section", "text": {
                "type": "mrkdwn",
                "text": "Here are the teams:"
            }}

    teamsObjects = [dividerObject, introObject]

    for team in teams:
      fields = []
      for user in team:
        fields.append({
                    "type": "plain_text",
                    "text": user,
                    "emoji": True
                })
      teamsObjects.append(dividerObject)
      teamsObjects.append({
            "type": "section",
            "fields": fields
        })
    res = sc.api_call(
      "chat.postMessage",
      channel=channel_ID,
      blocks=json.dumps(teamsObjects)
    )

    print(json.dumps(teamsObjects))

if __name__ == '__main__':  
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)







