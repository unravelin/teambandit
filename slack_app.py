import os
import pprint
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

pp = pprint.PrettyPrinter(indent=2)

general_ID="C5G0X66A0"

teamSize = 5 # should be 5

teamMessageTime = 0

lunchers = []

stringTeamList = ""


@app.route('/teambandit', methods=['POST'])
def teambandit():
    print(request.data)
    thread1 = threading.Thread(target=launch_team_bandit)
    thread1.start()
    
    return Response('Team Bandit has entered the building...')


@app.route('/webhook', methods=['POST'])
def webhook():
    global lunchers
    global teamMessageTime
    payload = json.loads(request.form["payload"])
    if (payload['actions'][0].get('action_id') == 'finalise'):
        update_message("Teams finalised! Bon apetit :shallow_pan_of_food:", teamMessageTime)
    if (payload['actions'][0].get('action_id') == 'regenerate'):
        print(teamMessageTime)
        generate_teams(lunchers, teamSize)
    return Response(status=200) 

def launch_team_bandit():
    timestamp = post_initial_message()
    print(timestamp)
    time.sleep(5)
    global lunchers
    global teamMessageTime
    lunchers = get_lunchers(timestamp)
    teamMessageTime = generate_teams(lunchers, teamSize)



def post_initial_message():
    res = sc.api_call(
      "chat.postMessage",
      text="Dearest hungry Raveliners, raise thy hand for lunch!",
      channel=general_ID
    )
    pp.pprint(res)
    timestamp = res['message']['ts']
    return timestamp

def update_message(message, time):
    print("In update message!")
    print(teamMessageTime)
    global stringTeamList
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
                "text": ""  + message
            }
        }]
    res = sc.api_call(
      "chat.update",
      ts = time,
      channel=general_ID,
      blocks=json.dumps(jsonList)
    )
    print(res)

def get_lunchers(messageTime):
    reactions = sc.api_call(
       "reactions.get",
       timestamp=messageTime,
       channel=general_ID,
       full=1
     )
    print(reactions)

    try:
        reactArray = reactions['message']['reactions']
    except KeyError:
        print ('sorry, no lunch')
        return []

    print(reactions)

    users = []

    for n in reactArray:
       users.append((n.get("users")))

    usersNoMatrix = []

    for row in users:
        for elem in row:
            usersNoMatrix.append(elem)

    print(list(set(usersNoMatrix)))

    #de-dupe the list
    return list(set(usersNoMatrix))


def generate_teams(uniqueUserList, teamSize):
    #randomize the list
    shuffle(uniqueUserList)

    name_list = []
    # turn userID list into a list of names
    for user_ID in uniqueUserList:
        name_list.append(get_name_from_userid(user_ID))

    # teamList = samsSolution(name_list, teamSize)
    teamList = astridsSolution(name_list, teamSize)
    
    global stringTeamList

    stringTeamList = [str(teams) for teams in teamList]

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

    if (teamMessageTime == 0):
        res = sc.api_call(
          "chat.postMessage",
          channel=general_ID,
          blocks=json.dumps(jsonList)
        )
        timestamp = res['message']['ts']
        return(timestamp)
    else:
        res = sc.api_call(
          "chat.update",
          channel=general_ID,
          ts = teamMessageTime,
          blocks=json.dumps(jsonList)
        )
        print("returning here")
        print(res)
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

        print (teamList)

        return teamList

def astridsSolution(group_list, team_size):
    if (len(group_list) <= team_size): # if there's less than a single team, just return the list
        return [group_list]
    else:

        group_size = len(group_list)

        team_number = math.ceil(group_size/team_size) # We want that many teams

        # This transitional number is important to work our how many teams will have fewer people
        top_group = team_number*team_size
        # Now we know. there will be {smaller_teams} teams with fewer people
        smaller_teams = top_group - group_size

        # And the rest are normal teams
        normal_teams = team_number - smaller_teams

        # sanity check?
        is_that_the_total = smaller_teams*(team_size-1)+ normal_teams*team_size


        print("{} teams with {} members and {} teams with {} members = {}".format(normal_teams, team_size, smaller_teams, team_size-1, is_that_the_total))

        ##### Ok, how do we generate those teams?

        # here's what's going to be an list of lists
        teams = []
        j = 0

        if normal_teams > 0:
            # If there should be 4 teams of X, we do this 4 times
            for i in range(0, normal_teams):
                # We take a chunk of the main list
                team = group_list[j:j+team_size]
                # append a list with that chunk to the list list
                teams.append(team)
                # increment j to take the next chunk
                j += team_size

        if smaller_teams > 0:
            # If there should be 3 teams of X-1, we do this 3 times
            for i in range (0, smaller_teams):
                team = group_list[j:j+team_size-1]
                teams.append(team)
                j += team_size-1
            
        print(teams)

        return teams

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
      channel=general_ID,
      blocks=json.dumps(teamsObjects)
    )

    print(json.dumps(teamsObjects))

if __name__ == '__main__':  
    port = int(os.environ.get('PORT', 4390))
    app.run(host='0.0.0.0', port=port, debug=True)  







