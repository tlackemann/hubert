![He'll get the lights for you](asset/hubert-sm.jpg)

# Hubert

_He'll get the lights for you._

## Description

A web application to make the [Hue](http://meethue.com) lights in your house smarter.

Hubert learns from your light usage patterns. Over time, Hubert will determine
when your lights should be on or off or even what color they should be. It does
this by logging the state of your lights every so often and running the data
against a multiple regression model. Hubert will only change the state of your
lights once it has determined enough data has been collected and the error rate
(calculate by determining the residual sum of squares, RSS) is within a certain
threshold.

For more information, see [How It Works](#how-it-works).

## Installation

Use git to checkout the repository:

```
git checkout https://github.com/tlackemann/hubert.git hubert
```

You can then install the application by running:

```
cd hubert && npm install && npm run build
```

This will install all required modules, compile the source code, and build the
front-end application.

### Running

This application is designed to be started with [Docker](https://docker.com/).

You can start the application by running:

```
docker-compose up
```

This will start all the instances necessary to run Hubert.

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
instance with the `hubert` schemas.

To seed the Cassandra instance, ensure your application is running (using
`docker-compose up`) and run the following:

```
docker run -it --link hubert_cassandra_1:cassandra --rm hubert_cassandra sh -c 'exec cqlsh "$CASSANDRA_PORT_9042_TCP_ADDR" -f /docker/hubert.cql'
```

## How It Works

Hubert automatically checks the status of your Hue lights every 10 seconds
and records the information to a Cassandra database. A python cron then reads
the information and makes predictions on based on the current conditions.

### Learning

The first few weeks of data collection are to train the linear regression model.
Hubert does not start altering the state of your lights until enough data
(currently 50,000 data points) has been collected and the rate of error is
within an acceptable limit.

### Containers

Hubert is composed of five applications, each ran from an individual container.

 1. `hubert` - The main processor; Sends updates to Cassandra container; Processes RabbitMQ messages to alter the state of the lights
 2. `learn` - Machine learning algorithm; Learns from usage and sends messages to RabbitMQ for processing
 3. `rabbitmq` - A RabbitMQ instance used for publish-subscribe
 4. `cassandra` - A Cassandra instance used for data collection

## Development

The Docker container for this application runs [nodemon]() to reboot the instance
whenever a file is changed. Since it's faster to run ES5 code (currently) we
need to compile ES6 down to ES5.

```
npm run dev
```

This will setup a listener on the `src/` folder to compile into the `dist/`
folder.

### Machine Learning Cron

Hubert applies linear regression to build opinions on the states of your Hue
lights. Python and [scikit-learn](http://scikit-learn.org/stable/) are used
to build intelligence from the data the application collects. hubert is able
to determine when your lights should be on or off and will automatically adjust
these settings based on feedback given.

All source code for the machine learning script can be found in `script/`. The
docker container `learn` is setup to be run via a cron.

You can setup a cron by easily adding the following to your `crontab`

```
* * * * * ./bin/learn
```

We recommend running the machine learning algorithm every minute.

## Configuration

All configuration can be found in `config/default.json`. This project utilizes
[config](https://www.npmjs.com/package/config) which allows you to override any
configuration setting easily by creating an environment-specific `.json` file
such as `config/production.json`.

## Features

* ~~Data collection~~ - *Done*
* Linear regression algorithm - *In progress*

## License

Apache 2.0
