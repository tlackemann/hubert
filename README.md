# Hue App

A web-application to make the lights in your house smarter.

## Installation

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
