# Programming for IoT applications - Project
# Telegram bot

# Insights:
# Okay, this script is part of the whole bot service works in this way:
# Firsty, the bot script using the teleport library requires the TOKEN generated by the Godfather, this TOKEN 
# which the user/administrator must register in the catalog (using a POST reques) this script requests a GET to the
# catalogManager webservice and then proceeds with the token creation.
# Secondly, in a similar manner, another GET request needs to be done to the catalog, because the Telegram Bot
# in order to work and perform operations, an user needs to 'log-in'. Let's remember that there are different GET request according to 
# the actors from the catalog, in particular we care about the users to log in.
# After an user succesfully logs-in, (username and password) there are different operations to do:
# 1) show the user gardens, it essencialy performs a GET request to the catalog particularly to the gardens and displays them.
# 2) show the average of available measurements from the last hour, whenever the user selects this on the telegram chat, a MQTT
# message is generated and sent to the message broker and then to the dataAnalytics.py service, the result from that service is also sent
# as a MQTT message, but the entity which subscribes is not this script but chatbot2.py, it also sends the result to the chatbot.
# 3) show the average of available measurements from the last day, whenever the user selects this on the telegram chat, a MQTT
# message is generated and sent to the message broker and then to the dataAnalytics.py service, the result from that service is also sent
# as a MQTT message, but the entity which subscribes is not this script but chatbot2.py, it also sends the result to the chatbot.
# 4) VERY IMPORTANT: SUBSCRIBE TO THE ALARM, IF A MEASUREMENT FROM A SENSOR IS ABNORMAL, AN ALARM IS SENT TO THE TELEGRAM CHAT, IF AND ONLY
# IF THE USER IS LOGGED-IN, otherwise it is not possible and makes no sense.
# 5) As stated on the proposal, telegram chatbot should be able to turn the external light service from the garden on/off, this is employed
# by a PUT requests to the catalog.
#6 ) RETRIEVE THE PLOTS FROM THE MEASUREMENTS RETRIEVING THEM FROM THINGSPEAK, overall we exploit REST, by doing a GET requests and using
# matplotlib to show them through the telegrambot, sadly the dynamic plots from Thingspeak can't be retrieved but the data points.

# Important: to manage the chatbot, there's a 'temporary' configuration file which saves the information about the gardenID, chatID and 
# gardens that the owner own, THIS PART MOSTLY STRESSES ABOUT THE GARDENS, WHICH ARE ESSENTIALLY THE CENTRAL ACTORS OF THE PROJECT.


import matplotlib
matplotlib.use('Agg')
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import json
import requests
import paho.mqtt.client as mqtt
import os
import cherrypy
import matplotlib.pyplot as plt

class MQTT:
    def __init__(self, clientID, broker, port, notifier):
        self.broker = broker
        self.port = port
        self.notifier = notifier
        self.clientID = clientID
        self._topic = ""
        self._isSubscriber = False
        # create an instance of paho.mqtt.client
        self._paho_mqtt = mqtt.Client(clientID, True)
        # register the callback
        self._paho_mqtt.on_connect = self.on_connect
        self._paho_mqtt.on_message = self.on_message_received

    def on_connect(self, client, userdata, flags, rc):
        print("Connected to %s with result code: %d" % (self.broker, rc))

    def on_message_received(self, client, userdata, msg):
        self.message = json.loads(msg.payload)
        if self.notifier:
            self.notifier.notify(self.message)  # Pass the received message to a notifier function if provided

    # Add a method to set a notifier function
    def set_notifier(self, notifier):
        self.notifier = notifier

    def publish_message(self, topic, msg):
        self._paho_mqtt.publish(topic, json.dumps(msg), 2)
        

    def subscribe_topic(self, topic):
        self._paho_mqtt.subscribe(topic, 2)
        self._isSubscriber = True
        self._topic = topic
        print("Subscribed to %s" % topic)

    def start_connection(self):
        self._paho_mqtt.connect(self.broker, self.port)
        self._paho_mqtt.loop_start()

    def unsubscribe_topic(self):
        if self._isSubscriber:
            self._paho_mqtt.unsubscribe(self._topic)

    def stop_connection(self):
        self.unsubscribe_topic()  
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()


class chatDataExposer:
    exposed = True
    def __init__(self):
        self.data_file = "chatConfig.json"
        self.load_data()
   
    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as file:
                self.data = json.load(file)

    def GET(self,*uri):
        if len(uri) == 1 and str(uri[0]).lower() == "getchatdata":
            return json.dumps(self.data)
        else:
            return "Invalid URL"

class channelIDandAPIKeys:
    exposed = True
    def __init__(self):
        self.data_file = "channelIDreadAPIKey.json"
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as file:
                self.data = json.load(file)

    def save_data(self):
        data = self.data
        with open(self.data_file, "w") as file:
            json.dump(data, file)

    def GET(self,*uri):
        if len(uri) == 1 and str(uri[0]).lower() == "getchannalsandreadapis":
            return json.dumps(self.data)
        else:
            return "Invalid URL"
    
    # The format is localhost:8085/channels/registerchannelandapi/gardenID/channelID/readapikey
    def POST(self,*uri):
        if len(uri) == 4 and str(uri[0]).lower() == "registerchannelandapi":
            gardenID = uri[1]
            channelID = uri[2]
            readAPIkey = uri[3]
            channel = "channel_{}".format(gardenID)
            apikey = "readkey_{}".format(gardenID)
            self.data[channel] = channelID
            self.data[apikey] = readAPIkey
            self.save_data()
            return "Channel ID and read API key saved successfully."


class chatBot:
    exposed = True

    def __init__(self):
        # Okay, the token from the telegrambot should be first: at the SR catalog, and then we will do a GET request
        # to the catalog in order to retrieve it, the endpoints and similar info are at the configuration file:
        with open('configFile.json', 'r') as config_file:
            self.config = json.load(config_file)
        #getToken = self.config["endpoints"]["getchatbotToken"]
        #response = requests.get(getToken)
        broker = self.config["endpoints"]["MQTTbroker"]
        port = self.config["endpoints"]["port"]
        #self.token = response.text.strip()
        self.bot = telepot.Bot("7063657147:AAFWqTBUlui9mx6NwJqpDy7YcMA1d-tE7x8")
        self.chat_states = {}
        self.loged = False
        self.userID = None
        #self.chatIDs=[]
        self.__message={"alert":"","action":""}
        self.mqtt_client = MQTT("client1", broker, port, notifier=None)
        self.mqtt_client.start_connection()
        MessageLoop(self.bot, {'chat': self.on_chat_message}).run_as_thread()
        self.data_file = "chatConfig.json"
        self.load_data()
   
    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as file:
                data = json.load(file)
                self.chatID = data["chatID"]
                self.gardenID = data["gardenID"]
                self.gardensOwner = data["gardensOwner"]
    
    def save_data(self):
        data = {"chatID": self.chatID, "gardenID": self.gardenID, "gardensOwner": self.gardensOwner}
        with open(self.data_file, "w") as file:
            json.dump(data, file)
    
    def on_chat_message(self, msg):
        content_type, chat_type, chat_ID = telepot.glance(msg)
        message = msg['text'].lower()

        self.load_data()
        self.chatID = chat_ID
        self.save_data()

        if message == "/start":
            self.bot.sendMessage(chat_ID, text="Welcome to the GreenTech Hub bot, in order to operate kindly proceed with: /login")

        elif message == "/login":
            self.bot.sendMessage(chat_ID, text= "Please write your username and password comma separated, example: username,password")
            self.chat_states[chat_ID] = "/login"

        elif message == "/showmygardens":
            if self.loged == True:
                userGardens = []
                self.gardensOwner = []
                gardensURL = self.config["endpoints"]["getGardens"]
                gardensResponse = requests.get(gardensURL)
                gardens = gardensResponse.json()
                self.load_data()
                
                for garden in gardens:
                    if garden["gardenOwnerUserID"] == self.userID:
                        userGardens.append(garden)
                        self.gardensOwner.append(garden["gardenID"])
                self.save_data()
                if userGardens:
                    self.bot.sendMessage(chat_ID, text = "Gardens you own: ")
                    for garden in userGardens:
                        garden_info = json.dumps(garden, indent=4) 
                        self.bot.sendMessage(chat_ID, text=garden_info)
                else:
                    self.bot.sendMessage(chat_ID,text = "You don't own any garden!")
            else:
                self.bot.sendMessage(chat_ID, text = "A user must be logged-in first!")

        elif message.startswith("/last "):
            if self.loged == True:
                try:
                    garden_id = int(message.split(" ")[1])
                    self.bot.sendMessage(chat_ID, text="Retrieving last available measurements for garden ID: {garden_id}")
                    self.load_data()
                    self.gardenID = garden_id
                    self.save_data()
                    topic = "IoTProject/"+str(garden_id)+"/calculation"
                    message = {
                                "userID": self.userID,
                                "garden": garden_id,
                                "state": "current"
                            }
                    
                    self.mqtt_client.publish_message(topic, message)
                    self.bot.sendMessage(chat_ID,text= "Message sent:")
                    prettyMessage = json.dumps(message)
                    self.bot.sendMessage(chat_ID, text = prettyMessage)
                    self.bot.sendMessage(chat_ID,text = "Sent to the topic:")
                    self.bot.sendMessage(chat_ID,text=topic)
                    resultTopic = "IoTProject/"+str(garden_id)+"/calculationresult"
                    self.mqtt_client.subscribe_topic(resultTopic)
                

                except:
                    self.bot.sendMessage(chat_ID, text="Invalid format. Please use /last followed by a garden ID.")
            else:
                self.bot.sendMessage(chat_ID, text = "A user must be logged-in first!")
 
        elif message.startswith("/hourly "):
            if self.loged == True:
                try:
                    garden_id = int(message.split(" ")[1])
                    self.bot.sendMessage(chat_ID, text="Retrieving hourly average measurements for garden ID: {garden_id}")
                    self.load_data()
                    self.gardenID = garden_id
                    self.save_data()
                    topic = "IoTProject/"+str(garden_id)+"/calculation"
                    message = {
                                "userID": self.userID,
                                "garden": garden_id,
                                "state": "hourly"
                            }
                    
                    self.mqtt_client.publish_message(topic, message)
                    self.bot.sendMessage(chat_ID,text= "Message sent:")
                    prettyMessage = json.dumps(message)
                    self.bot.sendMessage(chat_ID, text = prettyMessage)
                    self.bot.sendMessage(chat_ID,text = "Sent to the topic:")
                    self.bot.sendMessage(chat_ID,text=topic)
                    resultTopic = "IoTProject/"+str(garden_id)+"/calculationresult"
                    self.mqtt_client.subscribe_topic(resultTopic)
                except:
                    self.bot.sendMessage(chat_ID, text="Invalid format. Please use /last followed by a garden ID.")
            else:
                self.bot.sendMessage(chat_ID, text = "A user must be logged-in first!")
        
        elif message.startswith("/daily "):
            if self.loged == True:
                try:
                    garden_id = int(message.split(" ")[1])
                    self.bot.sendMessage(chat_ID, text="Retrieving daily average measurements for garden ID: {garden_id}")
                    self.load_data()
                    self.gardenID = garden_id
                    self.save_data()
                    topic = "IoTProject/"+str(garden_id)+"/calculation"
                    message = {
                                "userID": self.userID,
                                "garden": garden_id,
                                "state": "daily"
                            }
                    
                    self.mqtt_client.publish_message(topic, message)
                    self.bot.sendMessage(chat_ID,text= "Message sent:")
                    prettyMessage = json.dumps(message)
                    self.bot.sendMessage(chat_ID, text = prettyMessage)
                    self.bot.sendMessage(chat_ID,text = "Sent to the topic:")
                    self.bot.sendMessage(chat_ID,text=topic)
                    resultTopic = "IoTProject/"+str(garden_id)+"/calculationresult"
                    self.mqtt_client.subscribe_topic(resultTopic)
                except:
                    self.bot.sendMessage(chat_ID, text="Invalid format. Please use /last followed by a garden ID.")
            else:
                self.bot.sendMessage(chat_ID, text = "A user must be logged-in first!")


        elif message.startswith("/plots "):
            #Very important thing to mention: sadly it is not possible to dynamically retrieve the Thingspeak-generated plots
            #that we see at 'MyChannels' dashboard unless we use some MatLab tools, anyways in order to display plots it is possible
            #to do a GET request to read the conten of each field of the channel (e.g. the measurements from the sensors) and use
            #matplotlib to plot them and then send the pictures via Telegram, even though these plots are not as 'pretty' as the ones
            #they are still showing information. 
            if self.loged == True:
                try:
                    garden_id = int(message.split(" ")[1])
                    self.bot.sendMessage(chat_ID, text="Retrieving available plots for garden ID: {garden_id}")
                    self.gardenID = garden_id
                    self.save_data()

                    #Now we need to load the JSON configFile because we must retrieve keys, honestly I don't know whether that
                    #kind of information belongs either to a configuration file or a catalog, but considering a catalog is supposed
                    #to be mostly about the discovery of services and devices I am leaning towards including API keys to the configuration file.
                    route = 'configFile.json'
                    with open(route, 'r') as config_file:
                        config = json.load(config_file)
                    route2 = "channelIDreadAPIKey.json"
                    with open(route2, "r") as config_file:
                        config2 = json.load(config_file)
                    
                    #First thing to do: look for the channel ID channel_IDX which belongs to the user query and also construct the URL:
                    channelID = "channel_"+str(self.gardenID)
                    apiKeyName = "readkey_"+str(self.gardenID)
                    print(channelID)
                    print(apiKeyName)
                    if channelID in config2:
                        channelIDValue = config2[channelID]
                        baseURL = config["base_url"].format(channel_id=channelIDValue)
                    
                    if apiKeyName in config2:
                        apiKeyValue = config2[apiKeyName]
                        url = config["URL"].format(base_url = baseURL, api_key = apiKeyValue)
                    
                    #Now let's do the a GET request to the URL in order to retrieve the data points
                    response = requests.get(url)
                    if response.status_code == 200:
                        #self.bot.sendMessage(self.chatID, text= "holaa gato")
                        data = response.json()
                        #Navigating thourgh the data obtained from the get request to the thingspeak channel we can set the information   
                        temperatureMeasurements = []
                        temperatureTimestamps = []
                        humidityMeasurements = []
                        humidityTimestamps = []
                        phMeasurements = []
                        phTimestamps = []
                        lightMeasurements = []
                        lightTimestamps = []
                        for entry in data["feeds"]:
                            if isinstance(entry["field1"], str):
                                temperatureMeasurements.append(float(entry["field1"]))
                                temperatureTimestamps.append(entry["created_at"])
                            if isinstance(entry["field2"], str):
                                humidityMeasurements.append(float(entry["field2"]))
                                humidityTimestamps.append(entry["created_at"])
                            if isinstance(entry["field3"], str):
                                phMeasurements.append(float(entry["field3"]))
                                phTimestamps.append(entry["created_at"])
                            if isinstance(entry["field4"], str):
                                lightMeasurements.append(float(entry["field4"]))
                                lightTimestamps.append(entry["created_at"])

                        # This little function plots the figures
                        def create_plot(measurements, timestamps, ylabel):
                            try:
                                if measurements:
                                    plt.figure(figsize=(8, 6))
                                    plt.plot(timestamps, measurements, marker="o", linestyle="-")
                                    plt.xlabel("Time")
                                    plt.ylabel(ylabel)
                                    plt.title(ylabel)
                                    
                                    plt.xticks([timestamps[-1]], [timestamps[-1]])
                                    image_path = "plot.png"
                                    plt.savefig(image_path)
                                    plt.close()

                                    with open(image_path, "rb") as file:
                                        self.bot.sendPhoto(self.chatID, file)
                            except Exception as e:
                                print("Error:", e)
                        
                        create_plot(temperatureMeasurements, temperatureTimestamps, "Temperature")
                        create_plot(humidityMeasurements, humidityTimestamps, "Humidity")
                        create_plot(phMeasurements, phTimestamps, "pH")
                        create_plot(lightMeasurements, lightTimestamps, "Light")
                    else:
                        self.bot.sendMessage(self.chatID,text="Could not send the request to Thingspeak!")
                except:
                    pass
                
        elif message.startswith("/externallights "):
            if self.loged == True:
                route = 'configFile.json'
                with open(route, 'r') as config_file:
                    config = json.load(config_file)
                garden_id = int(message.split(" ")[1])
                command = str(message.split(" ")[2]).lower()
                if command not in ["on","off"]:
                    self.bot.sendMessage(chat_ID, text="Invalid format. Please command must be either on/off")
                else:
                    # To do this, we need a PUT request
                        body = {"gardenID": garden_id,
                                "externalLights": command}
                        updateGardenURL = config["endpoints"]["updateGarden"]
                        putRequest = requests.put(updateGardenURL,json=body)
                        if putRequest.status_code == 200:
                            self.bot.sendMessage(chat_ID, text=f"External lights for garden {garden_id} turned {command}.")
                        else:
                            self.bot.sendMessage(chat_ID, text=f"Failed to update external lights for garden {garden_id}. Check if you own that garden!")
                    

                    
                

        elif chat_ID in self.chat_states and self.chat_states[chat_ID] == "/login":
            if ',' not in message:
                self.bot.sendMessage(chat_ID, text="Invalid format. Please enter username and password separated by a comma.")
                return
            username, password = message.split(",", 1)
            # At this point let's do a get request to the SRcatalog in order to check whether that's a valid user or not
            usersURL = self.config["endpoints"]["getUsers"]
            usersResponse = requests.get(usersURL)
            users = usersResponse.json()
            for user in users:
                if user["username"].lower() == username.lower() and user["password"] == password:
                    self.userID = user["userID"]
                    self.bot.sendMessage(chat_ID, text= "Logged-in successfully.")
                    self.bot.sendMessage(chat_ID, text="Now you can do the following:\n"
                                    "- View gardens associated to you: </showmygardens>\n"
                                    "- Request last available measurements of a garden: </last gardenID>\n"
                                    "- Request daily average: </daily gardenID>\n"
                                    "- Request hourly average: </hourly gardenID>\n"
                                    "- Control external lights: </externallights gardenID on/off>\n"
                                    "- Request plot of a measure: </plots gardenID>")
                    self.loged = True
                    break
            if not self.loged:
                self.bot.sendMessage(chat_ID, text= "Error, user-password mismatching.")
            else:
                del self.chat_states[chat_ID] 

   


if __name__ == "__main__":
    # Create an instance of the bot
    bot = chatBot()
    conf = {
        "/": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher(),
            "tools.sessions.on": True,
        }
    }
    with open("configFile.json", "r") as config_file:
                config = json.load(config_file)
    url = config["endpoints"]["registerService"]
    body = {"name": "telegrambot",
            "endpoint": "http://telegrambot:8085/"}
    response = requests.post(url, json=body)
    cherrypy.tree.mount(chatDataExposer(),"/", conf)
    cherrypy.tree.mount(channelIDandAPIKeys(),"/channels",conf)
    cherrypy.config.update({
        'server.socket_port': 8085,
        'server.socket_host': '0.0.0.0'  
    })
    cherrypy.engine.start()
    cherrypy.engine.block()
    cherrypy.engine.exit()
    while True:
        pass












