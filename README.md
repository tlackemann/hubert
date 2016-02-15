# Hubert

![He'll get the lights for you](asset/hubert-sm.jpg)

_He'll get the lights for you._

![david-dm](https://david-dm.org/tlackemann/hubert.svg)

## Description

A Nest-inspired application for the [Phillips Hue](http://meethue.com).

For more information, see [How It Works](#how-it-works).

## Installation

To install Hubert, simply run:

```
./bin/install
```

The application will download and build all necessary Docker containers. You
will be prompted to press the 'Link' button on your Hue Bridge to complete the
installation.

## Usage

Hubert runs as a Docker daemon. To start Hubert, run:

```
./bin/start
```

To stop Hubert, run:

```
./bin/stop
```

## How It Works

Hubert learns from your light usage patterns. It does this by logging the state
of your lights every so often and running the data against a ridge regression
model. Hubert will only start changing the state of your lights once it has
determined enough data has been collected and the error rate (calculate by
the mean squared error) is within a certain threshold.

All information is recorded to a Cassandra database. A python cron then reads
the information and makes predictions on based on the current conditions.

### Learning

The first few weeks of data collection are to train the ridge regression model.
Hubert does not start altering the state of your lights until enough data
has been collected and the mean squared error is within an acceptable limit.

Hubert's algorithm is simple in that it loops over a range of polynomials (0-9)
and a range of alphas (`0.0, 1e-8, 1e-5, 1e-1`) to determine the fit that
best minimizes the test error. There are plans to implement k-fold
cross-validation or something similar to best fit smaller amounts of data.

**Disclaimer:** Python and Machine Learning are both very new to me. I always
welcome and appreciate constructive feedback.

### Containers

Hubert is composed of four containers.

 1. `hubert` - The main processor; Sends updates to Cassandra container; Processes RabbitMQ messages to alter the state of the lights
 2. `learn` - Machine learning algorithm; Learns from usage and sends messages to RabbitMQ for processing
 3. `rabbitmq` - A RabbitMQ instance used for publish-subscribe
 4. `cassandra` - A Cassandra instance used for data collection

### Machine Learning Cron

Hubert applies linear regression to build opinions on the states of your Hue
lights. Python and [scikit-learn](http://scikit-learn.org/stable/) are used
to build intelligence from the data the application collects. Hubert is able
to determine when your lights should be on or off and will automatically adjust
these settings based on feedback given.

All source code for the machine learning script can be found in `script/`. The
docker container `learn` is setup to be run via a cron.

You can setup a cron by easily adding the following to your `crontab`

```
* * * * * ./bin/learn
```

We recommend running the machine learning algorithm every minute.

## Development

Development for Hubert is relatively straight-forward.

### Dependencies

* [Node.js](http://nodejs.org)
* [Docker](https://docker.com/)

### Installation

Use git to checkout the repository:

```
git checkout https://github.com/tlackemann/hubert.git hubert
```

Then install the application by running:

```
cd hubert && npm install && npm run build
```

This will install all required modules and compile the source code.

### Create Hue Bridge User

In order to use this application, you'll first need to register it with your Hue
Bridge. This can easily be done by following the below steps:

1. Press the 'link' button on your Hue Bridge
2. Run `HUE_USER=my-cool-username node dist/install.js`
3. Update `./config/default.json` with your new username

A new user will automatically be created for you. Update the configuration
file with the hash it generates, it will look something like this:

```
033a6feb77750dc770ec4a4487a9e8db
```

Don't forget to update the configuration file, otherwise the application
will not be able to communicate properly.

### Seed Cassandra Database

In addition to creating a bridge user, you'll also need to seed a Cassandra
instance with the `hubert` schemas.

To seed the Cassandra instance, start the Cassandra container by running:

```
docker-compose up cassandra
```

Then run the following to seed the necessary schemas:

```
docker run -it --link hubert_cassandra_1:cassandra --rm hubert_cassandra sh -c 'exec cqlsh "$CASSANDRA_PORT_9042_TCP_ADDR" -f /docker/hubert.cql'
```

### Create Machine Learning Cron

Finally, build the machine learning container so that we can execute it as a
cron.

```
docker build -t hubert_learn:latest script/
```

Now add the following to your `crontab` (make sure to update `/path/to/hubert`
with the correct folder):

```
* * * * * /path/to/hubert/bin/learn
```

### Running

Start the application by running:

```
docker-compose up
```

This will start all containers necessary to run Hubert.


The Docker container for the node.js applications use [nodemon]() to reboot the
instance whenever a file is changed. Since it's faster to run ES5 code
(currently) we need to compile ES6 down to ES5.

```
npm run dev
```

This will setup a listener on the `src/` folder to compile into the `dist/`
folder.

### Configuration

All configuration can be found in `config/default.json`. This project utilizes
[config](https://www.npmjs.com/package/config) which allows you to override any
configuration setting easily by creating an environment-specific `.json` file
such as `config/production.json`.

#### Twilio

**Experimental:** Hubert integrates with Twilio to alert you when the state of
your light has changed. To enable Twilio, simply update the configuration file
with your Twilio credentials.

## License

    Copyright 2016 Thomas Lackemann

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
