import hue from './hue'
import Log from './log'

// Setup logger
const log = new Log('hubert-install')

// Set the username
const username = process.env.HUE_USER || 'hue-app-user';

// Create the user
hue.getDefaultBridge()
  .then((bridge) => {
    const user = hue.registerUser(
      bridge.ipaddress,
      username
    )
    return user
  })
  .then((user) => {
    log.info('User created: %s (%s)', username, user)
    log.info('Done!')
  })
