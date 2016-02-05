import Hapi from 'hapi'
import config from 'config'
import log from './log'

// Setup the server
const server = new Hapi.Server()
server.connection({
  port: config.app.port,
})

// Load our plugins
server.register([
  require('./plugin/cassandra'),
  require('./plugin/logger'),
  require('./plugin/hue'),
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
