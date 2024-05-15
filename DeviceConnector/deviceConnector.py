# Programming for IoT applications - Project
# Device Connector.

# Some insights: Essentially the device connector is an independent software entity where:
# - The MAIN AND MOST IMPORTANT THING THE DEVICE CONNECTOR DOES IS TO CONTROL THE DEVICES (SENSORS) of the project, in particular,
# the device connector here tries to emulate a real-world microcontroller, in particular, the device connector first does GET request
# to the catalog webservice in order to retrieve the information about the gardens, devices and MQTT data. This has to be done because
# we need to associate the device (tells the measure type) with the garden (tells the ecosystem type) in order to proceed with realistic
# simulation of the sensors.
# - On the other hand, it handles the message publication via MQTT, each device has a particular MQTT topic to publish based on the measurement type
# and device ID (unique), this script takes care of the message publication, i.e. it simulates the sending of the measurements of the sensors
# to the message broker.
# - ALSO, ANOTHER VERY IMPORTANT POINT HERE IS THE FOLLOWING: In this script, the control strategies are also activated/deactivated
# in the proposal we wrote that the device connector is the point where the 'actuators' are located, essentially the control strategies are taken
# as the actuators and according to the user's preferences (they register the strategies at the catalog webservice). The script
# requests via a GET the information of the strategies to the catalog, and based on that, it eithers brings the value of the measurement down or
# up as the simulation running time keeps going on. Also, it sends an alarm via MQTT to the Telegram Chatbot IF AND ONLY IF, the user who owns the
# garden is already logged in.

#Important: both the turning on/off of the sensors and strategies are handled as PUT methods, at http:localhost:8088/status/.... and just after that
#the publishing of messages via MQTT and the control provided by the strategies are considered!
#after that there's another PUT sent to the SRcatalog script but just to keep it updated.

import json
import time
import queue
import os
import cherrypy
import random
import requests
import threading
import string
import paho.mqtt.client as mqtt

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
        self.notifier.notify(msg.topic, msg.payload)

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

class dataRetrieval(object):
    def __init__(self):
        pass
    
    def responses(self):
        with open("configFile.json") as config_file:
            config = json.load(config_file)
        
        getDevices = config["endpoints"]["getDevices"]
        getGardens = config["endpoints"]["getGardens"]
        getMQTT = config["endpoints"]["getMQTTdata"]

        try:
            devicesResponse = requests.get(getDevices)
            if devicesResponse.status_code == 200:
                devices = devicesResponse.json()  
            else:
                print("Failed to retrieve devices data. Status code:", devicesResponse.status_code)
                return None
        except requests.RequestException as e:
            print("Error retrieving devices data:", e)
            return None
        
        try:
            gardensResponse = requests.get(getGardens)
            if gardensResponse.status_code == 200:
                gardens = gardensResponse.json()  
            else:
                print("Failed to retrieve gardens data. Status code:", gardensResponse.status_code)
                return None
        except requests.RequestException as e:
            print("Error retrieving gardens data:", e)
            return None
        
        try:
            MQTTresponse = requests.get(getMQTT)
            if MQTTresponse.status_code == 200:
                MQTTdata = MQTTresponse.json()  
            else:
                print("Failed to retrieve MQTT data. Status code:", MQTTresponse.status_code)
                return None
        except requests.RequestException as e:
            print("Error retrieving MQTT data:", e)
            return None
            
        if devices and gardens:
            for device in devices:
                for garden in gardens:
                    if device["gardenID"] == garden["gardenID"]:
                        device["ecosystemType"] = garden["ecosystemType"]
        
        self.data = {"MQTTdata": MQTTdata, "devices": devices}
        
        with open("devices.json", "w") as json_file:
            json.dump(self.data, json_file)
        
        return self.data
        

class sensorStatus(object):
    exposed = True

    def __init__(self):
        data = dataRetrieval()
        data.responses()
        self.devices = []
        self.mqttdata = []
        self.data_file = "devices.json"
        self.active_sensors = {}
        self.load_data()
        self.status = None
        self.deviceID = None
        self.message_queue = queue.Queue()
        self.publisher_thread = threading.Thread(target=self.publish_messages)
        self.publisher_thread.daemon = True
        self.publisher_thread.start()
        with open("configFile.json") as config_file:
            self.config = json.load(config_file)

    def publish_messages(self):
        while True:
            try:
                message = self.message_queue.get()
                if message:
                    self.publish_message(message)
            except Exception as e:
                print("Error publishing message:", e)

    def publish_message(self, message):
        deviceID, sensorInstance = message
        sensorInstance.getTemperature()

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as file:
                data = json.load(file)
                self.devices = data.get("devices",[])
                self.mqttdata = data.get("MQTTdata",[])

    def generate_clientID(self):
        return ''.join(random.choices(string.ascii_letters, k=4))

    def PUT(self, *uri):
        if len(uri) == 3:
            try:
                command = str(uri[0]).lower()
                self.deviceID = int(uri[1])
                self.status = str(uri[2]).lower()
                possibleStatus = ['on', 'off']
                possibleCommands = ["changestatus"]
        
                if self.status in possibleStatus and command in possibleCommands:
                    if self.status == "off":
                        body = {"status": "off"}
                    else:
                        body = {"status": "on"}

                    url = self.config["endpoints"]["updateDevice"]+str(self.deviceID)
                    response = requests.put(url, json=body)

                    if self.status == "on":
                        if self.deviceID not in self.active_sensors:
                            sensor_instance = temperatureSensor(self.get_device_info(self.deviceID),
                                                                self.mqttdata, 0.5, 0.5,
                                                                self.generate_clientID())
                            sensor_instance.startSim() 
                            self.active_sensors[self.deviceID] = sensor_instance
                            self.message_queue.put((self.deviceID, sensor_instance))
                    else:
                        if self.deviceID in self.active_sensors:
                            self.active_sensors[self.deviceID].stopSim() 
                            del self.active_sensors[self.deviceID]

            except Exception as e:
                print("Error:", e)
                return "There is something wrong with the URL."
            
        elif len(uri) == 4:
            try:
                command = str(uri[0]).lower()
                self.gardenID = int(uri[1])
                self.measure = str(uri[2]).lower()
                self.status = str(uri[3]).lower()
                possibleMeasures = ["temperature","humidity","ph","light"]
                possibleStatus = ['on', 'off']
                possibleCommands = ["setstrategy"]
                if self.status in possibleStatus and command=="setstrategy" and self.measure in possibleMeasures:
                        if self.status == "off":
                            body = {"status": "off"}
                        else:
                            body = {"status": "on"}
                        
                        url = self.config["endpoints"]["updateStrategy"]+str(self.gardenID)+"/"+str(self.measure)
                        print("Hola")
                        response = requests.put(url, json=body)
            except Exception as e:
                print("Error:", e)
                return "There is something wrong with the URL."
        else: 
            return "Incorrect URI length."

    def start_sensor_deployment(self):
        while True:
            self.sensorDeployment()
            time.sleep(13)  

    def sensorDeployment(self):
        for deviceID, sensorInstance in self.active_sensors.items():
            sensorInstance.getTemperature()

    def get_device_info(self, deviceID):
        for device in self.devices:
            if device["deviceID"] == deviceID:
                return device
        return None


class temperatureSensor(object):
    def __init__(self, deviceinfo, mqttinfo, fluctuation, noise_stddev, clientID):
        self.sensorID = deviceinfo["deviceID"]
        self.gardenID = deviceinfo["gardenID"]
        self.status = deviceinfo["status"]
        self.topic = deviceinfo["MQTTtopics"][0]
        self.unit = deviceinfo["unit"]
        self.ecosystemType = deviceinfo["ecosystemType"].lower()
        self.sensorType = deviceinfo["measureType"][0].lower()
        with open("configFile.json") as config_file:
            self.config = json.load(config_file)
        if self.sensorType == "temperature":
            if self.ecosystemType == "water":
                self.initial = 20  
                self.min = 15
                self.max = 30
            elif self.ecosystemType == "tropical":
                self.initial = 25
                self.min = 20
                self.max = 35
            elif self.ecosystemType == "dry":
                self.initial = 35
                self.min = 30
                self.max = 40
        elif self.sensorType == "humidity":
            if self.ecosystemType == "water":
                self.initial = 70
                self.min = 40
                self.max = 100
            elif self.ecosystemType == "tropical":
                self.initial = 60
                self.min = 40
                self.max = 90
            elif self.ecosystemType == "dry":
                self.initial = 30
                self.min = 15
                self.max = 50
        elif self.sensorType == "ph":
            if self.ecosystemType == "water":
                self.initial = 7
                self.min = 6.5
                self.max = 8.5
            elif self.ecosystemType == "tropical":
                self.initial = 7
                self.min = 6
                self.max = 8
            elif self.ecosystemType == "dry":
                self.initial = 7
                self.min = 6
                self.max = 8
        elif self.sensorType == "light":
            if self.ecosystemType == "water":
                self.initial = 80
                self.min = 50
                self.max = 120
            elif self.ecosystemType == "tropical":
                self.initial = 90
                self.min = 60
                self.max = 130
            elif self.ecosystemType == "dry":
                self.initial = 120
                self.min = 100
                self.max = 150
            

        self.fluctuation = fluctuation
        self.status = deviceinfo["status"].lower()
        self.noise_stddev = noise_stddev
        broker = self.config["MQTTbroker"]
        port = self.config["port"]
        self.client = MQTT(clientID, broker, port, None)

    def startSim(self):
        self.client.start_connection()

    def stopSim(self):
        self.client.stop_connection()

    def applyFluctuation(self):
        self.initial += random.uniform(-self.fluctuation, self.fluctuation)
        self.initial = max(self.min, min(self.initial, self.max))


    def addNoise(self):
        self.initial += random.gauss(0, self.noise_stddev)
        # NOW HERE WE WILL DO THE IMPLEMENTATION OF THE CONTROL, WHAT WE WILL DO IS THE FOLLOWING:
        # FIRST, DO A GET REQUEST TO THE WEB SERVICE THAT THE RESOURCE CATALOG EXPOSE, TO BE MORE
        # SPECIFIC, WE WILL DO A GET REQUEST TO THE STRATEGIES, /strategies/printallstrategies,
        # IF:
        # There is an active strategies for that very measurementType and garden, thus, status = on
        # we will do a script such doing a slow reduction/augmentation of the measurement value, until it 
        # goes back to the interval established in the strategy, if there are no strategies associated then
        # no control happens and essentially the measurement will fluctuate without any pattern in particular.
        print("self.ecosystemType:", self.ecosystemType)
        print("self.sensorType:", self.sensorType)
        with open("measurementAlertLevels.json", "r") as levelFile:
                alertLevels = json.load(levelFile)

        if self.initial > alertLevels[self.ecosystemType][self.sensorType]["high"] or self.initial < alertLevels[self.ecosystemType][self.sensorType]["low"]:
            
            topic = "IoTProject/"+str(self.gardenID)+"/alarm"
            message = "ALERT, THE MEASUREMENT "+str(self.sensorType)+"OF GARDEN "+str(self.gardenID)+" HAS FIRED AN ALARM, PLEASE SET or CREATE THE STRATEGY ON AT THE DEVICE CONNECTOR!"
            self.client.publish_message(topic,message)



        with open("configFile.json", "r") as config_file:
                config = json.load(config_file)
                
        url = config["endpoints"]["getStrategies"]
        response = requests.get(url)
        strategies = response.json()
        for strategy in strategies:
            if strategy["gardenID"] == self.gardenID and strategy["measureType"] == self.sensorType and strategy["status"] == "on":
                userMaxValue = strategy["maximumValue"]
                userMinValue = strategy["minimumValue"]
                if self.initial > userMaxValue:
                    self.initial = self.initial - 0.5                
                elif self.initial < userMinValue:
                    self.initial = self.initial + 0.5
                    
                


    def getTemperature(self):
        self.applyFluctuation()
        self.addNoise()
        timestamp = int(time.time())
        message = {
            "gardenID": self.gardenID,
            "sensorID": self.sensorID,
            "n": self.sensorType,
            "u": self.unit,
            "v": self.initial,
            "t": timestamp
        }
        topicToPublish = self.topic
        self.client.publish_message(topicToPublish, message)
        print(f"{topicToPublish} measured a {self.sensorType} of {self.initial} {self.unit} at the time {timestamp}")
        return self.initial

       
if __name__ == "__main__":
    conf = {
        "/": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher(),
            "tools.sessions.on": True,
        }
    }
    
    with open("configFile.json", "r") as config_file:
                config = json.load(config_file)
                
    url = config["endpoints"]["registerService"]
    body = {"name": "srcatalog",
            "endpoint": "http://srcatalog:8089/"}
    body2 = {"name": "deviceconnector",
            "endpoint": "http://deviceconnector:8088/"}
    response = requests.post(url, json=body)
    response2 = requests.post(url, json=body2)
    web_service = sensorStatus()

    deployment_thread = threading.Thread(target=web_service.start_sensor_deployment)
    deployment_thread.daemon = True
    deployment_thread.start()

    cherrypy.tree.mount(web_service, "/status", conf)
    cherrypy.config.update({
        'server.socket_port': 8088,
        'server.socket_host': '0.0.0.0'  # Listen on all interfaces
    })
    cherrypy.engine.start()
    cherrypy.engine.block()
