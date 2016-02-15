import hue from 'node-hue-api'
import Promise from 'bluebird'
import config from 'config'
import Log from './log'

// Setup logger
const log = new Log('hubert-hue')

const HueApi = hue.HueApi;

function getDefaultBridge() {
  return new Promise((res, rej) => {
    hue.nupnpSearch((err, result) => {
      if (err) {
        log.error('An error occurred fetching bridges from Hue: %s', err)
        return rej(err);
      }

      // Get the first bridge
      const bridge = result.length ? result[0] : {}
      if (!bridge.id) {
        log.error('No bridges found!');
        return rej('No bridges found');
      }

      log.info('Found bridge: %s (IP: %s)', bridge.id, bridge.ipaddress)
      res(bridge)
    })
  })
}

function getConnection(ip, username) {
  return new HueApi(ip, username)
}

function registerUser(ip, username) {
  return new Promise((res, rej) => {
    const hpi = new HueApi();
    log.info('Registering user: %s', username)
    hpi.registerUser(ip, username)
      .then((user) => {
        res(user)
      })
      .fail((err) => {
        rej(err)
      })
      .done()
  })
}

function connect() {
  return new Promise((res, rej) => {
    let api = {}

    getDefaultBridge()
      .then((bridge) => {
        const ip = bridge.ipaddress
        const username = config.hue.hash

        log.info('Attempting to establish a connection ...')
        log.info('Connecting on %s with username "%s"', ip, username)

        // Establish a connection with the bridge
        api = this.getConnection(ip, username)
        return api.config()
      })
      .then((state) => {
        // Check to make sure we've successfully authenticated
        if (!state.whitelist) {
          log.error('Successfully connected to the bridge however the user provided is incorrect.')
          log.error('Check that "hue.user" provided in the configuration is correct')
          throw new Error('Invalid User')
        }

        // Let's get the lightbulbs now
        log.info('Successfully connected to the bridge "%s"', state.name)

        // Done, that's it
        res(api)
      })
      .catch((err) => {
        rej(err)
      })
  })
}

export default {
  getConnection,
  getDefaultBridge,
  registerUser,
  connect,
}
