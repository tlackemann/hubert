import hue from './hue'
import log from './log'

// Set the username
const username = process.env.HUE_USER || 'hue-app-user';

// Create the user
hue.getDefaultBridge()
  .then((bridge) => {
    return hue.registerUser(
      bridge.ipaddress,
      username
    )
  })
  .then((user) => {
    console.log(user)
    log.info('User created: %s (%s)', username, user)
    log.info('Done!')
  })
