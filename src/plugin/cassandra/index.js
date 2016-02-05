import config from 'config'
import cassandra from 'cassandra-driver'

exports.register = (server, options, next) => {
  const client = new cassandra.Client({
    contactPoints: config.db.cassandra.hosts,
    keyspace: config.db.cassandra.keyspace,
    authProvider: new cassandra.auth.PlainTextAuthProvider(
      config.db.cassandra.username || null,
      config.db.cassandra.password || null
    ),
  })

  server.method('cassandra', () => client, {})
  next()
}

exports.register.attributes = {
  name: 'Plugin: Cassandra',
  version: '1.0.0',
}
