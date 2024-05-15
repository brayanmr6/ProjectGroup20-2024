# Programming for IoT applications - Project
# Catalog manager.

# Insights: 
# The catalog manager is the crucial entity of the project, it is essentially used to discover, register and expose
# services and devices; in the context of this project in the catalog; which is a JSON file where all the data about the project
# is stored, to be more precise, it contains data about: the users, the gardens, the devices, the strategies, MQTT broker. It exposes REST web services
# in order to register (POST), update (PUT), read (GET) and delete (DELETE) any of the previously mentioned according to the user queries;
# also, this web service is exposed and then used by another entities of the project, mainly for GET and PUT requests, but not limited to them,
# exploiting REST. In particular, the endpoints of the requests performed by other software entities of the project are stored in a dictionary-way in a configuration
# file stored as a JSON (configFile.json). 
# On the other hand, information about the otherservices is also stored here, in particular regarding names of the services and their ordinary
# endpoint.
# 

# Important to mention: 
# In order to 'maintain' scalability and correlation among all actors, there is also an 'updating' system which scopes to keep the catalog
# updated whenever a user/garden/device/strategy is DELETED/REGISTERED.
# In particular, almost all classes follow the same structure, some functions to load and save changes, and then the REST methods as needed in each case.


import json
import cherrypy
import os
import datetime
import threading
import time
import paho.mqtt.client as mqtt
import requests



class users(object):
    exposed = True

    #  The first three methods are used to manage the catalog itself, which is a JSON file, essentially it facilitates the loading, saving
    # and indexing for access to its contents.
    def __init__(self):
        self.users = []
        self.data_file = "catalog.json"
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as file:
                data = json.load(file)
                self.users = data.get("users", [])
                self.devices = data.get("devices",[])
                self.gardens = data.get("gardens",[])
                self.strategies = data.get("strategies",[])
                self.MQTTbroker = data["MQTTbroker"]
                self.port = data["port"]
                self.chatbotToken = data["chatbotToken"]
                self.services = data.get("services",[])

    def save_data(self):
        data = {"MQTTbroker": self.MQTTbroker, "port": self.port, "users": self.users,  "gardens": self.gardens, "devices": self.devices, "strategies": self.strategies, "chatbotToken": self.chatbotToken, "services": self.services}
        with open(self.data_file, "w") as file:
            json.dump(data, file)


    # The GET method in class users has the following functions:
    # - Retrieve all the information related to "users": [ ... ] in the JSON file http://localhost:port/users/printallusers
    # - Retrieve a particular user based on the user ID provided in the URI, http://localhost:port/users/searchuserid/userid
    # - Retrieve a particular user based on the garden ID provided in the URI, http://localhost:port/users/searchusergarden/gardenid
    # - Retrieve a particular user based on his/her username provided in the URI, http://localhost:port/users/searchuserusername/username
    def GET(self,*uri):
        possibleCommands = ["printallusers","searchuserid","searchusergarden","searchuserusername"]
        if len(uri) != 0:
            
            if len(uri)==1:    
                userCommand = str(uri[0]).lower()
                if userCommand == "printallusers":
                    return json.dumps(self.users)
                else:
                    return "The URI has size 1, but the only available command is http://localhost:port/users/printallusers"
                 
            elif len(uri)==2:
                    userCommand = str(uri[0]).lower()
                    if userCommand in possibleCommands:
                        if userCommand == "searchuserid":
                            try:
                                userID = int(uri[1])
                                for user in self.users:
                                    if userID == user.get('id'):
                                        return json.dumps(user)
                                return "User not found with the given ID, refer to http://localhost:port/users/searchuserid/userid"
                            except:
                                return "There seems to be a problem with the user ID, it must be an integer. Refer to http://localhost:port/users/searchuserid/userid"
                        elif userCommand == "searchusergarden":
                            try:
                                gardenID = int(uri[1])
                                for user in self.users:
                                    for garden in user.get("gardens", []):
                                        if gardenID == garden.get("gardenId"):
                                            return json.dumps(user)
                                return "User with given garden ID not found, refer to http://localhost:port/users/searchusergarden/gardenid"
                            except:
                                return "There seems to be a problem with the garden ID, it must be an integer. Refer to http://localhost:port/users/searchusergarden/gardenid "
                        elif userCommand == "searchuserusername":
                            username = str(uri[1]).lower()
                            for user in self.users:
                                if username == str(user.get('username')).lower():
                                    return json.dumps(user)
                            return "User with given username not found. Refer to http://localhost:port/users/searchuserusername/username"
            else:
                return "The URI size seems to be larger than 2, which is invalid, try again, refer to http://localhost:port/users/.../..."
        else:
            return "The URI is empty, refer to http://localhost:port/users/.../..."
    

    # The PUT method in the class users has the following functions:
    # - Update the username of an user in the following way http://localhost:port/users/updateuser
    # - Update the password of an user in the following way http://localhost:port/users/updateuser
    # The JSON body request should contain at least:
    # {"userID": id,
    #  "password": password,
    #  "newusername": newusername,
    #  "newpassword": newpassword} #Only if we want to change the password of the user, if it's only the username ignore it.
    def PUT(self, *uri):
        possibleCommands = ["updateuser"]
        if len(uri) != 0:
            if len(uri) == 1:
                userCommand = str(uri[0]).lower()
                if userCommand in possibleCommands:
                    self.load_data()
                    updatedData = json.loads(cherrypy.request.body.read().decode('utf-8'))
                    if updatedData:
                        if "userID" in updatedData and "password" in updatedData:
                            try:
                                userID = int(updatedData["userID"])
                                password = updatedData["password"]
                                for user in self.users:
                                    if userID == user.get("userID") and password == user.get("password"):
                                        if "newusername" in updatedData:
                                            user["username"] = updatedData["newusername"]
                                            self.save_data()
                                        if "newpassword" in updatedData:
                                            user["password"] = updatedData["newpassword"]
                                            self.save_data()
                                        return "User updated successfully." 
                                return "There userID/password provided in the JSON body do not match."
                            except:
                                return "There seems to be a problem in the JSON request, userID must be an integer."
                        else:
                            return "There is no userID in the body JSON request. It requires the user ID for update."
                    else:
                        return "The body of the JSON requests is empty."   
                else:
                    return "The command at the URI is unknown, refer to http://localhost:port/users/updateuser"        
            else:
                return "The URI size is larger than 1, it is not possible, refer to http://localhost:port/users/updateuser"
        else:
            return "The URI is empty, refer to http://localhost:port/users/updateuser"
        

    # The POST method in the class has the following functions:
    # - Registers a new user, but only username, id, password, registration_date (dd-mm-yyyy), gardens is []
    # - https://localhost:port/users/registeruser/username/password
    
    def POST(self,*uri):
        possibleCommands = ["registeruser"]
        if len(uri) != 0:
            userCommand = str(uri[0]).lower()
            if userCommand in possibleCommands:
                
                if len(uri) == 3:
                    username = uri[1]
                    password = uri[2]

                    if any(user["username"] == username for user in self.users):
                        return "Username already exists. Please choose another one."
                            
                    new_id = max(user['userID'] for user in self.users) + 1 if self.users else 1     
                    registration_date = datetime.datetime.now().strftime("%d-%m-%Y")
                    new_user = {
                                "username": username,
                                "userID": new_id,
                                "password": password,
                                "registration_date": registration_date,
                                "gardens": []
                            }      
                    self.users.append(new_user) 
                    self.save_data()       
                    return "User registered successfully."
                else:
                    return "The length of the URI is incorrect than 3, refer to http://localhost:port/users/registeruser/username/password"
            else:
               return "The command provided is unknown, please refer to http://localhost:port/users/registeruser/username/password"
        else:
            return "The URI is empty, refer to http://localhost:port/users/registeruser/username/password" 
           
    # The DELETE method for class user deletes all the information related to an user given its ID and password:
    # Delete user information, http://localhost:port/users/deleteuser/id/password, it should go with id since delete is not reversible!
    def DELETE(self, *uri):
        possibleCommands = ["deleteuser"]
        if len(uri) != 0:
            userCommand = str(uri[0]).lower()
            if userCommand in possibleCommands:
                if len(uri) == 3:
                    userID = uri[1]
                    password = uri[2]
                    self.load_data()
            
                    try:
                        userID = int(userID)
                    except :
                        return "Invalid userID format. It should be an integer, http://localhost:port/users/deleteuser/userid/password"
                    
                    
                    for user in self.users:
                        if userID == user.get('userID'):
                            if password == user.get('password'):
                                self.users.remove(user)
                                self.save_data()
                                return "The user was deleted successfully."
                            else:
                                return "Incorrect password."
                    
                    return "The user provided was not found."
                else:
                    return "The URI length is incorrect, refer to http://localhost:port/users/deleteuser/userid/password"
            else:
                return "The command provided at the URI doesn't exist, refer to http://localhost:port/users/deleteuser/userid/password" 
        else:
            return "The URI is empty, refer to http://localhost:port/users/deleteuser/userid/password"

        
class devices(object):
    exposed = True

    #  The first three methods are used to manage the catalog itself, which is a JSON file, essentially it facilitates the loading, saving
    # and indexing for access to its contents.
    def __init__(self):
        self.users = []
        self.data_file = "catalog.json"
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as file:
                data = json.load(file)
                self.users = data.get("users", [])
                self.devices = data.get("devices",[])
                self.gardens = data.get("gardens",[])
                self.strategies = data.get("strategies",[])
                self.MQTTbroker = data["MQTTbroker"]
                self.port = data["port"]
                self.chatbotToken = data["chatbotToken"]
                self.services = data.get("services",[])

    def save_data(self):
        data = {"MQTTbroker": self.MQTTbroker, "port": self.port, "users": self.users,  "gardens": self.gardens, "devices": self.devices, "strategies": self.strategies, "chatbotToken": self.chatbotToken, "services": self.services}
        with open(self.data_file, "w") as file:
            json.dump(data, file)

    # The GET method for class devices is used for:
    # - Retrieve all the information related to "devices": [ ... ] in the JSON file http://localhost:port/devices/printalldevices
    # - Retrieve a particular device based on the device ID provided in the URI, http://localhost:port/devices/searchdeviceid/deviceid
    # - Retrieve a particular device(s) based on the garden ID provided in the URI, http://localhost:port/devices/searchdevicesgarden/gardenid
    def GET(self,*uri):
        possibleCommands = ["printalldevices","searchdeviceid","searchdevicesgarden"]
        if len(uri) != 0:
            userCommand = str(uri[0]).lower()
            if len(uri) == 1:
                if userCommand in possibleCommands and userCommand == "printalldevices":
                    return json.dumps(self.devices)
                else:
                    return "The command is unknown, if the URI length is 1 the only command available is http://localhost:port/devices/printalldevices"
            elif len(uri) == 2:
                if userCommand in possibleCommands:
                    if userCommand == "searchdeviceid":
                        try:
                            inputdeviceID = int(uri[1])
                        except:
                            return "The input device ID is not an integener, refer to http://localhost:port/devices/searchdeviceid/deviceid"
                        
                        for device in self.devices:
                            if inputdeviceID == device.get("deviceID"):
                                return json.dumps(device)
                        return "The device was not found with the given ID, refer to http://localhost:port/devices/searchdeviceid/deviceid"
                    elif userCommand == "searchdevicesgarden":
                        try:
                            inputgardenID = int(uri[1])
                            gardens = []
                        except:
                            return "The input garden ID is not an integener, refer to http://localhost:port/devices/searchdevicesgarden/gardenid"
                        
                        for device in self.devices:
                            if inputgardenID == device.get("gardenID"):
                                gardens.append(device)
                        if gardens:
                            return json.dumps(gardens)
                        else:
                            return "No devices were found associated with the given garden ID, refer to http://localhost:port/devices/searchdevicesgarden/gardenid"    
                    else:
                        return "The URI is incorrect, if URI length equals 2, searchdeviceid or searchdevicesgarden"
                else:
                    return "The commands at the URI are unknown, searchdeviceid or searchdevicesgarden"
            else:
                return "The URI length is incorrect, it can be only 1 or 2."
        else:
            return "The URI is empty! refer to http://localhost:port/devices/.../... "
                
        
    # The PUT method for class devices is used for updating a device:
    # - Very important, I think a device can only update: - deviceName, availableServices, gardenID.
    # Since it makes no sense to update a device ID, since it's an unique identifier, also measure type is unique to each device.
    # However the way to use this requires the ID of the device to update, in this way: http://localhost:port/devices/updatedevice/deviceID
        
    def PUT(self, *uri):
        possibleCommands = ["updatedevice"]
        
        if len(uri) == 2: 
            try:
                userDeviceID = int(uri[1])
            except:
                return "The device ID at the URI is not an integer, http://localhost:port/devices/updatedevice/deviceid"
                
            userCommand = str(uri[0]).lower()
            if userCommand in possibleCommands:
                self.load_data()
                for device in self.devices:
                    if userDeviceID == device.get("deviceID"):
                        updatedData = json.loads(cherrypy.request.body.read().decode('utf-8'))

                        if "gardenID" in updatedData:
                            for garden in self.gardens:
                                if updatedData["gardenID"] == garden.get("gardenID"):
                                    mqtt_topics = []
                                    if "availableServices" in device and "MQTT" in device['availableServices']:
                                        measure_types = device.get('measureType')
                                        if isinstance(measure_types, list):
                                            for measure_type in measure_types:
                                                mqtt_topic = "IoTProject/{}/{}/{}".format(updatedData['gardenID'], measure_type.lower(), userDeviceID)
                                                mqtt_topics.append(mqtt_topic)
                                        elif isinstance(measure_types, str):
                                            mqtt_topic = "IoTProject/{}/{}/{}".format(updatedData['gardenID'], measure_types.lower(), userDeviceID)
                                            mqtt_topics.append(mqtt_topic)
                                        else:
                                            return "Invalid measureType format. It should be a string or a list."
                                    
                                    device['MQTTtopic'] = mqtt_topics
                                    device.update(updatedData)
                                    self.save_data()
                                    return "The device was updated successfully."
                            else:
                                return "The new garden provided does not exist."
                        else:
                            device.update(updatedData)
                            self.save_data()
                            return "The device was updated successfully."
                else:
                        return "The provided device ID does not exist, therefore cannot be updated."
            else:
                return "The URI command is unknown. Check 'updatedevice'. Refer to http://localhost:port/devices/updatedevice/deviceid"
        else:
            return "The URI has an incorrect length. Refer to http://localhost:port/devices/updatedevice/deviceid"


    # The POST method for class devices is used for adding new devices to the catalog:
    # - It must be reached in this way: https//localhost:port/devices/registerdevice/
    # {"deviceName": name,
    # "measureType": list
    # "gardenID": id, mandatory to include
    # "availabeServices": [MQTT,REST], list
    # "endpoints": [], #TODO: Do devices need REST? I think not, so only the MQTT topic is enough.
    # VERY IMPORTANT: in order to proceed with this, since there are numerous fields it's better to use requests library and get the JSON
    # with the information about the device. VERY IMPORTANT: device name can be repeated, since usually all sensors from the same type and 
    # manufacturer are named exactly equal, however the deviceID must be unique amongst all of them.
    def POST(self,*uri):
        possibleCommands = ["registerdevice"]
        if len(uri) != 0:
            if len(uri) == 1:
                userCommand = str(uri[0]).lower()
                if userCommand in possibleCommands:
                    self.load_data()
                    new_device = json.loads(cherrypy.request.body.read().decode('utf-8'))
                    if "deviceID" in new_device:
                        return "The ID assignation is automatic, this field can not be contained in the JSON body request."
                    else:
                        pass
                    if "gardenID" in new_device:
                        found = False
                        providedgardenID = new_device["gardenID"]
                        for garden in self.gardens:
                            if providedgardenID == garden.get("gardenID"):
                                found = True
                        if not found:
                            return "There is no garden associated with the garden ID of the JSON body content, all devices must belong to a previous registered garden. "
                    else:
                        return "There is no garden ID in the JSON body request, all devices must belong to a previous registered garden."
                    
                    new_id = max(device['deviceID'] for device in self.devices) + 1 if self.devices else 1
                    registration_date = datetime.datetime.now().strftime("%d-%m-%Y")
                    new_device["deviceID"] = new_id
                    new_device["registrationDate"] = registration_date
                    new_device["status"] = "off"
                    mqtt_topics = []
                    
                    if "availableServices" in new_device and "MQTT" in new_device["availableServices"]:
                        measure_types = new_device.get("measureType")
                        if isinstance(measure_types, list):
                            for measure_type in measure_types:
                                mqtt_topic = "IoTProject/{}/{}/{}".format(providedgardenID, measure_type.lower(), new_id)
                                mqtt_topics.append(mqtt_topic)
                        elif isinstance(measure_types, str):
                            mqtt_topic = "IoTProject/{}/{}/{}".format(providedgardenID, measure_types.lower(), new_id)
                            mqtt_topics.append(mqtt_topic)
                        else:
                            return "Invalid measureType format. It should be a string or a list."
                    if new_device['measureType'][0].lower() == "temperature":
                        new_device['unit'] = "Cel"
                    elif new_device["measureType"][0].lower() == "humidity":
                        new_device['unit'] = "%"
                    elif new_device["measureType"][0].lower() == "ph":
                        new_device["unit"] = "units"
                    elif new_device["measureType"][0].lower() == "light":
                        new_device["unit"] = "Lux"
                    new_device["MQTTtopics"] = mqtt_topics

                    self.devices.append(new_device)
                    self.save_data()
                    return "New device registered"
                else: 
                    return "The command is unknown, refer only to: http://localhost:port/devices/registerdevice"
            else:
                return "The URI length is incorrect, refer only to: http://localhost:port/devices/registerdevice"
        else:
            return "The URI is empty, refer to http://localhost:port/devices/registerdevice"
        
    # The method DELETE of class devices will be used only to delete a device, and all the information related to it, nothing else in particular.
    # All the information is deleted. The way to access to it is: http://localhost:port/devices/deletedevice/deviceid
    def DELETE(self,*uri):
        possibleCommands = ["deletedevice"]
        if len(uri) != 0:
            if len(uri) == 2:
                userCommand = str(uri[0]).lower()
                try:
                    userDeviceID = int(uri[1])
                except:
                    return "The deviceID given at the URI is not an integer, refer to http://localhost:port/devices/deletedevice/deviceid"
                    
                self.load_data()
                if userCommand in possibleCommands:
                    for device in self.devices:
                        if userDeviceID == device.get("deviceID"):
                            self.devices.remove(device)
                            self.save_data()
                            return "The device was deleted successfully."
                    else:
                        return "No device found with the given ID, refer to http://localhost:port/devices/deletedevice/deviceid"
                else:
                    return "The URI is command of the URI is unknown, refer to http://localhost:port/devices/deletedevice/deviceid"
            else:
                return "The URI is incorrect, refer to http://localhost:port/devices/deletedevice/deviceid"
        else:
            return "The URI is empty, refer to http://localhost:port/devices/deletedevice/deviceid"
        
class gardens(object):
    
    exposed = True

    #  The first three methods are used to manage the catalog itself, which is a JSON file, essentially it facilitates the loading, saving
    # and indexing for access to its contents.
    def __init__(self):
        self.users = []
        self.data_file = "catalog.json"
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as file:
                data = json.load(file)
                self.users = data.get("users", [])
                self.devices = data.get("devices",[])
                self.gardens = data.get("gardens",[])
                self.strategies = data.get("strategies",[])
                self.MQTTbroker = data["MQTTbroker"]
                self.port = data["port"]
                self.chatbotToken = data["chatbotToken"]
                self.services = data.get("services",[])

    def save_data(self):
        data = {"MQTTbroker": self.MQTTbroker, "port": self.port, "users": self.users,  "gardens": self.gardens, "devices": self.devices, "strategies": self.strategies, "chatbotToken": self.chatbotToken, "services": self.services}
        with open(self.data_file, "w") as file:
            json.dump(data, file)
    
    
    # The GET method for class gardens is used for:
    # - Retrieve all the information related to "gardens": [ ... ] in the JSON file http://localhost:port/gardens/printallgardens
    # - Retrieve a particular garden based on the garden ID provided in the URI, http://localhost:port/gardens/searchgardenid/gardenid
    # - Retrieve a particular garden(s) based on the user owner ID provided in the URI, http://localhost:port/gardens/searchgardensuser/userid
    def GET(self,*uri):
        possibleCommands = ["printallgardens","searchgardenid","searchgardensuser"]
        if len(uri) != 0:
            if len(uri) == 1 and str(uri[0]).lower() in possibleCommands:
                return json.dumps(self.gardens)
            
            elif len(uri) == 2 and str(uri[0]).lower() in possibleCommands:
                userCommand = str(uri[0]).lower()
                
                if userCommand == "searchgardenid":
                    try:
                        gardenID = int(uri[1])
                        for garden in self.gardens:
                            if gardenID == garden.get("gardenID"):
                                return json.dumps(garden)
                        return "No garden could be found with the provided garden ID. Refer to http://localhost:port/gardens/searchgardenid/gardenid"
                    except:
                        return "There is a problem with the garden ID provided, it must be an integer number. Refer to http://localhost:port/gardens/searchgardenid/gardenid"
                
                elif userCommand == "searchgardensuser":
                    gardens = []
                    try:
                        userID = int(uri[1])
                        for user in self.users:
                            if userID == user.get("userID"):
                                for garden in self.gardens:
                                    if garden["gardenOwnerUserID"] == userID:
                                        gardens.append(garden)
                        if gardens:
                            return json.dumps(gardens)
                        else:
                            return "There are not gardens associated with the user ID provided. Refer to http://localhost:port/gardens/searchgardensuser/userid "
                    except:
                            return "There is a problem with the user ID provided, it must be an integer number. Refer to http://localhost:port/gardens/searchgardensuser/userid"           
            else:
                return "Unkown command."
        else:
            return "The URI is empty, refer to refer to http://localhost:port/gardens/.../..."
        
    # The PUT method would allow to update the gardens, in particular I think these are the attributes that can change about the gardens so far:
    # gardenName
    # ecosystemType
    # ownerUserID (for example a user transfers its garden to someone else)
    # externalLights
    # Here maybe we should be able to update available devices but I'll do an automatic script to do that whenever a new user/device/garden is
    # added or deledted or something else, so only the 4 features above can be updated here.
        
    # The request body simply has to put the desired keys to change.
    def PUT(self,*uri):
        possibleCommands = ["updategarden"]
        if len(uri) != 0:
            if len(uri) == 1:
                
                userCommand = str(uri[0]).lower()
                if userCommand in possibleCommands:
                    self.load_data()
                    updatedData = json.loads(cherrypy.request.body.read().decode('utf-8'))
                    gardenID = updatedData.get("gardenID")
                    for garden in self.gardens:
                        if gardenID == garden.get("gardenID"):
                            
                            garden.update(updatedData)
                            self.save_data()
                            return "The garden has been updated succesfully."
                    return "The garden could not be updated since no device was found with the given garden ID in the request."        
                else:
                    return "The command is unknown. Refer to http://localhost:port/gardens/updategarden"
            else:
                return "The URI size is larger than 0. Refer to http://localhost:port/gardens/updategarden"
        else:
            return "The URI is empty, refer to http://localhost:port/gardens/updategarden"



    # The POST method of gardens allows to register a garden.
    # The body requested at the web service should include:
    # {gardenName: name
    # gardenOwnerID: userID of the owner
    # ecosystemType: dry/mid/tropical
    # availableMeasures: [temperature/humidity/ph/lighthing] EMPTY AT FIRST
    # availableDevices: [empty at first]} EMPTY AT FIRST

    # Then the script must assign an automatic numeric ID for the garden, and probably endpoints but to see later.
    
    def POST(self,*uri):
        possibleCommands = ["registergarden"]
        if len(uri) != 0:
            if len(uri) == 2:
                try:
                    userCommand = str(uri[0]).lower()
                    owneruserID = int(uri[1])
                    if userCommand in possibleCommands:
                        user_exists = False
                        for user in self.users: 
                            if owneruserID == user.get("userID"):
                                user_exists = True
                                break 
                        if user_exists:
                            self.load_data()
                            new_garden = json.loads(cherrypy.request.body.read().decode('utf-8'))
                            new_gardenID = max(garden['gardenID'] for garden in self.gardens) + 1 if self.gardens else 1
                            registration_date = datetime.datetime.now().strftime("%d-%m-%Y")
                            new_garden["gardenID"] = new_gardenID
                            new_garden["registrationDate"] = registration_date
                            new_garden["gardenOwnerUserID"] = owneruserID
                            new_garden["availableMeasures"] = []
                            new_garden["availableDevices"] = []
                            new_garden["externalLights"] = "off"
                            self.gardens.append(new_garden)
                            self.save_data()
                            return "The new garden has been registered succesfully."
                        else:
                            return "The garden cannot be registered because the user ID provided does not exist."
                    else:
                        return "The command provided seems not to exist, refer to http://localhost:port/gardens/registergarden/userID"           
                except:
                    return "The command provided seems not to exist or the user ID is invalid, refer to http://localhost:port/gardens/registergarden/userID"
            else:
                return "The URI is larger or lower than two, refer to http://localhost:port/gardens/registergarden/userID"
        else:
            return "The URI is empty, refer to refer to http://localhost:port/gardens/registergarden/userID"

    # Used to delete all the information of a garden, http://localhost:port/gardens/deletegarden/gardenID  
    def DELETE(self,*uri):
        possibleCommands = ["deletegarden"]
        if len(uri) != 0:
            if len(uri) == 2:
                try:
                    userCommand = str(uri[0]).lower()
                    usergardenID = int(uri[1])
                    self.load_data()
                    if userCommand in possibleCommands:
                        for garden in self.gardens:
                            if usergardenID == garden.get("gardenID"):
                                self.gardens.remove(garden)
                                self.save_data()
                                return "The garden was deleted successfully."
                            
                        return "The garden could not be deleted since there are no gardens associated with the given ID. Refer to http://localhost:port/gardens/deletegarden/gardenID "
                    else:
                        return "The command is unknown. Refer to http://localhost:port/gardens/deletegarden/gardenID "
                except:
                    return "The garden ID must be an integer number. Refer to http://localhost:port/gardens/deletegarden/gardenID"
            else:
                return "The DELETE method allows only 2 URI, refer to http://localhost:port/gardens/deletegarden/gardenID "
        else:
            return "The URI is empty, refer to http://localhost:port/gardens/deletegarden/gardenID "
        

class strategies(object):
    exposed = True

    def __init__(self):
        self.users = []
        self.data_file = "catalog.json"
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as file:
                data = json.load(file)
                self.users = data.get("users", [])
                self.devices = data.get("devices",[])
                self.gardens = data.get("gardens",[])
                self.strategies = data.get("strategies",[])
                self.MQTTbroker = data["MQTTbroker"]
                self.port = data["port"]
                self.chatbotToken = data["chatbotToken"]
                self.services = data.get("services",[])

    def save_data(self):
        data = {"MQTTbroker": self.MQTTbroker, "port": self.port, "users": self.users,  "gardens": self.gardens, "devices": self.devices, "strategies": self.strategies, "chatbotToken": self.chatbotToken, "services": self.services}
        with open(self.data_file, "w") as file:
            json.dump(data, file)

    
    
    def GET(self,*uri):
        if len(uri) != 0:
            userCommand = str(uri[0]).lower()
            if len(uri) == 1:
                if userCommand == "printallstrategies":
                    return (json.dumps(self.strategies))
                else:
                    "The command is unknown, since the URI is 1, refer to http://localhost:port/strategies/printallstrategies"
            elif len(uri) == 2:
                if userCommand == "printgardenstrategies":
                    try:
                        gardenID = int(uri[1])
                        strategies = []
                        gardenExists = False
                        for garden in self.gardens:
                            if garden["gardenID"] == gardenID:
                                gardenExists = True
                        if gardenExists == True:
                            for strategy in self.strategies:
                                if strategy["gardenID"]== gardenID:
                                    strategies.append(strategy)
                            if strategies:
                                return json.dumps(strategies)
                            else:
                                return "Sadly there are not strategies associated for that garden."
                        else:
                            return "The garden ID provided seems not to exist."
                    except:
                        return "Check the URI components, gardenID must be an integer."
                else:
                    return "Something wrong"
            else:
                return "The URI is to long, its maximum length is 2."              
        else:
            return "The URI is empty, refer to refer to http://localhost:port/strategies/..."

    
    # The POST method of strategies allow to register a strategy for a certain
    # measure. Okay, we need to first know which garden to register the strategy, what measure
    # initially the web service must ensure that the garden ID and measure do exist and are available in that garden.
    # Then, the strategies work like this: 
    # First, a value of the strategy determines how often does the sensor of that measure senses, then 
    # Second, set lowest and highest allowed values, it the measure goes up or below:
    #           - The famous telegram alarm is sent
    #           - The actuators, which I think they are implicit and not 'declared' as devices start to normalize the measure
    #           to keep it within the user set range.
            
    # I think it is nice to exposed it at http://localhost:port/strategies/registerstrategy/GARDENID/MEASURE
    # Then the JSON body of the request should be: {"maximumValue": max,
    #                                               "minimumValue": min,
    #                                               "samplingFreq": frequency}
    # So, in overall, the resource catalog (the JSON) will register the frequency like this
    # also, THE STRATEGY IS BY DEFAULT REGISTERED AS OFF, IT NEEDS TO BE ACTIVATED ON THE DEVICE CONNECTOR.
    """ {"gardenID": id,
     "ecosystemType": eco,
     "measure": measure,
     "maxiumValue": max,
     "minimumValue": min,
     "status": off}    """         

    def POST(self,*uri):
        possibleCommands = ["registerstrategy"]
        if len(uri) != 0:
            if len(uri) == 3:
                try:
                    userCommand = str(uri[0]).lower()
                    gardenID = int(uri[1])
                    measureType = str(uri[2]).lower()
                    for strategy in self.strategies:
                        if gardenID == strategy.get("gardenID") and measureType == strategy.get("measureType"):
                            return "There is already a strategy associated with the given garden and measure type, modify it instead."

                    if userCommand in possibleCommands:
                        garden_exists = False
                        for garden in self.gardens: 
                            if gardenID == garden.get("gardenID"):
                                for available_measure in garden.get("availableMeasures"):
                                    if measureType == available_measure.lower():
                                        garden_exists = True
                                        ecosystemType = garden.get("ecosystemType")
                                        break
       
                        if garden_exists:
                            self.load_data()
                            new_strategy = json.loads(cherrypy.request.body.read().decode('utf-8'))
                            new_strategy["gardenID"] = gardenID
                            new_strategy["ecosystemType"] = ecosystemType
                            registration_date = datetime.datetime.now().strftime("%d-%m-%Y")
                            new_strategy["registrationDate"] = registration_date
                            new_strategy["measureType"] = measureType
                            new_strategy["status"] = "off"
                            self.strategies.append(new_strategy)
                            self.save_data()
                            return "The new strategy has been registered succesfully."
                        else:
                            return "The strategy cannot be registered because the garden ID provided or the garden does not have that measure."
                    else:
                        return "The command provided seems not to exist, refer to http://localhost:port/strategies/registerstrategy/GARDENID/MEASURE"           
                except:
                    return "The command provided seems not to exist or the user ID is invalid, refer to http://localhost:port/strategies/registerstrategy/GARDENID/MEASURE"
            else:
                return "The URI is larger or lower than three, refer to http://localhost:port/strategies/registerstrategy/GARDENID/MEASURE"
        else:
            return "The URI is empty, refer to refer to http://localhost:port/strategies/registerstrategy/GARDENID/MEASURE"
    
    # Well, only thing we can tweak about the strategies are the minimum value, maximum value.
    # changing ecosystemType depends on the garden so then in the updater will take care of this, and changing
    # measure kind of strategy makes 0 sense, so only those 2 features mentioned before.
    def PUT(self,*uri):
        if len(uri) != 0:
            if len(uri) == 3:
                try:
                    userCommand = str(uri[0]).lower()
                    gardenID = int(uri[1])
                    measureType = str(uri[2]).lower()
                    updatedData = json.loads(cherrypy.request.body.read().decode('utf-8'))
                    if userCommand == "updatestrategy":
                        for strategy in self.strategies:
                            if strategy["gardenID"] == gardenID and strategy["measureType"] == measureType:
                                strategy.update(updatedData)
                                self.save_data()
                                return "Strategy updated successfully."
                        return "Strategy not found, no updates carried out."
                    else:
                        return "Unknown command."
                except:
                    return "Check your math, kid"
            else:
                return "Wrong format"
        else: 
            return "The URI is empty."
    
    
    
    def DELETE(self,*uri):
        if len(uri) != 0:
            if len(uri) == 3:
                if str(uri[0]).lower() == "deletestrategy":
                    try:
                        gardenID = int(uri[1])
                        measure = str(uri[2]).lower()
                        
                        for strategy in self.strategies:
                            if strategy["gardenID"] == gardenID and str(strategy["measureType"]).lower() == measure:
                                self.strategies.remove(strategy)
                                self.save_data()
                                return "The strategy was deleted successfully."
                        return "The strategy for the given GARDENID and measuretype was not found, please recheck http://localhost:port/strategies/deletestrategy/GARDENID/MEASURE"
                    except:
                        return "Something wrong with the URI components, gardenID must be an integer. http://localhost:port/strategies/deletestrategy/GARDENID/MEASURE"
                else:
                    "Only available command is deletestrategy, therefore unknown command."
            else:
                "The URI length is wrong, refer to http://localhost:port/strategies/deletestrategy/GARDENID/MEASURE"
        else:
            "The URI is empty, refer to http://localhost:port/strategies/deletestrategy/GARDENID/MEASURE"


        
class MQTTbroker(object):
    exposed = True

    def __init__(self):
        self.users = []
        self.data_file = "catalog.json"
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as file:
                data = json.load(file)
                self.users = data.get("users", [])
                self.devices = data.get("devices",[])
                self.gardens = data.get("gardens",[])
                self.strategies = data.get("strategies",[])
                self.MQTTbroker = data["MQTTbroker"]
                self.port = data["port"]
                self.chatbotToken = data["chatbotToken"]
                self.services = data.get("services",[])

    def save_data(self):
        data = {"MQTTbroker": self.MQTTbroker, "port": self.port, "users": self.users,  "gardens": self.gardens, "devices": self.devices, "strategies": self.strategies, "chatbotToken": self.chatbotToken, "services": self.services}
        with open(self.data_file, "w") as file:
            json.dump(data, file)

    def GET(self,*uri):
        if uri[0] == 'mqttdata':
            response = {"broker": self.MQTTbroker, "port": self.port}
            return json.dumps(response)


class catalog(object):
    
    exposed = True
    
    def __init__(self):
        self.users = []
        self.data_file = "catalog.json"
     
    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as file:
                self.data = json.load(file)
        else:
            self.data = {}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def GET(self, *uri):
        self.load_data()  
        if len(uri) == 1 and str(uri[0]).lower() == "printall":
            return self.data


# The purpose of this class is to keep the catalog updated, for example:
# If a new garden is registered then it must be visible also in the users, the opposite if it's deleted
# Also for the devices in each garden.
class catalogUpdater(object):
    exposed = True

    #  The first three methods are used to manage the catalog itself, which is a JSON file, essentially it facilitates the loading, saving
    # and indexing for access to its contents.
    def __init__(self):
        self.users = []
        self.data_file = "catalog.json"
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as file:
                data = json.load(file)
                self.users = data.get("users", [])
                self.devices = data.get("devices",[])
                self.gardens = data.get("gardens",[])
                self.strategies = data.get("strategies",[])
                self.MQTTbroker = data["MQTTbroker"]
                self.port = data["port"]
                self.chatbotToken = data["chatbotToken"]
                self.services = data.get("services",[])

    def save_data(self):
        data = {"MQTTbroker": self.MQTTbroker, "port": self.port, "users": self.users,  "gardens": self.gardens, "devices": self.devices, "strategies": self.strategies, "chatbotToken": self.chatbotToken, "services": self.services}
        with open(self.data_file, "w") as file:
            json.dump(data, file)

    # For users, what we need to care on is the list of gardens associated to each user.
    # When a new user is registered it has an empty list of gardens, let's use this method to keep that list updated with the registered/deleted gardens.
    # We can monitor it every 30 seconds.         
    def checkUsers(self):
        self.load_data()
        for user in self.users:
            for garden in self.gardens:
                if user["userID"] == garden["gardenOwnerUserID"]:
                    if garden["gardenID"] in user["gardens"]:
                        break
                    else:
                        user["gardens"].append(garden["gardenID"])
        self.save_data()

    # Then we have the gardens, in gardens what we need to keep updated are: the id of the devices that are inside a garden (e.g. check if a device was
    # registered/deleted and update the garden information, but also the available measures (temperature,humidity,etc) this depends on the sensors themselves.
    def checkGardens(self):
        self.load_data()
        # First let's approach the devices
        for garden in self.gardens:
            devices = []
            for device in self.devices:
                if garden["gardenID"] == device["gardenID"]:
                    devices.append(device["deviceID"])
            garden["availableDevices"] = devices
        self.save_data()

        #Secondly the available measures.
        for garden in self.gardens:
            measures = []
            for device in self.devices:
                if garden["gardenID"] == device["gardenID"]:
                    measures.extend(device["measureType"])
            measures = set(measures)
            measures = list(measures)
            garden["availableMeasures"] = measures
        self.save_data()

    # This is used to delete all the information that depends on an user, for example if user A is deleted, then all gardens associated
    # with user A are deleted and subsequently all the devices associated to those gardens.
    def userAndGardenDeletion(self):
        self.load_data()
        existantUsers = []
        for user in self.users:
            existantUsers.append(user["userID"])

        for garden in self.gardens:
            if garden["gardenOwnerUserID"] not in existantUsers:
                self.gardens.remove(garden)

        existantGardens = []
        for garden in self.gardens:
            existantGardens.append(garden["gardenID"])

        for user in self.users:
            for garden in user["gardens"]:
                if garden not in existantGardens:
                    user["gardens"].remove(garden)
        self.save_data()

        for device in self.devices:
            if device["gardenID"] not in existantGardens:
                self.devices.remove(device)
        self.save_data()

    def checkStrategies(self):
        # First, we need to check if the garden for which the strategy is registered still exists, this is in case
        # it gets deleted, all this works like a feedforward fashion.
        self.load_data()
        gardensExistant = []
        for garden in self.gardens:
            gardensExistant.append(garden["gardenID"])

        for strategy in self.strategies:
            if strategy["gardenID"] not in gardensExistant:
                self.strategies.remove(strategy)
                self.save_data()

        for strategy in self.strategies:
            for garden in self.gardens:
                if strategy["gardenID"] == garden["gardenID"]:
                    if strategy["ecosystemType"] != garden["ecosystemType"]:
                        strategy["ecosystemType"] = garden["ecosystemType"]
                        self.save_data()

        
    def periodic_check(self):
        while True:
            self.checkUsers()
            self.checkGardens()
            self.checkStrategies()
            self.userAndGardenDeletion()
            time.sleep(5)

class services(object):

    exposed = True

    def __init__(self):
        self.users = []
        self.data_file = "catalog.json"
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as file:
                data = json.load(file)
                self.users = data.get("users", [])
                self.devices = data.get("devices",[])
                self.gardens = data.get("gardens",[])
                self.strategies = data.get("strategies",[])
                self.MQTTbroker = data["MQTTbroker"]
                self.port = data["port"]
                self.chatbotToken = data["chatbotToken"]
                self.services = data.get("services",[])

    def save_data(self):
        data = {"MQTTbroker": self.MQTTbroker, "port": self.port, "users": self.users,  "gardens": self.gardens, "devices": self.devices, "strategies": self.strategies, "chatbotToken": self.chatbotToken, "services": self.services}
        with open(self.data_file, "w") as file:
            json.dump(data, file)

    def GET(self,*uri):
        if len(uri) == 1 and str(uri[0]).lower() == "getservices":
            return json.dumps(self.services)
        
    def POST(self,*uri):
        if len(uri) == 1 and str(uri[0]).lower() == "registerservice":
            self.load_data()
            newService = json.loads(cherrypy.request.body.read().decode('utf-8'))
            service = {"serviceName": newService["name"],
                    "serviceEndpoint": newService["endpoint"]
                    }
            self.services.append(service)
            self.save_data()



class bot(object):
    exposed = True

    def __init__(self):
        self.users = []
        self.data_file = "catalog.json"
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as file:
                data = json.load(file)
                self.users = data.get("users", [])
                self.devices = data.get("devices",[])
                self.gardens = data.get("gardens",[])
                self.strategies = data.get("strategies",[])
                self.MQTTbroker = data["MQTTbroker"]
                self.port = data["port"]
                self.chatbotToken = data["chatbotToken"]
                self.services = data.get("services",[])

    def save_data(self):
        data = {"MQTTbroker": self.MQTTbroker, "port": self.port, "users": self.users,  "gardens": self.gardens, "devices": self.devices, "strategies": self.strategies, "chatbotToken": self.chatbotToken, "services": self.services}
        with open(self.data_file, "w") as file:
            json.dump(data, file)

    def GET(self, *uri):
        if len(uri) == 1 and str(uri[0]) == "getchatbottoken":
            return json.dumps(self.chatbotToken)
        else:
            return "Invalid URL construction."
    #.../updatechatbottoken/token
    def PUT(self, *uri):
        if len(uri) == 2 and str(uri[0]) == "updatechatbottoken":
            self.chatbotToken = uri[1]
            self.save_data()


if __name__ == "__main__":
    

    conf = {
        "/": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher(),
            "tools.sessions.on": True,
        }
    }
    web_service = users()
    web_service2 = devices()
    web_service3 = gardens()
    web_service4 = MQTTbroker()
    web_service5 = strategies()
    web_service6 = catalog()
    chatbot = bot()
    serviceWeb = services()
    updater = catalogUpdater()
    cherrypy.tree.mount(web_service, "/users", conf)
    cherrypy.tree.mount(web_service2,"/devices", conf)
    cherrypy.tree.mount(web_service3,"/gardens", conf)
    cherrypy.tree.mount(web_service4,"/mqtt", conf)
    cherrypy.tree.mount(web_service5,"/strategies", conf)
    cherrypy.tree.mount(web_service6,"/catalog", conf)
    cherrypy.tree.mount(chatbot,"/chatbot",conf)
    cherrypy.tree.mount(serviceWeb,"/services",conf)
    cherrypy.config.update({
        'server.socket_port': 8089,
        'server.socket_host': '0.0.0.0'  # Listen on all interfaces
    })
    cherrypy.engine.start()
    with open("configFile.json") as config_file:
            config = json.load(config_file)
    url = config["url"]+"registerservice"
    body = {"name": "catalogmanager",
            "endpoint": url}
    response = requests.post(url, data=body)
    cherrypy.engine.block()
    cherrypy.engine.exit()
    


    