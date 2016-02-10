import Hapi from 'hapi'
import config from 'config'
import Log from './log'

const log = new Log('hubert-worker');

// Setup the server
const server = new Hapi.Server()
server.connection({
  port: config.app.port,
})

// Load our plugins
server.register([
  require('./plugin/healthcheck'),
  require('./plugin/hubert'),
  require('./plugin/processor'),
], (err) => {
  if (err) {
    log.error('Failed to load plugin: %s', err)
    process.exit(1)
  }

  // Run!
  server.start(() => {
    log.info('Server running at %s', server.info.uri)
  })
})
