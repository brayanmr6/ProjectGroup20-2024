Greetings.
This is the final project for the course Programming for IoT Applications, developed by group #20.


**Summary:**

The project is titled 'GreenTech Hub' and its purpose relies on the caring of gardens, particularly those that you may have at your own home. The project allows a user to register their profile, the gardens they may own, and the devices that each of the gardens may have. In this project, we consider the existence of three kinds of gardens, let's call them 'ecosystem types', they are: dry, tropical and water. Each of them possesses different needs and characteristics. Each garden may have at most, one of these kinds of sensors: temperature, humidity, pH and light; once the sensors are turned on the measurement process starts. A user may have awareness of the state of their garden using either the Telegram chatbot or the web, however, the Telegram chatbot is more personal since it also receives alarms in case some measurement is over the recommended threshold for your garden type. To combat those undesirable measurements, it is also possible for the user to set strategies that will take care of the problematic measurements in your garden. 



**Detailed explanation of each component**:

Inside the scripts, there are also comments regarding some insights and tasks.

The precise endpoints are inside the configFile.json of each of the services.

* SRcatalog: The SR catalog is a software entity whose main task is to help to register and discover devices and services. Essentially it exposes mostly all REST methods (GET, PUT, POST, DELETE) to all entities that may compose the catalog.json (which contains all the services and devices), to be more precise, it contains detailed information about the users, gardens, devices, strategies, MQTT broker, services endpoints and also the crucial key to make the Telegram chatbot work, the token. This catalog is **IS EXPOSED** as a web service and avails any other service to make any kind of REST requests to it (this is crucial for the project since the catalog.json stores the details of each 'entity'). Inside the container, it can be reached by other services at this address: HTTP://SRCATALOG:8089/....

* DeviceConnector: The device connector is a software entity in which we simulate a 'microcontroller' in the sense that in this script the sensors (devices) are controlled (turned ON/OFF), this is performed by a PUT request performed at HTTP://DEVICECONNECTOR:8088/..., this command also triggers another PUT request to the SRCATALOG web service, where the feature 'status' of the device is set to 'on' or 'off'. By default, all sensors are off, but whenever they are turned on, the script automatically starts to simulate measurements of the particular sensor turned on. The service whose task is to subscribe to these messages is the ThingspeakAdaptor, overall. Regarding the strategies, they are also turned on/off at the device connector. 
