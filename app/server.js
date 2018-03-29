//server.js

const express = require('express');
const MongoClient = require('mongodb').MongoClient;
const bodyParser = require('body-parser');
const request = require("request");
const path = require('path');
const app = express();

const port = 8000;


app.engine('pug', require('pug').__express)
app.set('views', path.join(__dirname, 'views'));
app.set('view engine', 'pug');
require('./routes')(app, {});

app.use(bodyParser.json());
app.use(bodyParser.urlencoded({extended: true}));
//app.use('/', express.static('views'));

app.get('/', function (req, res) {

	//render the 'index' template
	res.render('index');

    });

app.listen(port, () => {
	console.log('We are live on ' + port);
    });



module.exports = app;
