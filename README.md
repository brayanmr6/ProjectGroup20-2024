Greetings.
This is the final project for the course Programming for IoT Applications, developed by group #20.


**Summary:**

The project is titled 'GreenTech Hub' and its purpose relies on the caring of gardens, particularly those that you may have at your own home. The project allows a user to register their profile, the gardens they may own, and the devices that each of the gardens may have. In this project, we consider the existence of three kinds of gardens, let's call them 'ecosystem types', they are: dry, tropical and water. Each of them possesses different needs and characteristics. Each garden may have at most, one of these kinds of sensors: temperature, humidity, pH and light; once the sensors are turned on the measurement process starts. A user may have awareness of the state of their garden using either the Telegram chatbot or the web, however, the Telegram chatbot is more personal since it also receives alarms in case some measurement is over the recommended threshold for your garden type. To combat those undesirable measurements, it is also possible for the user to set strategies that will take care of the problematic measurements in your garden. 



**Detailed explanation of each component**:

Inside the scripts, there are also comments regarding some insights and tasks.

The precise endpoints are inside the configFile.json of each of the services.

* SRcatalog: The SR catalog is a software entity whose main task is to help register and discover devices and services. Essentially it exposes mostly all REST methods (GET, PUT, POST, DELETE) to all entities that may compose the catalog.json (which contains all the services and devices), to be more precise, it contains detailed information about the users, gardens, devices, strategies, MQTT broker, services endpoints and also the crucial key to make the Telegram chatbot work, the token. This catalog is **IS EXPOSED** as a web service and avails any other service to make any kind of REST requests to it (this is crucial for the project since the catalog.json stores the details of each 'entity'). Inside the container, it can be reached by other services at this address: HTTP://SRCATALOG:8089/....

* DeviceConnector: The device connector is a software entity in which we simulate a 'microcontroller' in the sense that in this script the sensors (devices) are controlled (turned ON/OFF), this is performed by a PUT request performed at HTTP://DEVICECONNECTOR:8088/..., this command also triggers another PUT request to the SRCATALOG web service, where the feature 'status' of the device is set to 'on' or 'off'. By default, all sensors are off, but whenever they are turned on, the script automatically starts to simulate measurements of the particular sensor turned on. The service whose task is to subscribe to these messages is the ThingspeakAdaptor, overall. Regarding the strategies, they are also turned on/off at the device connector, as well with a PUT request which will also trigger a PUT that updates the catalog.json, in particular, whenever a sensor is generating a measurement it will also consider a configuration file with some 'alert levels' and if meet, an alarm is sent via MQTT to the Telegram chatbot, on the other hand, regarding the control strategies, if they are on for that given sensor, it will either bring up or down the measurement value, and eventually will meet again 'normal values'.

* ThingspeakAdaptor: The Thingspeak adaptor is a service that first, aims to receive the measurements from the sensors generated at the deviceconnector, and this is done by exploiting MQTT by subscribing to the topics that the sensors that are 'on' may have, and in order to retrieve those topics, a GET request is performed to the catalog, since it stores the topics where the sensors publish the messages. Another key part of the ThingspeakAdaptor is that it exposes the measurements as a JSON file where all of them are stored once they are arrived, look at the MQTT class. This is done because different services need those values to operate, for example, the plotters and the data statistics. Important: since we want to send the data to Thingspeak as well, we need to input the write API key of each channel, let's remember that each garden generates a Thingspeak channel, but before starting a sensor is recommended to configure the channels properly, a POST request at this service allows to register the write API key for each channel.

* TelegramBot and TelegramBotResponder: The TelegramBot is one of the user awareness components, in particular, this webservice allows the user to perform different queries while using the GreenTech Hub bot at the Telegram App. A user must log-in first in order to proceed, and to verify that log-in, a GET request to the users to the SRcatalog webservice is performed, once validate there are different operations here, for example, show the gardens that a user may own (they may be several), also, a series of statistics like retrieving last data, hourly and daily average are available, these operations send MQTT messages to another webservice, the DataAnalytics one, which calculates the result and send it back to the TelegramBotResponder, who sends it back to the Telegram chat, to maintain consistency, the chat_ID retrieved by TelegramBot service is exposed via REST and the TelegramBotResponder retrieves it to send the message to the correct chat. The TelegramBot also subscribes to the MQTT alarm in case of abnormal measurements. The other two procedures possible are turning external lights on/off, by a PUT request to the catalog.json and also retrieve the plots, but before doing so, a POST request must register the Thingspeak Channel ID and read API key to the TelegramBot webservice, to recreate the plots we contact Thingspeak API and get the datapoints and plot them using matplotlib (not possible to retrieve the original ones I think).

* DataAnalytics: as stated before, its function is to subscribe to all possible calculation request topics that may surge and reply them back to the topics that the TelegramBotResponder subscribes to, due to confusion and lack of consistency in our opinion, also as stated in the proposal, the control strategies are created at the SRcatalog and activated at the deviceConnector.

* Webdashboard: is the other part of the user awareness part, it's a very basic local webpage based on HTML that does similar functionalities to the Telegram Chatbot, but in this case it does not listen to alarms, but it is based on REST methods, it allows to retrieve the gardens, the measurements from the given garden and the plots from a given garden, in a similar way to the TelegramBot explained above.


**Limitations**:

* Sadly, the project can't support more than 4 gardens since at that point Thingspeak requires paid license.
* In the ThingspeakAdaptor and TelegramBot services it's a bit tedious to configure the keys from Thingspeak, even though it's not a limitation for the services to work, it may limit some particular functions, such as the plot retrieving, so we recommend configuring the API keys before starting any sensors, anyways, the project is meant to run non-stop so in a real-world implementation, where it is not restarted every 10 minutes for testing purposes that shouldn't be a problem.
* When deploying the docker-compose.yml we have noticed that ThingspeakAdaptor service tends to hang waiting for the SRcatalog webservice even though that shouldn't happen as stated on the depends, however, by stopping the multi-container and starting it again it works properly.
* The webdashboard could be improved more, the emphasis was aimed towards the TelegramBot which in fact performs all that webdashboard does and even more.
* For testing purposes the time between measurements is around 15 seconds, which is lower than Thingspeak free sampling time, so some measurements may not be actually sent to Thingspeak, but most of them do.

**How to run the project**:

There are some predefined entities in the catalog.json file, available for testing purposes.
In a command prompt the following 2 lines (if in the correct folder) run the docker-compose.yml file and deploy all the containers.

docker network create testnetwork2
docker-compose up
