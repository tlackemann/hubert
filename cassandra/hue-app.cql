-- Drop the keyspace
DROP KEYSPACE IF EXISTS hue_app;

-- Create our keyspace
CREATE KEYSPACE hue_app WITH replication =
  { 'class': 'SimpleStrategy', 'replication_factor': 1 };

-- Use the keyspace
USE hue_app;

-- Table: light_events
CREATE COLUMNFAMILY light_events (
  light_id text,
  ts timeuuid,
  PRIMARY KEY(light_id, ts)
);
