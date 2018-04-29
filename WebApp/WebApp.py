import flask
import requests
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import time
import flask.ext.login as flask_login
import json
import base64
import re
from datetime import datetime, timedelta
mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'still a secret'

# These will need to be changed according to your credentials, app will not run without a database
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = '' #--------------CHANGE----------------
app.config['MYSQL_DATABASE_DB'] = 'fitbit'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#Fitbit api information
redirect_uri = "http://127.0.0.1:5000/callback"
client_id = "" # ---------------CHANGE-----------------
client_secret = "" # ---------------CHANGE-----------------

#EventBrite api information
eventbrite_token = '' # ---------------CHANGE-----------------

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
        return render_template('register.html', name = flask_login.current_user.name)
    else:
        location=request.form.get('location') #or users could enter their location on search page, leaving it here as an example
        cursor = conn.cursor()
        cursor.execute("UPDATE USER SET LOCATION = '{0}' WHERE FBID = '{1}'".format(location,flask_login.current_user.id))

        return redirect(flask.url_for('protected'))

#user profile route
@app.route('/profile', methods=['GET', 'POST'])
@flask_login.login_required
def protected():
    activities = getActivities()
    if flask.request.method == 'GET':
        events = recommendEvents(activities)
        insertActivities(activities)
        return render_template('profile.html', name=flask_login.current_user.name, activities = activities, location = flask_login.current_user.location, events = events)
    else:
        if flask.request.form['change-location'] != '':
            location = flask.request.form['change-location']
            emptyRecommendations()
        else:
            location = flask_login.current_user.location
        print (location)

        datekey = flask.request.form['datekey']
        radius = flask.request.form['radius']
        flask_login.current_user.location = location

        events = recommendEvents(activities, datekey, radius)
        insertActivities(activities)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE USER SET LOCATION = '{0}' WHERE FBID = '{1}'".format(location, flask_login.current_user.id))
        return render_template('profile.html', name=flask_login.current_user.name, activities=activities,
                               location=location, events=events)

#search events
#@flask_login.login_required
@app.route("/searchEvents", methods=['POST'])
def searchEventsRoute():
    cursor = conn.cursor()
    #check results cache for term given.
    search_term = flask.request.form['search_term']
    location_term = flask.request.form['city']
    dateKey = flask.request.form['datekey']
    radius = flask.request.form['radius']

    cursor.execute("SELECT NAME, DATE, VENUE, DES, LINK, IS_FREE, RNUM FROM RESULTCACHE WHERE SID = '{0}' AND LOCATION_TERM = '{1}'".format(search_term, location_term))
    events = cursor.fetchall()
    events = [{"name": str(events[i][0]), "date": str(events[i][1]), "venue": str(events[i][2]), "desc": str(events[i][3]), "link": str(events[i][4]), "is_free":str(events[i][5]), "search_term":search_term, "location_term":location_term, "resNum": i } for i in range(len(events))]
    if(events):
        #results found, return them.
        #print("CACHE PULL")
        deleteOldResults()
        if flask_login.current_user.is_authenticated:
            return render_template('searchEvents.html', events= events, name= flask_login.current_user.name)
        else:
            return render_template('searchEvents.html', events= events, message="Here Are Your Search Results!")

    else:
        # get first instance of search results

        if(dateKey == 'all' and radius == ''):
            events = searchEvents(flask.request.form['search_term'], location_term=flask.request.form['city'])
        else:
            events = searchEvents(flask.request.form['search_term'], location_term=flask.request.form['city'], dateKey= dateKey, radius=radius)

        events = [{"name":events[i][0], "date":reformatDate(events[i][1]), "venue":events[i][2], "desc":events[i][3], "link":events[i][4], "is_free": events[i][5], "search_term":events[i][6], "resNum": i, "location_term": str(events[i][7])} for i in range(len(events))]
        #insert search results into the cache.
        #print("api call")
        for event in events:
            cursor.execute("INSERT INTO RESULTCACHE (SID, NAME, DATE, VENUE, DES, LINK, IS_FREE, RNUM, LOCATION_TERM) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}', '{8}')".format(search_term, event["name"], event["date"], event["venue"], event["desc"], event["link"], event["is_free"], event["resNum"], location_term))
        conn.commit()
        #delete old results
        deleteOldResults()
        if flask_login.current_user.is_authenticated:
            return render_template('searchEvents.html', events= events, name= flask_login.current_user.name)
        else:
            return render_template('searchEvents.html', events= events)

#helper function
def searchcount():
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT SID), COUNT(DISTINCT LOCATION_TERM) FROM RESULTCACHE")
    count = cursor.fetchall()[0]
    return count

#deletes old results from results cache if more than 5 searches have occured.
def deleteOldResults():
    count = searchcount()
    if(count[0] > 5 or count[1] > 5):
        #get SID of first record in cache.
        cursor = conn.cursor()
        cursor.execute("SELECT SID FROM RESULTCACHE ORDER BY ID LIMIT 1")
        sid = cursor.fetchall()[0][0]
        #remove all results matching sid
        cursor.execute("DELETE FROM RESULTCACHE WHERE SID = '{0}'".format(sid))
        conn.commit()

#search events api call
def searchEvents(search_term, location_term, dateKey='', radius=''):
    url = "https://www.eventbriteapi.com/v3/events/search/"
    head = {'Authorization': 'Bearer {}'.format(eventbrite_token)}
    key = dateKey
    data = {}
    if (key == 'all'):
        key = ''
    if dateKey != '' and radius != '':
        data = {"q": search_term, "sort_by": "date", "location.address": location_term ,"categories":"108", "expand": "venue","location.within": radius + "mi", "start_date.keyword": key} #108 is fitness category
    elif dateKey != '':
        data = {"q": search_term, "sort_by": "date", "location.address": location_term ,"categories":"108", "expand": "venue",  "start_date.keyword": key}
    elif radius != '':
        data = {"q": search_term, "sort_by": "date", "location.address": location_term ,"categories":"108", "expand": "venue","location.within": radius + "mi"}
    else:
        data = {"q": search_term, "sort_by": "date", "location.address": location_term ,"categories":"108", "expand": "venue"}
    myResponse = requests.get(url, headers = head, params=data)
    results = []
    if(myResponse.ok):
        jData = json.loads(myResponse.text)
        events = jData['events']
        for event in events:
            #format the strings for the database
            name = event['name']['text']
            name =reformatString(name)

            date = event['start']['local']

            if (event['venue'] == None or event['venue']['address'] == None or event['venue']['address']['address_1'] == None):
                venue = "Venue in description."
            else:
                venue  = event['venue']['address']['address_1']
                venue = reformatString(venue)

            if (event['description'] == None or event['description']['text'] == None):
                desc = "No description provided."
            else:
                desc = event['description']['text']
                desc = reformatString(desc)

            eventbrite_link = event['url']

            is_free = str(event['is_free'])

            results.append((name, date, venue, desc, eventbrite_link, is_free, search_term, location_term))
    else:
        # If response code is not ok (200), print the resulting http error code with description
        myResponse.raise_for_status()

    return results

@app.route("/", methods=['GET'])
def hello():
    if flask_login.current_user.is_authenticated:
        return flask.redirect(flask.url_for('protected'))
    else:
        return render_template('homepage.html')

@app.route("/searchPage", methods=['GET'])
def searchPage():
    if flask_login.current_user.is_authenticated:
        return render_template('homepage.html', name= flask_login.current_user.name)
    else:
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

    return user_name

#save user events
@app.route('/saveEvent', methods=["POST"])
@flask_login.login_required
def saveEvent():
    cursor = conn.cursor()
    resnum = flask.request.form["name"]
    cursor.execute("SELECT SID, NAME, DATE, VENUE, DES, LINK FROM RESULTCACHE WHERE RNUM = '{0}'".format(resnum))
    event = cursor.fetchall()[0]
    #check if saved event already exists
    cursor.execute("SELECT LINK FROM SAVEDEVENTS WHERE LINK = '{0}'".format(event[5]))
    if (cursor.fetchall()):
        return render_template('savedEvents.html', message="Event already saved", events=getSearchSaved(),
                               name=flask_login.current_user.name)
    # reformat strings to avoid database errors.
    else:
        name = event[1]
        name = reformatString(name)

        date = event[4]
        date = reformatString(date)

        fbid = flask_login.current_user.id
        cursor.execute("INSERT INTO SAVEDEVENTS (FBID, SID, NAME, DATE, VENUE, DES, LINK, IS_FREE) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}')".format(fbid, event[0], name, event[2], event[3], date, event[5], event[6]))
        conn.commit()
        return render_template('savedEvents.html', events=getSearchSaved())

#get user saved events
@app.route('/savedEvents', methods=["GET"])
@flask_login.login_required
def getSavedEvents():
    fbid = flask_login.current_user.id
    cursor = conn.cursor()
    cursor.execute("SELECT NAME, DATE, VENUE, DES, LINK, IS_FREE FROM SAVEDEVENTS WHERE FBID = '{0}'".format(fbid))
    events = cursor.fetchall()
    events = [{"name": str(events[i][0]), "date": str(events[i][1]), "venue": str(events[i][2]), "desc": str(events[i][3]), "link": str(events[i][4]), "is_free":str(events[i][5]),  "resNum": i } for i in range(len(events))]
    return render_template('savedEvents.html', events= events)

#helper function for search events saved
@flask_login.login_required
def getSearchSaved():
    fbid = flask_login.current_user.id
    cursor = conn.cursor()
    cursor.execute("SELECT  NAME, DATE, VENUE, DES, LINK, IS_FREE FROM SAVEDEVENTS WHERE FBID = '{0}'".format(fbid))
    events = cursor.fetchall()
    events = [{"name": str(events[i][0]), "date": str(events[i][1]), "venue": str(events[i][2]), "desc": str(events[i][3]), "link": str(events[i][4]), "is_free": str(events[i][5]), "resNum": i } for i in range(len(events))]
    return events

#get fitbit activities
def getActivities():
    url = "https://api.fitbit.com/1/user/"+ flask_login.current_user.id +"/activities/list.json?afterDate=2005-01-01&sort=desc&limit=20&offset=0"
    headers = {'Authorization': "Bearer " + flask_login.current_user.access_token}
    response = requests.request("GET", url, headers=headers)
    response = json.loads(response.text)

    activities = []

    cursor = conn.cursor()
    for activity in response['activities']:
        activities.append(activity['activityName'])
    return activities

def insertActivities(activities):
    cursor = conn.cursor()
    for activity in activities:
        cursor.execute("INSERT INTO ACTIVITIES (FBID, ACTIVITY) VALUES ('{0}', '{1}') ON DUPLICATE KEY UPDATE ACTIVITY=ACTIVITY;".format(flask_login.current_user.id, activity))
    conn.commit()
    return


def recommendEvents(api_activities, datekey='all', radius=''):
    #fill the table with new events
    cursor = conn.cursor()
    cursor.execute("SELECT ACTIVITY FROM ACTIVITIES WHERE FBID = '{0}'".format(flask_login.current_user.id))
    db_activities = cursor.fetchall()
    db_activities = [str(db_activities[index][0]) for index in range(len(db_activities))]

    print ("radius: " + radius)
    print ("datekey: " + datekey)

    #if activity list hasn't changed, load recommended events from the cache
    if  db_activities != [] and set(api_activities) == set(db_activities):
        cursor.execute("SELECT TIME_MODIFIED FROM RECOMMENDATIONS WHERE FBID = '{0}' LIMIT 1".format(flask_login.current_user.id))
        if cursor.rowcount != 0:
            time_modified = cursor.fetchall()[0][0]
            now = datetime.now()
            now_minus_10 = now - timedelta(minutes = 10)
            #if its been less than 10 minutes since the recommended events were updated, pull from cache
            if time_modified > now_minus_10:
                cursor.execute("SELECT SID, NAME, DATE, VENUE, DES, LINK, IS_FREE, DATE_KEY, RADIUS FROM RECOMMENDATIONS WHERE FBID = '{0}' AND DATE_KEY = '{1}' AND RADIUS = '{2}'".format(flask_login.current_user.id, datekey, radius))
                events = cursor.fetchall()
                if cursor.rowcount != 0:
                    events = [{"name": str(events[i][1]), "date": str(events[i][2]), "venue": str(events[i][3]), "desc": str(events[i][4]), "link": str(events[i][5]), "is_free": str(events[i][6]), "search_term": str(events[i][0]), "resNum": i } for i in range(len(events))]
                    print ("pulling from cache")
                    return events

    #empty the cache of recommended events and call searchEvents() with each of the user's activities
    emptyRecommendations()
    events = []
    for activity in api_activities:
        event = searchEvents(activity, flask_login.current_user.location, dateKey= datekey, radius= radius)
        events.append(event)

    #flatten the 2D array into a 1D array
    events = [event for category in events for event in category]

    #sort events by date
    events = sorted(events, key=lambda x: x[1])

    #Put date in readable format
    events = [{"name":events[i][0], "date":reformatDate(events[i][1]), "venue":events[i][2], "desc":events[i][3], "link":events[i][4], "is_free":events[i][5], "search_term":events[i][6], "resNum": i} for i in range(len(events))]
    #insert events into table
    for event in events:
        cursor.execute("INSERT INTO RECOMMENDATIONS (FBID, SID, NAME, DATE, VENUE, DES, LINK, IS_FREE, DATE_KEY, RADIUS, RNUM) VALUES ('{0}','{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}', '{8}', '{9}', '{10}') ON DUPLICATE KEY UPDATE RNUM=RNUM".format( flask_login.current_user.id, event["search_term"], event["name"], event["date"], event["venue"], event["desc"], event["link"], event["is_free"], datekey, radius, event["resNum"]))
    conn.commit()
    return events

def emptyRecommendations():
    cursor = conn.cursor()
    cursor.execute("DELETE FROM RECOMMENDATIONS WHERE FBID = '{0}'".format(flask_login.current_user.id))
    conn.commit()

#save user events
@app.route('/saveEventRecommendations', methods=["POST"])
@flask_login.login_required
def saveEventRecommendations():
    cursor = conn.cursor()
    resnum = flask.request.form["name"]
    cursor.execute("SELECT NAME, DATE, VENUE, DES, LINK, IS_FREE FROM RECOMMENDATIONS WHERE RNUM = '{0}'".format(resnum))
    event = cursor.fetchall()[0]
    #check if saved event is already in table
    cursor.execute("SELECT LINK FROM SAVEDEVENTS WHERE LINK = '{0}'".format(event[4]))
    activities = getActivities()
    if(cursor.fetchall()):
        return render_template('profile.html', message= "Event already saved", events=recommendEvents(activities), name= flask_login.current_user.name, activities = activities)
    #reformat strings to avoid database errors.
    else:
        name = event[0]
        name = reformatString(name)

        date = event[3]
        date = reformatString(date)

        fbid = flask_login.current_user.id
        cursor.execute(
            "INSERT INTO SAVEDEVENTS (FBID, NAME, DATE, VENUE, DES, LINK, IS_FREE) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format(
                fbid, name, event[1], event[2], date, event[4], event[5]))
        conn.commit()
        return render_template('savedEvents.html', events=getRecSaved())

#helper function for recommendations saved
@flask_login.login_required
def getRecSaved():
    fbid = flask_login.current_user.id
    cursor = conn.cursor()
    cursor.execute("SELECT NAME, DATE, VENUE, DES, LINK, IS_FREE FROM SAVEDEVENTS WHERE FBID = '{0}'".format(fbid))
    events = cursor.fetchall()
    events = [{"name": str(events[i][0]), "date": str(events[i][1]), "venue": str(events[i][2]), "desc": str(events[i][3]), "link": str(events[i][4]), "is_free":str(events[i][5]), "resNum": i } for i in range(len(events))]
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


##Formatting functions
# Dates from EventBrite api are in the format '2018-04-21T13:00:00'. reformatDate() turns it into
# 'April 21 at 1:00PM'
def reformatDate(date):
    new_date = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')
    new_date = new_date.strftime("%B %-d at %-I:%M%p")
    #print(new_date[-1])
    return new_date

#escape single quotes to insert into mysql
def reformatString(text):
    text = list(text)
    for char in range(len(text)):
        if(text[char] == "'"):
            text[char] = "''"
    text= "".join(text)
    return text

if __name__ == '__main__':
    app.run(port=5000, debug=True)
