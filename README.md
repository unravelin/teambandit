# Deprecation notice

**This project has been folded into [unravelin/slack-bandits](https://github.com/unravelin/slack-bandits).**

---

# teambandit

Teambandit is a slackbot to easily generate random teams for lunch.

Usage: enter /teambandit in slack. The app will wait an hour before generating teams based on the users that have reacted with emojis to the original message.

SLACK_API_TOKEN is an environment variable that you need to populate with the API token for your Slack instance.

SLEEP_TIME defines the length in seconds before teams are generated

teamSize defines the optimal team size.

Required slack scope:

- chat:write:bot

- chat:write:user

- reactions:read

- search:read

- users:read
