# Programming for IoT applications - Project
# Thingspeak adaptor.

# Insights: 
# Essentially the ThingSpeak adaptor is an independent software entity where:
# - We use the catalog data exposed by the SR catalog service via REST, to discover services and devices, in particular,
# for this part we need essentially all information stored in the catalog, users, gardens, devices, strategies and MQTT broker,
# because we need to do some association among actors in order to be sure about the data exchange. I achieve this using a 
# GET request.
# - We subscribe to the topics that are 'on' which means that there are sensors publishing their measures via MQTT, with the information
# retrieved from the catalog. Moreover, in this script I also develop a MQTT class in order to manage all related. But here the important is that:
# 1) WE SUBSCRIBE TO TOPICS OF DEVICES WHOSE STATUS ARE 'ON'
# 2) IF THEY ARE 'ON' IT MEANS THERE ARE ALREADY MESSAGES (MEASUREMENTS) BEING SENT FROM THE DEVICE CONNECTOR VIA THE MESSAGE BROKER
# 3) IN THE MQTT SCRIPT, THERE'S A METHOD THAT STORES ALL THE MESSAGES RECEIVED AND THEN CAN BE EXPOSED USING REST (this had to be developed
# debugging due to some troubles with MQTT)
# - We need to retrieve all that information, and then, store it and expose it via REST so that the strategies part
# are able to use them to calculate strategies.  http://localhost:8087/...
# 
# VERY IMPORTANT: 
# In the ThingSpeak adaptor script, we proceed with the creation of the ThingSpeak channels and fields. 
# So the procedure is, at the configuration File register the APIKEYS, sadly they can't be retrieved dynamically using Python, only possible using
# some MathWorks add-on (afaik), so the following things: writeAPIKEY, channelID, readkey, must be retrieved manually.
# Also, talking about limitations: the maximum amount of channels Thingspeak allows in free-mode are 4, so at most, this project works fine with 4 gardens
# but this could be solved buying the license.

import json
import os
import cherrypy
import threading
import time
import string
import random
import requests
import paho.mqtt.client as mqtt


class thingspeakKeys(object):
    exposed = True

    def __init__(self):
        self.users = []
        self.data_file = "apiKeys.json"
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
        if len(uri)==1 and uri[0] == "showkeys":
            return json.dumps(self.data)
        
    def POST(self, *uri):
        if len(uri) != 0:
            if str(uri[0]).lower() == "registerapikey":
                gardenID = uri[1]
                key = uri[2]
                keyIndex = "garden{}WriteAPIKEY".format(gardenID)
                self.data[keyIndex] = key
                self.save_data()
                return "The write API key has been registered successfully."


class MessageStore:
    def __init__(self):
        self.received_messages = []  # Shared list to store received messages

    def add_message(self, message):
        self.received_messages.append(message)

    def get_messages(self):
        return self.received_messages

class MQTT:
    message_store = MessageStore()  # Shared message store among all MQTT clients

    def __init__(self, clientID, broker, port, notifier):
        self.broker = broker
        self.port = port
        self.notifier = notifier
        self.clientID = clientID
        self._topic = ""
        self._isSubscriber = False
        self._paho_mqtt = mqtt.Client(clientID, True)
        self._paho_mqtt.on_connect = self.on_connect
        self._paho_mqtt.on_message = self.on_message_received

    def on_connect(self, client, userdata, flags, rc):
        print("Connected to %s with result code: %d" % (self.broker, rc))

    def on_message_received(self, client, userdata, msg):
        message = json.loads(msg.payload)  
        self.message_store.add_message(message)  # Add message to the shared store

        value = message["v"]
        gardenID = message["gardenID"]
        measureType = str(message["n"]).lower()

        with open("apiKeys.json", "r") as config_file:
                config = json.load(config_file)

        garden_key = f"garden{gardenID}WriteAPIKEY"
        write_api_key = config[garden_key]
        if measureType == "temperature":
            api_url = f'https://api.thingspeak.com/update?api_key={write_api_key}&field{1}={value}'
        if measureType == "humidity":
            api_url = f'https://api.thingspeak.com/update?api_key={write_api_key}&field{2}={value}'
        if measureType == "ph":
            api_url = f'https://api.thingspeak.com/update?api_key={write_api_key}&field{3}={value}'
        if measureType == "light":
            api_url = f'https://api.thingspeak.com/update?api_key={write_api_key}&field{4}={value}'
        
        response = requests.get(api_url)
        if response.status_code == 200:
            print('Data sent successfully to ThingSpeak.')
        else:
            print('Failed to send data to ThingSpeak.')



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



# Let's create this class to perform GET request to SRcatalog web service
class dataRetrieval(object):

    # First thing we need to do is to do a GET request to the SRcatalog so we get all information required.
    # We know it is exposed at http://localhost:8089/
    # Actually we probably will need information from almost each section of the catalog (e.g. user,garden,device)
    # so it's better to get all of it: http://localhost:8089/catalog/printall, this is a GET request

    def responses(self):
        with open("configFile.json") as config_file:
            config = json.load(config_file)
        getCatalog = config["endpoints"]["getCatalog"]


        try:
            catalogResponse = requests.get(getCatalog)
            if catalogResponse.status_code == 200:
                self.catalog = catalogResponse.json()  
            else:
                print("Failed to retrieve catalog data. Status code:", catalogResponse.status_code)
                return None
        except requests.RequestException as e:
                print("Error retrieving devices data:", e)
                return None
    
        return self.catalog
    

# Okay, now in this class what we do is, use the dataRetrieval class in order to do the GET request,
# and then surf over the devices section of the catalog and subscribe to the available topics.
# IMPORTANT: The topic creation is done using the gardens ID + measure type + device ID, it is impossible
# that a garden or device share ID, therefore it is totally impossible to have equal topics, so,
# for simplicity I will just subscribe to all the topics, and then, whenever the devices (sensors) are turned
# on at the device connector, we thingspeakadaptor is already subscribed so it's just a matter of waiting
# for the messages to be published.
# Also, I will put all the messages received (they are already in SenML) in a dictionary, then data processing
# will do the rest.
class topicSubscriber(object):

    def __init__(self):
        
        self.subscribed_devices = set()

    def generate_clientID(self):
        return ''.join(random.choices(string.ascii_letters, k=4))

    def subscriber(self):
        while True:  # Infinite loop to keep script alive
            print("Searching for new devices to subscribe")
            data = dataRetrieval()
            self.catalog = data.responses()
            mqtt_broker = self.catalog.get("MQTTbroker")
            mqtt_port = self.catalog.get("port")
            devices = self.catalog.get("devices",[])
            for device in devices:
                device_id = device["deviceID"]
                if device_id not in self.subscribed_devices:
                    self.client = MQTT(self.generate_clientID(), mqtt_broker, mqtt_port, None)
                    self.client.start_connection()
                    self.client.subscribe_topic(device["MQTTtopics"][0])
                    self.subscribed_devices.add(device_id)  # Add device ID to the set of subscribed devices
            
            # Sleep for a while to avoid excessive looping
            time.sleep(15)  # Sleep for 60 seconds before re-subscribing


# Okay, this class is important and needs to be created because it will expose the messages received at the topics
# those messages, as stated above are the measurements from the devices, they need to be exposed so that the data
# analytics and statistics part will eventually use a GET request to have access to them and do whatever calculation
# they may need.
class messageExposer(object):
    exposed = True

    def GET(self, *uri):
        if len(uri) != 0:
            if len(uri) == 1:
                if uri[0].lower() == "getmessages":
                    messages = MQTT.message_store.get_messages()
                    return json.dumps(messages)
            else:
                return "URI length is wrong."
        else:
            return "The URI is empty."   
    
# Now here we will start doing the ThingSpeak creation, in particular, we will use
# A CHANNEL PER EACH GARDEN, in particular before I thought of doing all gardens of user in a channel but 
# that is a mess and in terms of scalability is not possible since there is a limit of fields in a channel
# of course there is also a limit of fields per channel but a garden has a least 4 measurements, e.g, 4 fields
# the free account limits the number of channels (gardens) but it's scalable in the sense that it just needs
# a paid subscription



# VERY IMPORTANT, SEEMS LIKE THERE IS not a dynamic way to retrieve the WRITE API KEY,
# so the procedure will be to copy the WRITE API KEY and update the configuration file.
class thingSpeakChannelCreation(object):
    def __init__(self):
        # Load configuration from file
        with open("configFile.json") as config_file:
            config = json.load(config_file)
        self.getAPIkey = config["thingspeakUserAPIKEY"]
        self.thingSpeakCreateChannel = config["endpoints"]["createChannelThingsspeak"]
        self.channels_created = set()  # Use a set to keep track of created channels
    

    def creation(self):
        # So, we know each garden may have at most 4 channels, they are fixed so basically if a garden does not measures
        # ph, it will just be empty because someday it may have it, so let's just simplify work.
        while True:
            # First let's use the dataRetrieval class to get the catalog and therefore we can extract the gardens
            data = dataRetrieval()
            self.catalog = data.responses()
            gardens = self.catalog.get("gardens",[])
            
            for garden in gardens:
                if garden["gardenID"] not in self.channels_created:
                    channel_details = {
                    "api_key": self.getAPIkey,
                    "name": "gardenID-"+str(garden["gardenID"]),
                    "description": "Garden Name: "+str(garden["gardenName"]+"     Ecosystem type: "+str(garden["ecosystemType"])),
                    "field1": "temperature",
                    "field2": "humidity",
                    "field3": "ph",
                    "field4": "light"}

                    response = requests.post(self.thingSpeakCreateChannel, json=channel_details)
                    if response.status_code == 200:
                        self.channels_created.add(garden["gardenID"])
                        print("Channel created successfully.")
                    else:
                        print("Failed to create channel. Status code:", response.status_code)
                        print(response.text)
            time.sleep(5)
            



if __name__ == "__main__":
   

    conf = {
        "/": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher(),
            "tools.sessions.on": True,
        }
    }
    subscriber = topicSubscriber()
    subscriber_thread = threading.Thread(target=subscriber.subscriber)
    subscriber_thread.daemon = True
    subscriber_thread.start()
    thingSpeakChannels = thingSpeakChannelCreation()
    thingSpeakThread = threading.Thread(target=thingSpeakChannels.creation)
    thingSpeakThread.daemon = True
    thingSpeakThread.start()
    web_service = messageExposer()
    web_service2 = thingspeakKeys()
    with open("configFile.json", "r") as config_file:
                config = json.load(config_file)
    url = config["endpoints"]["registerService"]
    body = {"name": "thingspeakadaptor",
            "endpoint": "http://thingspeakadaptor:8087/"}
    response = requests.post(url, json=body)
    cherrypy.tree.mount(web_service,"/messages", conf)
    cherrypy.tree.mount(web_service2,"/keys",conf)
    cherrypy.config.update({
        'server.socket_port': 8087,
        'server.socket_host': '0.0.0.0'  # Listen on all interfaces
    })
    cherrypy.engine.start()
    cherrypy.engine.block()
    cherrypy.engine.exit()



