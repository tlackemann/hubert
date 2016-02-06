import numpy as np
import cassandra
from sklearn import linear_model
from cassandra.cluster import Cluster

print 'Connecting to Cassandra ...'

# Connect to Cassandra
cluster = Cluster(['cassandra'])
session = cluster.connect('hue_app')

# First let's grab all the lights we know about
print 'Fetching lights ...'
lights = session.execute('SELECT * FROM lights')
print 'Fetched %s lights from database ...' % len(lights.current_rows)

for light in lights:
    print 'Processing light "%s"' % light.name
    # Declare our X input (week hour)
    X = []
    # Declare our Z output (reachable && state_on, bri, hue, sat, x, y)
    Z = []

    # Now load all the events for this light
    light_events = session.execute('SELECT light_id, state_on, reachable, bri, hue, sat, x, y, ts FROM light_events WHERE light_id = %s ORDER BY ts DESC', [light.light_id])
    for event in light_events:
        # Get the datetime of the timeuuid - We're going to convert this to a
        # "Week Minute" (0-10079 based scale based on how many minutes in a week)
        # 1440 = Minutes in a day
        # Formula: [(weekday * 1440) + (hour * 60) + minute]
        # e.g.
        # Monday 12:00am = (0 * 1440) + (0 * 60) + 0 = 0
        # Monday 1:00am = (0 * 1440) + (1 * 60) + 0 = 59
        # Tuesday 12:00am = (1 * 1440) + (0 * 60) + 0 = 1339
        # Sunday 11:59pm = (6 * 1440) + (23 * 60) + 59 = 8640 + 1380 + 59 = 10079
        event_time = cassandra.util.datetime_from_uuid1(event.ts)
        # Monday is 0 and Sunday is 6
        day_of_week = event_time.weekday()
        current_hour = event_time.hour
        current_minute = event_time.minute
        week_hour = (day_of_week * 1440) + (current_hour * 60) + current_minute
        X.append([week_hour])

        event_state = 1 if (event.reachable and event.state_on) else 0
        Z.append([event_state, event.bri, event.hue, event.sat, event.x, event.y])

    # Create a linear regression on the indv. light
    clf = linear_model.LinearRegression()
    clf.fit(X, Z)

    # Predict a custom time
    # Sat 9:00pm = (5 * 1440) + (21 * 60) + 0 = 7200 + 1260 = 8460
    print clf.predict(8460)
    # Sun 9:00am = (6 * 1440) + (9 * 60) + 0 = 8640 + 540 = 9180
    print clf.predict(9180)

cluster.shutdown()
print 'Done!'
