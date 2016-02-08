import amqp from 'amqp'
import config from 'config'

const connection = amqp.createConnection({ host: config.rabbitmq.host });
