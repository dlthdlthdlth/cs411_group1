//server.js

const express = require('express');
const MongoClient = require('mongodb').MongoClient;
const bodyParser = require('body-parser');
const path = require('path');
const app = express();

const port = 8000;

var searchresults = require('./routes/searchresults');

app.engine('pug', require('pug').__express)
app.set('views', path.join(__dirname, 'views'));
app.set('view engine', 'pug');
require('./routes')(app, {});

app.use(bodyParser.urlencoded({extended: false}));
app.use(bodyParser.json());

app.use('/', express.static('views'));
//app.use('/searchresults', searchresults);

app.listen(port, () => {
	console.log('We are live on ' + port);
    });


app.post('/searchresults', (req, res)  => {
  var term = req.body.search;
  res.send ("The search term is " +term )



  });

module.exports = app;
