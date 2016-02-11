// import cassandra from 'cassandra-driver'
import config from 'config'
import Log from './../../log'
import hue from './../../hue'
// import db from './../../cassandra'

// Setup logger
const log = new Log('hubert-processor')

exports.register = (server, options, next) => {
  const rabbitmq = require('./../../rabbitmq')

  log.info('Initializing processor ...')

  // Wait for connection to become established.
  rabbitmq.on('ready', () => {
    log.info('Connection ready')

    const opts = {
      autoDelete: false,
    }

    // Connect to Hue
    hue.connect()
      .then((api) => {
        // Use the default 'amq.topic' exchange
        rabbitmq.queue(config.rabbitmq.queue, opts, (q) => {
          log.info('Subscribed to %s', config.rabbitmq.queue)
          // Catch all messages
          q.bind('#')
          // Receive messages
          q.subscribe((message) => {
            const msg = message.data.toString()
            const messageState = JSON.parse(msg);
            log.info('Received message: %s', msg)

            // Change the light states
            // @todo - Check actual light state before modifying
            let state = {}
            if (messageState.on !== undefined) {
              state.on = Boolean(messageState.on)

              const onOrOff = (state.on) ? 'ON' : 'OFF';
              api.setLightState(messageState.id, state)
                .then((result) => {
                  log.info('Turned light "%s" %s', messageState.id, onOrOff)
                })
                .catch((err) => {
                  log.error('Problem turning light "%s" %s: %s', messageState.id, onOrOff, err)
                })
            }
          })
        })

        next()
      })
      .catch((err) => {
        log.error('An error occurred while initializing the processor: %s', err)
        log.error('Shutting down the application ...')
        return process.exit(1)
      })
  })

  rabbitmq.on('error', (err) => {
    next(err)
  })
}

exports.register.attributes = {
  name: 'Plugin: RabbitMQ Processor',
  version: '1.0.0',
}
