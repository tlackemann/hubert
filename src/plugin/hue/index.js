import log from './../../log'
import hue from './../../hue'

exports.register = (server, options, next) => {
  log.info('Initializing Hue Monitor')

  // Find available bridges and use the first one
  // @todo - Support for multiple bridges
  hue.getDefaultBridge()
    .then((bridge) => {
      // Establish a connection with the bridge
      log.info('Attempting to establish a connection ...')
      const HueApi = hue.HueApi
      const connection = new HueApi(bridge.ipaddress, config.hue.username)
    })
    .catch(() => {
      log.error('Shutting down the application ...')
      return process.exit(1)
    })
  })

  next()
}

exports.register.attributes = {
  name: 'Plugin: Hue Monitor',
  version: '1.0.0',
}
