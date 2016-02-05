import Boom from 'boom'
import log from './../../log'


exports.register = (server, options, next) => {
  server.route({
    method: 'GET',
    path: '/',
    handler: (request, reply) => {
      log.info('Hitting the homepage')
      reply(200)
    },
  })
  next()
}

exports.register.attributes = {
  name: 'Plugin: SPA',
  version: '1.0.0',
}
