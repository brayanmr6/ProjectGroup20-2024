#  Programming for IoT applications - Project
# Webpage

# This service has a functionality support the user awareness area in cooperation with the Telegram Bot,
# we exploit the library Flask in order to run a webpage locally supported on some HTML templates. 
# At the beginning it basically displays a log-in menu, where the USER must enter the username and password 
# that was registered at the SRcatalog script, there's a GET request to the mentioned webservice and the data entered is then
# compared and, if valid, three operations can be done:

# - Display the gardens that the user own
# - Display the measurements retrieved by all the sensors that the garden possesses
# - Retrieve plots from the gardens.

# The first function calls once again a GET request to SRcatalog webservice, to be more specific it exploits the garden class.
# The second one performes a GET request to the thingspeakadaptor web service, let's remember that the measurements published by the
# device connector can be retrieved with a GET request like this: http://thingspeakadaptor:8087/messages/getmessages
# And finally, the last function is performed by accessing to the Thingspeak API and retrieving the data points that are stored there
# in order to do that we need channel ID, readAPIkey, those 2 values at this point should had already been inputed at the Telegram chatbot
# script, and as a matter of fact, the webpage just does a GET request to http://telegramchatbot:8085/channelandreadapikey/...
# to get them and continue with the plotting functions.

import matplotlib
matplotlib.use("Agg")
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import requests
import json
import os
import matplotlib.pyplot as plt
from flask import send_file

app = Flask(__name__)
app.secret_key = "..."

# Check if user was logged-in
def is_logged_in():
    return "username", "userID" in session


@app.route("/login", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        route = "configFile.json"
        with open(route, "r") as config_file:
            configFile = json.load(config_file)
        url = configFile["getUsers"]
        
        username = request.form["username"]
        password = request.form["password"]
        
        response = requests.get(url)
        
        if response.status_code == 200:
            users = response.json()
            for user in users:
                if user["username"] == username and user["password"] == password:
                    session["username"] = username
                    session["userID"] = user["userID"]
                    return redirect(url_for("menu"))
            else:
                return "Invalid username or password"
        else:
            return "Failed to fetch user data"
    return render_template("login.html")


@app.route("/menu")
def menu():
    if not is_logged_in():
        return redirect(url_for("index"))
    return render_template("menu.html")


@app.route("/see_my_gardens", methods=["GET", "POST"])
def see_my_gardens():
    if not is_logged_in():
        return redirect(url_for("index"))
    
    username = session["username"]
    userID = session["userID"]  
    
   
    route = "configFile.json"
    with open(route, "r") as config_file:
        configFile = json.load(config_file)
    url = configFile["getGardensUser"].format(user=userID) 
    response = requests.get(url)
    
    if response.status_code == 200:
        gardens = response.json()
        pretty_gardens = json.dumps(gardens, indent=4)
        return "<pre>" + pretty_gardens + "</pre>"
    else:
        return "Failed to fetch gardens"

@app.route("/see_last_measurements", methods=["GET", "POST"])
def see_last_measurements():
    if not is_logged_in():
        return redirect(url_for("index"))

    username = session["username"]
    userID = session["userID"]  
    route = "configFile.json"
    with open(route, "r") as config_file:
        configFile = json.load(config_file)
    urlGardens = configFile["getGardensUser"].format(user=userID) 
    urlMessages = configFile["getMessages"]

    gardens_response = requests.get(urlGardens)
    
    if gardens_response.status_code == 200:
        gardens = gardens_response.json()
        garden_ids = [garden["gardenID"] for garden in gardens]
        print(garden_ids)
        
        garden_id = int(request.form.get("garden_id")) 
        print(garden_id)

        if garden_id not in garden_ids:
            return "Error, invalid garden ID! You must enter the ID of a garden you own."
        
            
        messages_response = requests.get(urlMessages)      
        if messages_response.status_code == 200:
            
            messages = messages_response.json()
            measurements = []
            for message in messages:
                if garden_id == message["gardenID"]:
                    measurements.append(message)
            return json.dumps(measurements)
        else:
            return "Failed to fetch messages"
    else:
        return "Failed to fetch gardens"


@app.route("/see_plots", methods=["POST"])
def see_plots():
    if not is_logged_in():
        return redirect(url_for("index"))


    garden_id = int(request.form.get("garden_id"))
    route = "configFile.json"
    with open(route, "r") as config_file:
        config = json.load(config_file)
    urlGardens = config["getGardensUser"].format(user=session["userID"])
    gardens_response = requests.get(urlGardens)

    if gardens_response.status_code == 200:
        gardens = gardens_response.json()
        garden_ids = [garden["gardenID"] for garden in gardens]
        if garden_id not in garden_ids:
            return "Error, invalid garden ID! You must enter the ID of a garden you own."

    urlChannelsAndReadAPI = config["getChannelsAndAPIKeys"]
    channelsAndReadApisrequest = requests.get(urlChannelsAndReadAPI)
    channelsAndReadAPIKeys = channelsAndReadApisrequest.json()
    
    channelID = "channel_" + str(garden_id)
    if channelID in channelsAndReadAPIKeys:
        channelIDValue = channelsAndReadAPIKeys[channelID]
        baseURL = config["base_url"].format(channel_id=channelIDValue)
    apiKeyName = "readkey_" + str(garden_id)
    if apiKeyName in channelsAndReadAPIKeys:
        apiKeyValue = channelsAndReadAPIKeys[apiKeyName]
        url = config["URL"].format(base_url=baseURL, api_key=apiKeyValue)

    # GET request to the URL to retrieve the data points
    response = requests.get(url)
    if response.status_code == 200:
        #self.bot.sendMessage(self.chatID, text= "holaa gato")
        data = response.json()
        #Navigating through the data obtained from the GET request to the thingspeak channel we can set the information   
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

        def create_plot(measurements, timestamps, ylabel, save_dir):
            try:
                if measurements:
                    plt.figure(figsize=(8, 6))
                    plt.plot(timestamps, measurements, marker="o", linestyle="-")
                    plt.xlabel("Time")
                    plt.ylabel(ylabel)
                    plt.title(ylabel)
                    os.makedirs(save_dir, exist_ok=True)
                    plot_name = f"{ylabel.lower().replace(' ', '_')}_plot.png"
                    image_path = os.path.join(save_dir, plot_name)
                    plt.savefig(image_path)
                    plt.close()
                    return image_path


            except Exception as e:
                print("Error:", e)

        plots_dir = os.path.join(app.root_path, "static", "plots")
        temperature_plot_path = create_plot(temperatureMeasurements, temperatureTimestamps, "Temperature", plots_dir)
        humidity_plot_path = create_plot(humidityMeasurements, humidityTimestamps, "Humidity", plots_dir)
        ph_plot_path = create_plot(phMeasurements, phTimestamps, "pH", plots_dir)
        light_plot_path = create_plot(lightMeasurements, lightTimestamps, "Light", plots_dir)
        print("Temperature plot path:", temperature_plot_path)
        print("Humidity plot path:", humidity_plot_path)
        print("pH plot path:", ph_plot_path)
        print("Light plot path:", light_plot_path)

        # Filter out None plot paths
        plot_paths = [path for path in [temperature_plot_path, humidity_plot_path, ph_plot_path, light_plot_path] if path is not None]
        plot_names = [os.path.basename(path) for path in plot_paths]
        return render_template("plots.html",
                            temperature_plot=plot_names[0] if len(plot_names) > 0 else None,
                            humidity_plot=plot_names[1] if len(plot_names) > 1 else None,
                            ph_plot=plot_names[2] if len(plot_names) > 2 else None,
                            light_plot=plot_names[3] if len(plot_names) > 3 else None)

    return "Work in progress - Plots for Garden ID: {}".format(garden_id)

@app.route("/static/plots/<plot_name>")
def serve_plot(plot_name):
    return send_file(f"static/plots/{plot_name}")

if __name__ == "__main__":
    with open("configFile.json", "r") as config_file:
                config = json.load(config_file)
    url = config["registerService"]
    body = {"name": "webpage",
            "endpoint": "http://webpage:8083/"}
    response = requests.post(url, json=body)
    app.run(host="0.0.0.0", port=8083, debug=True)
