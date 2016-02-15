// import cassandra from 'cassandra-driver'
import config from 'config'
import twilio from 'twilio'
import { pick, isEqual, each } from 'lodash'
import Log from './../../log'
import hue from './../../hue'
// import db from './../../cassandra'

// Setup logger
const log = new Log('hubert-processor')

exports.register = (server, options, next) => {
  const rabbitmq = require('./../../rabbitmq')

  log.info('Initializing processor ...')
  log.info('Twilio enabled: %s', (Boolean(config.twilio.enabled)) ? 'True' : 'False')

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
            const messageStatus = JSON.parse(msg);
            const lightId = messageStatus.id
            log.info({ light_id: lightId }, 'Received message')

            // Change the light states
            // @todo - Check actual light state before modifying
            log.info({ light_id: lightId }, 'Fetching the state of Light ID: %s', lightId)
            api.lightStatus(lightId)
              .then((status) => {
                const requiredStates = ['on', 'bri', 'hue', 'sat', 'xy']
                const state = pick(status.state, requiredStates)
                const messageState = pick(messageStatus, requiredStates)
                // Compare against message state
                const equal = isEqual(state, messageState)
                const newState = {}
                if (!equal) {
                  log.info({ light_id: lightId }, 'States for light %s are not equal', lightId)
                  // Let's identify what is different
                  const twilioLogs = []
                  each(requiredStates, (s) => {
                    const currentValue = state[s]
                    const newValue = messageState[s]
                    if (
                      (s !== 'xy' && newValue !== currentValue) ||
                      (s === 'xy' && !isEqual(newValue, currentValue))
                    ) {
                      newState[s] = newValue
                      log.info(
                        { light_id: lightId },
                        '"%s": was %s, now %s',
                        s, currentValue, newValue
                      )
                      if (Boolean(config.twilio.enabled)) {
                        twilioLogs.push(`${s}: was ${currentValue}, now ${newValue}`)
                      }
                    }
                  })
                  // We should only up if the light is on or going to be on
                  if (newState.on || state.on) {
                    // Now update the light
                    api.setLightState(lightId, newState)
                      .then(() => {
                        log.info({ light_id: lightId }, 'Successfully updated light')

                        // Sending a message to the configured phone number
                        // Initialize to Twilio
                        if (Boolean(config.twilio.enabled)) {
                          log.info({ light_id: lightId }, 'Twilio is enabled')
                          const twilioClient = new twilio.RestClient(
                            config.twilio.sid,
                            config.twilio.token
                          );
                          twilioClient.sms.messages.create({
                            to: config.twilio.to,
                            from: config.twilio.number,
                            body: `Updated state of Light ${lightId}` +
                              `\n---\n${twilioLogs.join('\n')}`,
                          }, (error) => {
                            if (error) {
                              log.error(
                                { light_id: lightId },
                                'There was a problem sending SMS: %s',
                                error
                              )
                            } else {
                              log.info(
                                { light_id: lightId },
                                'Successfully sent SMS to %s',
                                config.twilio.to
                              )
                            }
                          })
                        }
                      })
                      .catch((err) => {
                        log.error(
                          { light_id: lightId },
                          'Problem saving current light state: %s',
                          err
                        )
                      })
                  } else {
                    log.info(
                      { light_id: lightId },
                      'Skipping update because light is off'
                    )
                  }
                } else {
                  log.info(
                    { light_id: lightId },
                    'States for light %s are equal, nothing to do',
                    lightId
                  )
                }
              })
              .catch((err) => {
                log.error(
                  { light_id: lightId },
                  'Problem fetching current light state: %s',
                  err
                )
              })
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
