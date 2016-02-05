import Boom from 'boom'
import log from './../../log'

exports.register = (server, options, next) => {
  server.route({
    method: 'GET',
    path: '/api/light',
    handler: (request, reply) => {
      reply(Boom.notImplemented())
    },
  })

  server.route({
    method: 'GET',
    path: '/api/light/{id}',
    handler: (request, reply) => {
      reply(Boom.notImplemented())
    },
  })
  next()
}

exports.register.attributes = {
  name: 'Plugin: API',
  version: '1.0.0',
}
