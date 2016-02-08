import cassandra from 'cassandra-driver'
import rabbiqmq from './rabbitmq'
import db from './cassandra'
/**
 * Blocking call for sleep to prevent accidental DDoS on our RabbitMQ instance
 */
function sleep(delay) {
  const start = new Date().getTime()
  while (new Date().getTime() < start + delay);
}

// Wait for connection to become established.
connection.on('ready', function () {
  // Use the default 'amq.topic' exchange
  connection.queue(config.rabbitmq.queue, function (q) {
    // Catch all messages
    q.bind('#');
    // Receive messages
    q.subscribe(function (message) {
      // Print messages to stdout
      console.log(message);
    });

    sleep(5000)

  });
});
