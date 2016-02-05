import hue from 'node-hue-api'
import Promise from 'bluebird'
import config from 'config'
import log from './log'

const HueApi = hue.HueApi;

const getDefaultBridge = () => {
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

const getConnection = (ip, username) => {
  return new HueApi(ip, username)
}

const registerUser = (ip, username) => {
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

export default {
  getConnection,
  getDefaultBridge,
  registerUser,
}
