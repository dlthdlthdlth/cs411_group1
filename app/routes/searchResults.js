var express = require('express');
var router = express.Router();


router.post('/searchresults', (req, res)  => {
  res.send('You sent the name "' + req.body.search + '".')
});


module.exports = router;
