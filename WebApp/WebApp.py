import flask
import requests
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import time
import flask.ext.login as flask_login
import json

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'still a secret'

# These will need to be changed according to your creditionals, app will not run without a database
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'change'
app.config['MYSQL_DATABASE_DB'] = 'fitbit'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#code used for login
#will be changed to use fitbit login api
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

#api search call
url = "https://www.eventbriteapi.com/v3/events/search/"
myToken = 'replace and delete'
head = {'Authorization': 'Bearer {}'.format(myToken)}
data = {"q": ""}

#example code/do not delete
conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT EMAIL FROM USER")
users = cursor.fetchall()

#ignore/don't delete
def getUserList():
    cursor = conn.cursor()
    cursor.execute("SELECT EMAIL FROM USER")
    return cursor.fetchall()

#ignore/don't delete
class User(flask_login.UserMixin):
    pass

#ignore/don't delete
@login_manager.user_loader
def user_loader(email):
    users = getUserList()
    if not (email) or email not in str(users):
        return
    user = User()
    user.id = email
    return user

#ignore/don't delete
@login_manager.request_loader
def request_loader(request):
    users = getUserList()
    email = request.form.get('email')
    if not (email) or email not in str(users):
        return
    user = User()
    user.id = email
    cursor = mysql.connect().cursor()
    cursor.execute("SELECT PASSWORD FROM USER WHERE EMAIL = '{0}'".format(email))
    data = cursor.fetchall()
    pwd = str(data[0][0])
    user.is_authenticated = request.form['password'] == pwd
    return user

#login route needs to be changed, but logic may be similar.
@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method != 'POST':
        return render_template('login.html', message='Login')
    else:
        # The request method is POST (page is recieving data)
        email = flask.request.form['email']
        cursor = conn.cursor()
        # check if email is registered
        if cursor.execute("SELECT PASSWORD FROM USER WHERE EMAIL= '{0}'".format(email)):
            data = cursor.fetchall()
            pwd = str(data[0][0])
            if flask.request.form['password'] == pwd:
                user = User()
                user.id = email
                flask_login.login_user(user)  # okay login in user
                return flask.redirect(flask.url_for('protected'))  # protected is a function defined in this file

        # information did not match
        return render_template('login.html', message="Incorrect Username or Password, please try again")

#log out function, needs to be changed
@app.route('/logout')
def logout():
    flask_login.logout_user()
    return render_template('homepage.html', message='Logged out')

#unathorized
@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('unauth.html')

#user profile
@app.route('/profile')
#@flask_login.login_required
def protected():
    return render_template('profile.html')

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
    myResponse = requests.get(url, headers = head, params=data)
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

#Default route
@app.route("/", methods=['GET'])
def hello():
    return render_template('homepage.html')


if __name__ == '__main__':
    app.run(port=5000, debug=True)

