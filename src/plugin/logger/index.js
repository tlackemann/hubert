import { assign } from 'lodash'
import log from './../../log'

exports.register = (server, options, next) => {
  server.on('response', (request) => {
    const method = request.method.toUpperCase()
    let extraParams = {
      ip: request.info.remoteAddress,
      response: request.response.source,
    }
    if (method === 'POST') {
      extraParams = assign({}, extraParams, { payload: request.payload })
    }
    log.info(extraParams, `${method} ${request.url.path} (${request.response.statusCode})`)
  })
  next()
}

exports.register.attributes = {
  name: 'Plugin: Log',
  version: '1.0.0',
}
