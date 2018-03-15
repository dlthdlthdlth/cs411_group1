

module.exports = function(app, db){
    app.post('/app', (req, res) => {
	    //post method
	    res.send('Hello')
	});
};

module.exports = function(app, db) {
    app.get('/app', (req, res) => {
	    //get method
	    res.send('Hello')
	});
};