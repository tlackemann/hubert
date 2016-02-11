// import cassandra from 'cassandra-driver'
import config from 'config'
import Log from './../../log'
import rabbitmq from './../../rabbitmq'
// import db from './../../cassandra'

// Setup logger
const log = new Log('hubert-processor')


exports.register = (server, options, next) => {
  log.info('Initializing processor ...')

  // Wait for connection to become established.
  rabbitmq.on('ready', () => {
    log.info('Connection ready')

    const opts = {
      autoDelete: false,
    }

    // Use the default 'amq.topic' exchange
    rabbitmq.queue(config.rabbitmq.queue, opts, (q) => {
      log.info('Subscribed to %s', config.rabbitmq.queue)
      // Catch all messages
      q.bind('#')
      // Receive messages
      q.subscribe((message) => {
        const msg = message.data.toString()
        log.info('Received message: %s', msg)
      })
      next()
    })
  })
}

exports.register.attributes = {
  name: 'Plugin: RabbitMQ Processor',
  version: '1.0.0',
}
