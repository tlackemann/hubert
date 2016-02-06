import config from 'config'
import Promise from 'bluebird'
import cassandra from 'cassandra-driver'
import { clone, map, fill } from 'lodash'
import log from './../../log'
import hue from './../../hue'

// Connect to Cassandra
const db = new cassandra.Client({
  contactPoints: config.db.cassandra.hosts,
  keyspace: config.db.cassandra.keyspace,
  authProvider: new cassandra.auth.PlainTextAuthProvider(
    config.db.cassandra.username || null,
    config.db.cassandra.password || null
  ),
})

// Setup a reference for our API
let api = {};

// We can ignore errors up to a certain limit
let errCount = config.app.errorThreshold

// Declare an error handler
const handleError = (err) => {
  log.error('Something went terribly wrong: %s', err)
  if (errCount > 0) {
    log.error('Will ignore %s more times ...', errCount - 1)
    errCount--
  } else {
    // Cleanup and shutdown
    clearInterval(intervalGetLightState)
    log.error('Shutting down the application ...')
    process.exit(1)
  }
}

// Declare a function to save states of our lights
const saveLightStates = (lights) => {
  const columns = [
    'light_id',
    'state_on',
    'bri',
    'hue',
    'sat',
    'effect',
    'x',
    'y',
    'ct',
    'alert',
    'colormode',
    'reachable',
    'name',
    'ts',
  ]
  const values = fill(clone(columns), '?')

  const queries = map(lights, (light) => {
    return {
      query: `INSERT INTO light_events (${columns.join(',')}) VALUES (${values.join(',')})`,
      params: [
        light.uniqueid,
        light.state.on,
        light.state.bri,
        light.state.hue,
        light.state.sat,
        light.state.effect,
        light.state.xy[0],
        light.state.xy[1],
        light.state.ct,
        light.state.alert,
        light.state.colormode,
        light.state.reachable,
        light.name,
        cassandra.types.TimeUuid.now(),
      ],
    }
  })

  // Save this stuff
  log.info('Preparing to save light states ...')
  db.batch(
    queries,
    { prepare: true },
    (err) => {
      if (err) {
        log.error('Problem saving the light states')
        return handleError(err)
      }
      log.info('Successfully saved light states of %s lights', queries.length)
      // If we had errors we can clear them again
      errCount = config.app.errorThreshold
    }
  )
}

// Declare an interval that will check for the state of our lights every X ms
let intervalGetLightState = false

const getLightState = () => {
  log.info('Getting light states')
  api.getFullState()
    .then((state) => saveLightStates(state.lights))
    .catch(handleError)
}

exports.register = (server, options, next) => {
  log.info('Initializing Hue Monitor')

  // Find available bridges and use the first one
  // @todo - Support for multiple bridges
  hue.getDefaultBridge()
    .then((bridge) => {
      const ip = bridge.ipaddress
      const username = config.hue.username

      log.info('Attempting to establish a connection ...')
      log.info('Connecting on %s with username "%s"', ip, username)

      // Establish a connection with the bridge
      api = hue.getConnection(ip, username)
      return api.config()
    })
    .then((state) => {
      // Check to make sure we've successfully authenticated
      if (!state.whitelist) {
        log.error('Successfully connected to the bridge however the user provided is incorrect.')
        log.error('Check that "hue.user" provided in the configuration is correct')
        throw 'Invalid User'
      }

      // Let's get the lightbulbs now
      log.info('Successfully connected to the bridge "%s"', state.name)

      // Start the interval
      intervalGetLightState = setInterval(getLightState, config.app.checkInterval)

      // Done, that's it
      next()
    })
    .catch((err) => {
      log.error('An error occurred while initializing the Hue Monitor: %s', err)
      log.error('Shutting down the application ...')
      return process.exit(1)
    })
}

exports.register.attributes = {
  name: 'Plugin: Hue Monitor',
  version: '1.0.0',
}
