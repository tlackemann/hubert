import config from 'config'
import { clone, map, fill, flatten } from 'lodash'
import cassandra from 'cassandra-driver'
import db from './../../cassandra'
import Log from './../../log'
import hue from './../../hue'

// Setup logger
const log = new Log('hubert-worker')

// Declare an interval that will check for the state of our lights every X ms
let intervalGetLightState = false

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
    'unique_id',
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
  const queries = map(lights, (light, id) => {
    const q = [
      {
        query: `INSERT INTO lights (light_id, name) VALUES (?, ?)`,
        params: [
          id,
          light.name,
        ],
      },
      {
        query: `INSERT INTO light_events (${columns.join(',')}) VALUES (${values.join(',')})`,
        params: [
          id,
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
      },
    ]
    return q
  })

  // Save this stuff
  log.info('Preparing to save light states ...')
  db.batch(
    flatten(queries, true),
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

exports.register = (server, options, next) => {
  log.info('Initializing worker ...')

  hue.connect()
    .then((api) => {
      function getLightState() {
        log.info('Getting light states')
        api.getFullState()
          .then((state) => saveLightStates(state.lights))
          .catch(handleError)
      }

      // Run once right away
      getLightState()

      // Setup the interval to check every X seconds
      intervalGetLightState = setInterval(getLightState, config.app.checkInterval)
      next()
    })
    .catch((err) => {
      log.error('An error occurred while initializing the worker: %s', err)
      log.error('Shutting down the application ...')
      return process.exit(1)
    })
}

exports.register.attributes = {
  name: 'Plugin: Hue Monitor',
  version: '1.0.0',
}
