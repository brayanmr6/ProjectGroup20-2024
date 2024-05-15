#  Programming for IoT applications - Project
# Data analytics.

# So, this script has the following tasks:
# - Retrieve information performing GET requests from the resource catalog to associate information and calculation
# - Perform calculations and statistics of: a garden/ a measure in a garden/ etc, TBD (this is free choice in proposal)
# - Publish/Subscribe to the topics of this calculations/statistics since the user via Telegram BOT will request them,
# this of course employs MQTT.


# A clarification going here:
# - The project DOES have and implements control strategies, but they are TURNED ON/OFF
# - at the device connector, because in the project proposal revised version we had to state them where they were
# - so, in particular the path that goes to a strategy registration to its implementation goes like this:
# Strategy register at SR catalog ---(EXPOSED WITH REST)---- > Device connector turns it on/off ----> (SENSOR MEASURE
# MENTS MINDING AND UNDER SENSOR ACTIVATION IF STRATEGY ON SENT VIA MQTT) ---- > Thingspeak Adaptor (where measurements are
# received) 


from itertools import groupby
from datetime import datetime, timedelta
import time
import string
import random
import json
import requests
import paho.mqtt.client as mqtt


# This class is very important and used only for retrieve the data about the catalog and messages doing a GET request
# to their respective webservice, we are using the configFile.json at the root folder
class dataRetrieval(object):
    def responses(self):
        with open("configFile.json") as config_file:
            config = json.load(config_file)

        getCatalog = config["endpoints"]["getCatalog"]
        getMessages = config["endpoints"]["getMessages"]

        try:
            catalogResponse = requests.get(getCatalog)
            if catalogResponse.status_code == 200:
                catalog = catalogResponse.json()  
            else:
                print("Failed to retrieve catalog data. Status code:", catalogResponse.status_code)
                return None
        except requests.RequestException as e:
                print("Error retrieving devices data:", e)
                return None
        
        try:
            messagesResponse = requests.get(getMessages)
            if messagesResponse.status_code == 200:
                messages = messagesResponse.json()  
            else:
                print("Failed to retrieve messages data. Status code:", messagesResponse.status_code)
                return None
        except requests.RequestException as e:
                print("Error retrieving messages data:", e)
                return None
    
        return {
            "catalog": catalog,
            "messages": messages
        }

class MQTT:
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
        self.message = json.loads(msg.payload)
        result = calculationWebService(self.message).calculation()
        #print(json.dumps(result))

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

# Ok, this is the first important class, and probably the only one, here, we need to do the following:
# - Subscribe to a MQTT topic, as of now, I'm thinking to subscribe to a generic topic like:
# IoTProject/ask/calculation
# - According to the message sent by the telegram bot, we will sent back some statistic, there are few of them
# actually there can be a lot of statistics, but as up now, the most suitable ones are:
"""1) Ask for the state of the garden: i.e. retrieve all last avaiable measurements
   2) Ask for the state of a specific measure of a garden: i.e. retrieve last temperature
   3) Ask for the states of all gardens of a single user
   4) Ask for the daily average (last day) state of a garden (all available measures)
   5) Ask for the daily average (last day) state of a measure of a garden
   6) Same same goes for hourly"""

class calculationWebService(object):
    """message:
    userID: uniqueID
    garden: []  Actually garden should be only one, giving more than one garden is a total mess.
    measurement: []
    state: current/hourly/daily
    """
    def __init__(self,message):
        self.message = message

    def calculation(self):
        self.userID = self.message["userID"]
        self.garden = self.message["garden"]
        # self.measureTypes = self.message["measurements"]
        self.state = self.message["state"]

        if str(self.state).lower() == "current":
            data = dataRetrieval()
            data2 = data.responses()
            measurements = data2.get("messages")
            catalog = data2.get("catalog")
            # Let's filter the measurements, first the gardens:
            firstFilter = [measure for measure in measurements if measure["gardenID"] == self.garden]
            """ # Second filter, measureTypes
            secondFilter = [measure for measure in firstFilter if measure["n"] in self.measureTypes] """
            # Group measurements by measure type
            grouped_measurements = {key: list(group) for key, group in groupby(firstFilter, key=lambda x: x["n"])}
            # Get the last entry for each measure type
            final_measurements = {measure_type: max(measures, key=lambda x: x["t"]) for measure_type, measures in grouped_measurements.items()}
        
            mqtt_client = MQTT("calculation_publisher", "mqtt.eclipseprojects.io", 1883, None)
            mqtt_client.start_connection()
            mqtt_client.publish_message("IoTProject/" + str(self.garden) + "/calculationresult", final_measurements)
            mqtt_client.stop_connection()

        elif str(self.state).lower() == "hourly":
            data = dataRetrieval()
            data2 = data.responses()
            measurements = data2.get("messages")
            catalog = data2.get("catalog")
            
            # Filter #1, select only messages correspondant to the gardenID:
            firstFilter = [measure for measure in measurements if measure["gardenID"] == self.garden]

            # Let's retrieve the available measurement types (ph,temperature,light,humidity):
            # a.k.a they appear at least one in the messages associated with that garden
            availableMeasurementType = []
            for measurement in firstFilter:
                if measurement["n"] not in availableMeasurementType:
                    availableMeasurementType.append(measurement["n"])

            # Now let's set the time window from one hour.
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=60)
            end_timestamp = int(end_time.timestamp())
            start_timestamp = int(start_time.timestamp())

            # Filter #2, keep measurements from the firstFilter that are within the timewindow
            secondFilter = [measure for measure in firstFilter if measure["t"] > start_timestamp and measure["t"] < end_timestamp]

            # Calculate the average value result for each measurement type:
            results = {}
            for measurementType in availableMeasurementType:
                measurementTypeCounts = 0
                measurementTypeAccumulator = 0
                for measure in secondFilter:
                    if measure["n"] == measurementType:
                        measurementTypeCounts += 1
                        measurementTypeAccumulator += measure["v"]
                if measurementTypeCounts > 0:
                    average_value = measurementTypeAccumulator / measurementTypeCounts
                    results[measurementType] = average_value

            mqtt_client = MQTT("calculation_publisher", "mqtt.eclipseprojects.io", 1883, None)
            mqtt_client.start_connection()
            mqtt_client.publish_message("IoTProject/" + str(self.garden) + "/calculationresult", results)
            mqtt_client.stop_connection()

        
        elif str(self.state).lower() == "daily":
            data = dataRetrieval()
            data2 = data.responses()
            measurements = data2.get("messages")
            catalog = data2.get("catalog")
            
            # Filter #1, select only messages correspondant to the gardenID:
            firstFilter = [measure for measure in measurements if measure["gardenID"] == self.garden]

            # Let's retrieve the available measurement types (ph,temperature,light,humidity):
            # a.k.a they appear at least one in the messages associated with that garden
            availableMeasurementType = []
            for measurement in firstFilter:
                if measurement["n"] not in availableMeasurementType:
                    availableMeasurementType.append(measurement["n"])

            # Now let's set the time window from one hour.
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=1440)
            end_timestamp = int(end_time.timestamp())
            start_timestamp = int(start_time.timestamp())

            # Filter #2, keep measurements from the firstFilter that are within the timewindow
            secondFilter = [measure for measure in firstFilter if measure["t"] > start_timestamp and measure["t"] < end_timestamp]

            # Calculate the average value result for each measurement type:
            results = {}
            for measurementType in availableMeasurementType:
                measurementTypeCounts = 0
                measurementTypeAccumulator = 0
                for measure in secondFilter:
                    if measure["n"] == measurementType:
                        measurementTypeCounts += 1
                        measurementTypeAccumulator += measure["v"]
                if measurementTypeCounts > 0:
                    average_value = measurementTypeAccumulator / measurementTypeCounts
                    results[measurementType] = average_value

            mqtt_client = MQTT("calculation_publisher", "mqtt.eclipseprojects.io", 1883, None)
            mqtt_client.start_connection()
            mqtt_client.publish_message("IoTProject/" + str(self.garden) + "/calculationresult", results)
            mqtt_client.stop_connection()
                  

# Finally this class is employed only to subscribe to all possible calculations, they depend on the user ID
# so that's why we need to do the GET requests.
class topicSubscriber(object):
    
    def __init__(self):
        self.subscribed_users = set()

    def generate_clientID(self):
        return ''.join(random.choices(string.ascii_letters, k=4))

    def subscriber(self):
        while True:  # Infinite loop to keep script alive
            print("Searching for new users to subscribe")
            data = dataRetrieval()
            self.catalogAndMessages = data.responses()
            mqtt_broker = self.catalogAndMessages.get("catalog").get("MQTTbroker")
            mqtt_port = self.catalogAndMessages.get("catalog").get("port")
            users = self.catalogAndMessages.get("catalog").get("users",[])
            for user in users:
                user_id = user["userID"]
                if user_id not in self.subscribed_users:
                    self.client = MQTT(self.generate_clientID(), mqtt_broker, mqtt_port, None)
                    self.client.start_connection()
                    self.client.subscribe_topic("IoTProject/"+str(user["userID"])+"/calculation")
                    self.subscribed_users.add(user_id) 
            time.sleep(15)

if __name__ == "__main__":
    
    time.sleep(30)
    with open("configFile.json", "r") as config_file:
                config = json.load(config_file)
    url = config["endpoints"]["registerService"]
    body = {"name": "dataAnalytics",
            "endpoint": "http://dataanalytics:8086/"}
    response = requests.post(url, json=body)
    
    subscriber = topicSubscriber()
    subscriber.subscriber()