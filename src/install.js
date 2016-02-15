import readline from 'readline'
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
const username = process.env.HUE_USER || 'hue-app-user';

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
      log.info('Done!')
      rl.close();
    })
    .catch((err) => {
      log.error("There was a problem creating the user: %s", err)
      process.exit(1)
      rl.close();
    })
});

// Create the user
