//server.js

const express = require('express');
const app = express();
const MongoClient = require('mongodb').MongoClient;
const bodyParser = require('body-parser');
const request = require("request");
const path = require('path');
const port = 8000;
const searchResults = require('./routes/searchResults');
const index = require('./routes/index');

app.engine('pug', require('pug').__express)
app.set('views', path.join(__dirname, 'views'));
app.set('view engine', 'pug');
//require('./routes')(app, {});

app.use(bodyParser.json());
app.use(bodyParser.urlencoded({extended: false}));
app.use('/searchResults', searchResults);

//app.use('/', express.static('views'));
app.use('/', index);


app.listen(port, () => {
	console.log('We are live on ' + port);
    });


module.exports = app;
