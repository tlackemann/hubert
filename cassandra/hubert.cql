-- Drop the keyspace
DROP KEYSPACE IF EXISTS hubert;

-- Create our keyspace
CREATE KEYSPACE hubert WITH replication =
  { 'class': 'SimpleStrategy', 'replication_factor': 1 };

-- Use the keyspace
USE hubert;

CREATE COLUMNFAMILY lights (
  light_id text,
  name text,
  PRIMARY KEY(light_id)
);

-- Table: light_events
CREATE COLUMNFAMILY light_events (
  light_id text,
  state_on boolean,
  bri int,
  hue int,
  sat int,
  effect text,
  x float,
  y float,
  ct int,
  alert text,
  colormode text,
  reachable boolean,
  name text,
  ts timeuuid,
  PRIMARY KEY(light_id, ts)
);
