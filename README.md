# hu.lux

A web application to make the [Hue](http://meethue.com) lights in your house smarter.

hu.lux learns from your light usage patterns. Over time, hu.lux will determine
when your lights should be on or off and even what color they should be. It does
this by logging the state of your lights every so often and running the data
against a multiple regression model. hu.lux will only change the state of your
lights once it has determined enough data has been collected and the error rate
(calculate by determining the residual sum of squares, RSS) is within a certain
threshold.

For more information, see [How It Works](#how-it-works).

## Installation

Use git to checkout the repository:

```
git checkout https://github.com/tlackemann/hu.lux.git hulux
```

You can then install the application by running:

```
cd hulux && npm install && npm run build
```

This will install all required modules, compile the source code, and build the
front-end application.

### Running

This application is designed to be started with [Docker](https://docker.com/).

You can start the application by running:

```
docker-compose up
```

This will start the application and a Cassandra instance.

You can view the application by navigating to http://192.169.99.100:3000 (this
might change slightly depending on your Docker installation.)

### Creating Hue Bridge User

In order to use this application, you'll need to register it with your Hue
Bridge. This can easily be done by following the below steps:

1. Press the 'link' button on your Hue Bridge
2. Run `HUE_USER=my-cool-username npm run hue`
3. Update `./config/default.json` with your new username

A new user will automatically be created for you. Don't forget to update the
config file, otherwise the application will not be able to communicate properly.

### Seeding Cassandra Database

In addition to creating a bridge user, you'll also need to seed a Cassandra
instance with the `hue_app` schemas.

To seed the Cassandra instance, ensure your application is running (using
`docker-compose up`) and run the following:

```
docker run -it --link hulux_cassandra_1:cassandra --rm hulux_cassandra sh -c 'exec cqlsh "$CASSANDRA_PORT_9042_TCP_ADDR" -f /docker/hue-app.cql'
```

## How It Works

hu.lux automatically checks the status of your Hue lights every 30 or so seconds
and records the information to a Cassandra database. A python cron then reads
the information and makes predictions on based on the current conditions.

### Learning

The first few weeks of data collection are to train the linear regression model.
hu.lux does not start altering the state of your lights until enough data
(currently 50,000 data points) has been collected and the rate of error is
within an acceptable limit.

## Development

The Docker container for this application runs [nodemon]() to reboot the instance
whenever a file is changed. Since it's faster to run ES5 code (currently) we
need to compile ES6 down to ES5.

```
npm run dev
```

This will setup a listener on the `src/` folder to compile into the `dist/`
folder. When a change is detected on the `dist/` folder, the application will
automatically reboot on the Docker instance.

### Front-end

The front-end application is built using
[React](https://facebook.github.io/react/index.html) &
[Redux](http://redux.js.org/).

The application source is located in the `app/` directory.

### Server

The server application is located in the `src/` directory but is compiled and
run from the `dist/` directory. Data is collected while the server is running.

### Machine Learning Cron

hu.lux applies linear regression to build opinions on the states of your Hue
lights. Python and [scikit-learn](http://scikit-learn.org/stable/) are used
to build intelligence from the data the application collects. hu.lux is able
to determine when your lights should be on or off and will automatically adjust
these settings based on feedback given.

All source for the machine learning cron can be found in `script/`. The docker
container `ml` will automatically initialize a cron to consistently learn
from the data collected.

## Features

* ~~Data collection~~ - *Done*
* Linear regression algorithm - *In progress*
* Front-end application - Not started

## License

MIT
