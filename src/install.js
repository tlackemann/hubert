import readline from 'readline'
import fs from 'fs'
import { assign } from 'lodash'
import config from 'config'
import hue from './hue'
import Log from './log'

// Setup logger
const log = new Log('hubert-install')

// Setup terminal input
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

// Set the username
const username = process.env.HUE_USER || config.hue.username || 'hubert';

rl.question('Please press the "link" button on your Hue Bridge and then press any key to continue', (answer) => {
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

      // Create a new "production" configuration
      const newConfig = assign({}, config, { hue: { username: username, hash: user } })
      fs.writeFileSync('config/production.json', JSON.stringify(newConfig))
      rl.close()
      log.info('Successfully saved configuration')
      process.exit(0)
    })
    .catch((err) => {
      log.error("There was a problem creating the user: %s", err)
      rl.close()
      process.exit(1)
    })
});

// Create the user
