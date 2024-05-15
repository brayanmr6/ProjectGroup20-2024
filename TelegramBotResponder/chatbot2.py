#  Programming for IoT applications - Project
# TelegramBotresponder.

# TelegramBot responder! This script is just a complementary function of the telegrambot, its only task is to subscribe to the
# the topics where the dataAnalytics.py script publishes the results of the user's functions chosen while usinf the Telegram chatbot.

# It was decided to be like that since the handling of the messages was easier, for some reason that I still don't know, it failed
# sometime when it was implemented in the original script, anyways, about some functionality:

# It does a GET request to the telegrambot script, because it needs to retrieve some information exposed in the json file "chatConfig"
# to be more precise it needs to know the GardenID, the garden that the user owns and of course, the chat ID to be sure that the message
# is sent to the corresponding chat!

import paho.mqtt.client as mqtt
import telepot
import json
import requests
import time

class messageReplier:
     
    def __init__(self):
        route = 'configFile.json'
        with open(route, 'r') as config_file:
            configFile = json.load(config_file)
        url = configFile["getchatdata"] 
        response = requests.get(url)
        chatdata = response.json()
        self.gardenID = chatdata["gardenID"]
        self.chatID = chatdata["chatID"]
        self.gardensUser = chatdata["gardensOwner"]

    def on_connect(self,client, userdata, flags, rc):
        print("Connected with result code "+str(rc))
        #client.subscribe("IoTProject/"+str(self.gardenID)+"/calculationresult")  # Subscribe to a topic upon connection
        for garden in self.gardensUser:
            client.subscribe("IoTProject/"+str(garden)+"/calculationresult")
        
        for garden in self.gardensUser:
            client.subscribe("IoTProject/"+str(garden)+"/alarm")

    def on_message(self,client, userdata, msg):
        #print(msg.topic+" "+str(msg.payload))  
        if str(msg.topic).endswith("/calculationresult"):
            self.send_telegram_message(msg.payload)  # Send the received message to Telegrm
        
        # ALARM SUBSCRIBER, VERY IMPORTANT!!!!!!!!!!11
        elif str(msg.topic).endswith("/alarm"):
            token = "7063657147:AAFWqTBUlui9mx6NwJqpDy7YcMA1d-tE7x8"
            bot = telepot.Bot(token)
            bot.sendMessage(self.chatID, text = str(msg.payload))

    def send_telegram_message(self,message):
        token = "7063657147:AAFWqTBUlui9mx6NwJqpDy7YcMA1d-tE7x8"
        bot = telepot.Bot(token)
        pretty_message = json.dumps(json.loads(message.decode("utf-8")), indent=4)
        bot.sendMessage(self.chatID, text="Result of your query:")
        bot.sendMessage(self.chatID, text=pretty_message)

with open("configFile.json", "r") as config_file:
                config = json.load(config_file)
url = config["registerService"]
body = {"name": "telegrambotresponder",
            "endpoint": "http://telegrambotresponder:8084/"}
response = requests.post(url, json=body)
time.sleep(20)
replier = messageReplier()
client = mqtt.Client()
client.on_connect = replier.on_connect
client.on_message = replier.on_message
client.connect("mqtt.eclipseprojects.io", 1883, 60)  
client.loop_forever()