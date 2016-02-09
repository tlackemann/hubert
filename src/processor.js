import cassandra from 'cassandra-driver'
import config from 'config'
import Log from './log'
import rabbitmq from './rabbitmq'
import db from './cassandra'

// Setup logger
const log = new Log('hubert-processor')

log.info('Worker running')

// Wait for connection to become established.
rabbitmq.on('ready', () => {
  log.info('Connection ready')

  const options = {
    autoDelete: false,
  }

  // Use the default 'amq.topic' exchange
  rabbitmq.queue( config.rabbitmq.queue, options, (q) => {
    log.info('Subscribed to %s', config.rabbitmq.queue)
    // Catch all messages
    q.bind('#')
    // Receive messages
    q.subscribe((message, headers, deliveryInfo, messageObject) => {
      const msg = message.data.toString()
      log.info('Received message: %s', msg);
    })
  })
})
