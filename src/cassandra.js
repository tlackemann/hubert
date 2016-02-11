import cassandra from 'cassandra-driver'
import config from 'config'
import Log from './log'

const log = new Log('hubert-cassandra')

// Connect to Cassandra
const db = new cassandra.Client({
  contactPoints: config.db.cassandra.hosts,
  keyspace: config.db.cassandra.keyspace,
  authProvider: new cassandra.auth.PlainTextAuthProvider(
    config.db.cassandra.username || null,
    config.db.cassandra.password || null
  ),
})

db.on('connect', () => {
  log.info('Cassandra connected')
})

export default db
