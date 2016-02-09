import amqp from 'amqp'
import config from 'config'

const connection = new amqp.createConnection({
  host: config.rabbitmq.host,
  login: config.rabbitmq.login,
  password: config.rabbitmq.password,
})
export default connection
