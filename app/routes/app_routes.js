const bodyParser = require('body-parser');

const request = require("request");
const eventbriteToken = 'Anonymous OAuth Token';


module.exports = function(app, db){
    app.post('/app', (req, res) => {
	    //post method
	    res.send('Hello')
	});
};


//Search for an event
module.exports = function(app, db){
  app.use(bodyParser.json());
  app.use(bodyParser.urlencoded({extended: true}));
  app.post('/searchresults', (req, res)  => {
    console.log(req.body);
    var term = req.body.search;
    var options = { method: 'GET',
      url: 'https://www.eventbriteapi.com/v3/events/search/',
      qs: { q: term, token: "Token" }};

    request(options, function (error, response, body) {
      if (error) throw new Error(error);

      var response = body;
      response = JSON.parse(response);
      var events = response.events;

      res.render('searchresults', { term: term, events: events});
    });

  });
};
