import amqp from 'amqp'

/**
 * Blocking call for sleep to prevent accidental DDoS on our RabbitMQ queue
 */
function sleep(delay) {
  const start = new Date().getTime()
  while (new Date().getTime() < start + delay)
}

while(true) {
  console.log('testing')
  sleep(5000)
}
