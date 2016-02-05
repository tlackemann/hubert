import hue from './hue'
import log from './log'

// Create the user
hue.getDefaultBridge()
  .then((bridge) => {
    return hue.registerUser(
      bridge.ipaddress,
      process.env.HUE_USER || 'hue-app-user'
    )
  })
  .then((user) => {
    log.info('Done!')
  })
