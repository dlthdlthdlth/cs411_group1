var express = require('express');
var router = express.Router();
const request = require("request");


const eventbriteToken = 'MHPPXZ3TBMC6E47PBCYK';

//Search for an event
router.post('/', (req, res)  => {
  var term = req.body.search;
  console.log(term);
  var options = { method: 'GET',
    url: 'https://www.eventbriteapi.com/v3/events/search/',
    qs: { q: term, token: eventbriteToken }};

  request(options, function (error, response, body) {
    if (error) throw new Error(error);

    var response = body;
    response = JSON.parse(response);
    var events = response.events;

    // var eventDict = {};
    //
    // for (var i = 0; i < events.length; i++){
    //   var eventName = events[i].name.text;
    //   eventDict[eventName] =  events[i].description.text;
    // }

    res.render('searchResults', { term: term, events: events});
  });

});

module.exports = router;
