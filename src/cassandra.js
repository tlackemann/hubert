import cassandra from 'cassandra-driver'
import config from 'config'

// Connect to Cassandra
const db = new cassandra.Client({
  contactPoints: config.db.cassandra.hosts,
  keyspace: config.db.cassandra.keyspace,
  authProvider: new cassandra.auth.PlainTextAuthProvider(
    config.db.cassandra.username || null,
    config.db.cassandra.password || null
  ),
})


export default db
