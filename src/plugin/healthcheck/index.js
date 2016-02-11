
exports.register = (server, options, next) => {
  server.route({
    method: 'GET',
    path: '/healthcheck',
    handler: (request, reply) => {
      reply('OK')
    },
  })
  next()
}

exports.register.attributes = {
  name: 'Plugin: Healthcheck',
  version: '1.0.0',
}
