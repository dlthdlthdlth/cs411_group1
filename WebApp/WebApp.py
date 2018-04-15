import flask
import requests
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import time
import flask.ext.login as flask_login
import json
import base64
import re
mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'still a secret'

# These will need to be changed according to your credentials, app will not run without a database
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'database_dude' #--------------CHANGE----------------
app.config['MYSQL_DATABASE_DB'] = 'fitbit'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)


#Fitbit api information
redirect_uri = "http://127.0.0.1:5000/callback"
client_id = "22CMVP" # ---------------CHANGE-----------------
client_secret = "7dea60be5733957b72a3ebc7859ee6d2" # ---------------CHANGE-----------------

#EventBrite api information
eventbrite_token = 'MHPPXZ3TBMC6E47PBCYK' # ---------------CHANGE-----------------

login_manager = flask_login.LoginManager()
login_manager.init_app(app)
conn = mysql.connect()

def getUserList():
    cursor = conn.cursor()
    cursor.execute("SELECT FBID FROM USER")
    return cursor.fetchall()

class User(flask_login.UserMixin):
    pass

@login_manager.user_loader
def user_loader(fbid):
    users = getUserList()
    if not (fbid) or fbid not in str(users):
        return

    cursor = conn.cursor()
    cursor.execute("SELECT ACCESS_TOKEN, REFRESH_TOKEN, NAME, LOCATION FROM USER WHERE FBID = '{0}'".format(fbid))
    data = cursor.fetchall()
    access_token = str(data[0][0])
    refresh_token = str(data[0][1])
    name = str(data[0][2])
    location = str(data[0][3])
    # Get a new access token if current one is expired
    if isExpired(access_token):
        new_tokens = refreshToken(fbid, access_token, refresh_token)
        access_token = new_tokens[0]
        refresh_token = new_tokens[1]

    user = User()
    user.id = fbid
    user.access_token = access_token
    user.refresh_token= refresh_token
    user.name = name
    user.location = location
    return user

# @login_manager.request_loader
# def request_loader(request):
#     users = getUserList()
#     email = request.form.get('fbid')
#     if not (email) or email not in str(users):
#         return
#     user = User()
#     user.id = email
#     cursor = mysql.connect().cursor()
#     cursor.execute("SELECT PASSWORD FROM USER WHERE EMAIL = '{0}'".format(email))
#     data = cursor.fetchall()
#     pwd = str(data[0][0])
#     user.is_authenticated = request.form['password'] == pwd
#     return user

@app.route('/login')
def login():
    url = "https://www.fitbit.com/oauth2/authorize?response_type=code&client_id="+ client_id + "&redirect_uri=" + redirect_uri + "&scope=activity%20location%20nutrition%20profile%20settings%20sleep%20social%20weight&expires_in=28800"
    return redirect(url)

#Gets access token once user has granted permission for the app to use Fitbit
@app.route('/callback', methods=['POST', 'GET'])
def callback():

    auth_header = client_id + ":" + client_secret
    encoded_auth_header = str((base64.b64encode(auth_header.encode())).decode('utf-8'))

    code = request.url.split("=")[1]
    url = "https://api.fitbit.com/oauth2/token"

    querystring = {"grant_type":"authorization_code","redirect_uri":redirect_uri,"clientId":client_id,"code": code}

    headers = {'Authorization': 'Basic '+ encoded_auth_header, 'Content-Type': "application/x-www-form-urlencoded"}

    response = requests.request("POST", url, headers=headers, params=querystring)

    response = json.loads(response.text)

    #Get the user's Fitbit id
    fbid = response['user_id']
    #Get access token to use Fitbit api
    access_token = response['access_token']
    #Get refresh token to refresh the access token once it expires
    refresh_token = response['refresh_token']

    users = getUserList()
    #If user hasn't logged into our app before
    if fbid not in str(users):
        registerUser(fbid, access_token, refresh_token)
        return flask.redirect(flask.url_for('register'))

    insertAccessToken(fbid, access_token)
    insertRefreshToken(fbid, refresh_token)
    user_name =  getUserName(fbid, access_token)

    #Create a user instance and log the user in
    user = User()
    user.id = fbid
    flask_login.login_user(user)

    return flask.redirect(flask.url_for('protected'))  # protected is a function defined in profile route


# If user has never logged into our app before
@app.route('/register', methods = ['POST', 'GET'])
@flask_login.login_required
def register():
    if flask.request.method == 'GET':
        return render_template('register.html')
    else:
        location=request.form.get('location') #or users could enter their location on search page, leaving it here as an example
        cursor = conn.cursor()
        cursor.execute("UPDATE USER SET LOCATION = '{0}' WHERE FBID = '{1}'".format(location,flask_login.current_user.id))
        conn.commit()
        return redirect(flask.url_for('protected'))


@app.route('/profile')
@flask_login.login_required
def protected():

    activities = getActivities()
    events = recommendEvents()

    return render_template('profile.html', name=flask_login.current_user.name, activities = activities, events = events)

#search events
#@flask_login.login_required
@app.route("/searchEvents", methods=['POST'])
def searchEventsRoute():
    results = searchEvents(flask.request.form['search_term'], flask_login.current_user.location)
    return render_template('searchEvents.html', results= results)


def searchEvents(search_term, location):
    url = "https://www.eventbriteapi.com/v3/events/search/"
    head = {'Authorization': 'Bearer {}'.format(eventbrite_token)}
    data = {"q": search_term, "sort_by": "date", "location.address": location, "categories":"108", "expand": "venue" } #108 is fitness category
    # city = flask.request.form['city']   ######    needs to be done later
    myResponse = requests.get(url, headers = head, params=data)
    results = []
    if(myResponse.ok):
        jData = json.loads(myResponse.text)
        events = jData['events']
        for event in events:
            name = event['name']['text']
            desc = event['description']['text']
            time = event['start']['local']
            venue = event['venue']['address']['address_1']

            results.append({"name":name, "desc": desc, "time":time, "venue":venue})
    else:
        # If response code is not ok (200), print the resulting http error code with description
        myResponse.raise_for_status()

    return results


@app.route("/", methods=['GET'])
def hello():
    return render_template('homepage.html')

@app.route('/logout')
def logout():
    flask_login.logout_user()
    return render_template('homepage.html', message='Logged out')

#Get username and store it in database
def getUserName(fbid, access_token):
    url = "https://api.fitbit.com/1/user/"+ fbid +"/profile.json"
    headers = {'Authorization': "Bearer " + access_token}
    response = requests.request("GET", url, headers=headers)
    response = json.loads(response.text)
    user_name = response['user']['displayName']
    cursor = conn.cursor()
    cursor.execute("UPDATE USER SET NAME = '{0}' WHERE FBID = '{1}'".format(user_name, fbid))
    conn.commit()
    return user_name

#get user past events, not finished
def pastEvents():
    cursor = conn.cursor()
    cursor.execute("SELECT ENAME, TYPE, INFO, DATE, TIME, LOCATION FROM PASTEVENTS WHERE UID='{0}'".format())
    return

#get user future events
def futureEvents():
    return

#get user saved events
def savedEvents():
    return

#get fitbit activities
def getActivities():
    url = "https://api.fitbit.com/1/user/"+ flask_login.current_user.id +"/activities/list.json?afterDate=2005-01-01&sort=desc&limit=20&offset=0"
    headers = {'Authorization': "Bearer " + flask_login.current_user.access_token}
    response = requests.request("GET", url, headers=headers)
    # print (response.headers)
    response = json.loads(response.text)

    activities = []

    cursor = conn.cursor()
    for activity in response['activities']:
        activities.append(activity['activityName'])
        cursor.execute("INSERT INTO ACTIVITIES (FBID, ACTIVITY) VALUES ('{0}', '{1}') ON DUPLICATE KEY UPDATE ACTIVITY=ACTIVITY;".format(flask_login.current_user.id, activity['activityName']))
    conn.commit()
    return activities

#needs to be implemented
def recommendEvents():
    cursor = conn.cursor()
    cursor.execute("SELECT FBID, ACTIVITY FROM ACTIVITIES WHERE FBID = '{0}'".format(flask_login.current_user.id))
    data = cursor.fetchall()
    events = []
    #call searchEvents() with each of the user's activities
    for index in range(len(data)):
        activity = str(data[index][1])
        event = searchEvents(activity, flask_login.current_user.location)
        events.append(event)

    #flatten the 2D array into a 1D array
    events = [event for category in events for event in category]

    return events

@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('unauth.html')

def registerUser(fbid, access_token, refresh_token):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO USER (FBID) VALUES ('{0}')".format(fbid))
    conn.commit()
    insertAccessToken(fbid,access_token)
    insertRefreshToken(fbid, refresh_token)
    user_name = getUserName(fbid, access_token)

    #Create a user instance and log the user in
    user = User()
    user.id = fbid
    flask_login.login_user(user)


def insertAccessToken(fbid, access_token):
    cursor = conn.cursor()
    cursor.execute("UPDATE USER SET ACCESS_TOKEN = '{0}' WHERE FBID = '{1}'".format(access_token, fbid))
    conn.commit()

def insertRefreshToken(fbid, refresh_token):
    cursor = conn.cursor()
    cursor.execute("UPDATE USER SET REFRESH_TOKEN = '{0}' WHERE FBID = '{1}'".format(refresh_token, fbid))
    conn.commit()

#Checks state of current access token by making a call to the Fitbit api
def isExpired(access_token):
    headers = {
    'accept': 'application/json',
    'content-type': 'application/x-www-form-urlencoded',
    'Authorization': 'Bearer ' + access_token,
    }
    data = [
      ('token', access_token),
    ]
    response = requests.post('https://api.fitbit.com/oauth2/introspect', headers=headers, data=data)

    response = str(response.content.decode("utf-8"))
    response = re.sub('^[^{]*', '', response)

    response = json.loads(response)

    if 'active' not in response:
        return True
    else:
        return False

#Refresh the access token and store new access token and refresh token in database
def refreshToken(fbid, access_token, refresh_token):

    auth_header = client_id + ":" + client_secret
    encoded_auth_header = str((base64.b64encode(auth_header.encode())).decode('utf-8'))

    url = "https://api.fitbit.com/oauth2/token"
    querystring = {"grant_type":"refresh_token","refresh_token": refresh_token, "expires_in": 28800}
    headers = {'Authorization': 'Basic '+ encoded_auth_header, 'Content-Type': "application/x-www-form-urlencoded"}

    response = requests.request("POST", url, headers=headers, params=querystring)
    response = json.loads(response.text)

    access_token = response['access_token']
    refresh_token = response['refresh_token']

    insertAccessToken(fbid, access_token)
    insertRefreshToken(fbid, refresh_token)

    return [access_token, refresh_token]


if __name__ == '__main__':
    app.run(port=5000, debug=True)
