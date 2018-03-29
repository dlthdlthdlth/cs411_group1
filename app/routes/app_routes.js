const bodyParser = require('body-parser');

const request = require("request");
const eventbriteToken = 'MHPPXZ3TBMC6E47PBCYK';


module.exports = function(app, db){
  app.use(bodyParser.json());
  app.use(bodyParser.urlencoded({extended: true}));

  //Search for an event
  app.post('/searchresults', (req, res)  => {
    console.log(req.body);
    var term = req.body.search;
    var options = { method: 'GET',
      url: 'https://www.eventbriteapi.com/v3/events/search/',
      qs: { q: term, token: eventbriteToken }};

    request(options, function (error, response, body) {
      if (error) throw new Error(error);

      var response = body;
      response = JSON.parse(response);
      var events = response.events;

      res.render('searchResults', { term: term, events: events});
    });

  });

  app.get('/homePage', (req, res) => {
    res.render('homePage', {});
  });

};
