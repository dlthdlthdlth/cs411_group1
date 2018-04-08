import flask
import requests
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import time
import flask.ext.login as flask_login
import json
import base64

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
eventbrite_url = "https://www.eventbriteapi.com/v3/events/search/"
myToken = '' # ---------------CHANGE-----------------
head = {'Authorization': 'Bearer {}'.format(myToken)}
data = {"q": ""}

login_manager = flask_login.LoginManager()
login_manager.init_app(app)
conn = mysql.connect()

session = {}

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
    user = User()
    user.id = fbid
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
    url = "https://www.fitbit.com/oauth2/authorize?response_type=code&client_id="+ client_id + "&redirect_uri=" + redirect_uri + "&scope=activity%20location%20nutrition%20profile%20settings%20sleep%20social%20weight&expires_in=604800"
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


    access_token = response['access_token']
    session['access_token'] = access_token

    refresh_token = response['refresh_token']
    session['refresh_token'] = refresh_token

    fbid = response['user_id']
    users = getUserList()
    if fbid not in str(users):
        cursor = conn.cursor()
        cursor.execute("INSERT INTO USER (FBID) VALUES ('{0}')".format(fbid))
        conn.commit()
        return flask.redirect(flask.url_for('register'))

    user = User()
    user.id = fbid
    flask_login.login_user(user)
    session['access_token'] = access_token

    return flask.redirect(flask.url_for('protected'))  # protected is a function defined in profile route
    #return render_template('test.html', message="You're logged in with Fitbit!")


# If user has never logged into our app before
@app.route('/register', methods = ['POST', 'GET'])
@flask_login.login_required
def register():
    if flask.request.method == 'GET':
        return render_template('register.html')
    else:
        location=request.form.get('location') #or users could enter their location on search page, leaving it here as an example
        print (location)
        cursor = conn.cursor()
        cursor.execute("UPDATE USER SET LOCATION = '{0}' WHERE FBID = '{1}'".format(location,flask_login.current_user.id))
        conn.commit()
        return redirect(flask.url_for('protected'))


@app.route('/profile')
@flask_login.login_required
def protected():
    #Check if user has access token before making api call to fitbit
    if (session.get('access_token', None)):
        print (session.get('access_token', None))
        url = "https://api.fitbit.com/1/user/"+ flask_login.current_user.id +"/profile.json"

        access_token = session.get('access_token', None)
        headers = {'Authorization': "Bearer " + access_token}

        response = requests.request("GET", url, headers=headers)

        response = json.loads(response.text)

        flask_login.current_user.name = response['user']['displayName']

        return render_template('profile.html', name=flask_login.current_user.name)
    #Redirect user to login if they don't have access token
    else:
        return render_template('unauth.html')


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return render_template('homepage.html', message='Logged out')


@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('unauth.html')

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
def fitbitactivities():
    return

#needs to be implemented
#@flask_login.login_required
def recommend():
   return

#search events
@app.route("/searchEvents", methods=['POST'])
#@flask_login.login_required
def searchEvents():
    event = flask.request.form['event']
    # city = flask.request.form['city']   ######    needs to be done later
    data['q'] = event
    myResponse = requests.get(eventbrite_url, headers = head, params=data)
    results = []
    if(myResponse.ok):
        jData = json.loads(myResponse.text)
        events = jData['events']
        for event in events:
            temp = event['name']
            temp = temp['text']
            temp2 = event['description']
            temp2 = temp2['text']
            results.append((temp, temp2))

    else:
        # If response code is not ok (200), print the resulting http error code with description
        myResponse.raise_for_status()

    return render_template('searchEvents.html', results= results)


@app.route("/", methods=['GET'])
def hello():
    return render_template('homepage.html')




if __name__ == '__main__':
    app.run(port=5000, debug=True)
