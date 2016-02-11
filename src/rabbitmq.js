import { createConnection as AmqpConnection } from 'amqp'
import config from 'config'

const connection = new AmqpConnection({
  host: config.rabbitmq.host,
  login: config.rabbitmq.login,
  password: config.rabbitmq.password,
})
export default connection
