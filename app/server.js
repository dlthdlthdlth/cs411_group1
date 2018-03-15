//server.js

const express = require('express');
const MongoClient = require('mongodb').MongoClient;
const bodyParser = require('body-parser');
const app = express();

const port = 8000;

//app.set('views', path.join(__dirname, 'views'));
//app.set('view engine', 'pug');
require('./routes')(app, {});
app.use('/', express.static('views'));

app.listen(port, () => {
	console.log('We are live on ' + port);
    });

module.exports = app;