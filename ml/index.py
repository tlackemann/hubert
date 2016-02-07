#!/usr/bin/python

import time
from time import sleep
import numpy as np
import cassandra
from sklearn import linear_model, datasets
from cassandra.cluster import Cluster

print 'Initializing ...'
start_time = time.time()

print 'Connecting to Cassandra ...'
# Connect to Cassandra
cluster = Cluster(['cassandra'])
session = cluster.connect('hue_app')

print 'Fetching lights ...'
lights = session.execute('SELECT * FROM lights')
print 'Fetched %s lights from database ...' % len(lights.current_rows)

for light in lights:
    print 'Processing light "%s"' % light.name
    # Declare our X input (week hour)
    X = []
    # Declare our Y output (reachable && state_on, bri, hue, sat, x, y)
    Y = []
    # Now load all the events for this light
    sql = 'SELECT light_id, state_on, reachable, bri, hue, sat, x, y, ts FROM light_events WHERE light_id = %s ORDER BY ts DESC'
    light_events = session.execute(sql, [light.light_id])
    total_rows = len(light_events.current_rows)
    # Loop over each light and store the data in X and Y
    for event in light_events:
        # Get the datetime of the event
        event_time = cassandra.util.datetime_from_uuid1(event.ts)
        # Monday is 0 and Sunday is 6
        day_of_week = event_time.weekday()
        current_hour = event_time.hour
        current_minute = event_time.minute
        # Get the datetime of the timeuuid - We're going to convert this to a
        # "Week Minute" (0-10079 based scale based on how many minutes in a week)
        # 1440 = Minutes in a day
        # Formula: [(weekday * 1440) + (hour * 60) + minute]
        # e.g.
        # Monday 12:00am = (0 * 1440) + (0 * 60) + 0 = 0
        # Monday 1:00am = (0 * 1440) + (1 * 60) + 0 = 59
        # Tuesday 12:00am = (1 * 1440) + (0 * 60) + 0 = 1339
        # Sunday 11:59pm = (6 * 1440) + (23 * 60) + 59 = 8640 + 1380 + 59 = 10079
        week_hour = (day_of_week * 1440) + (current_hour * 60) + current_minute
        X.append([week_hour])
        # Form the Y features
        event_state = 1 if (event.reachable and event.state_on) else 0
        # Based on our number of observations, we should be more kind to lesser
        # observations to try and not overfit
        if total_rows < 10000:
            Y.append([event.hue, event.bri])
        elif total_rows >= 10000 and total_rows < 50000:
            Y.append([event.hue, event.bri, event.sat, event_state])
        else:
            print '@todo'
            # @todo - Actually modify the light to what the best prediction is
            Y.append([event.hue, event.bri, event.sat, event_state, event.x, event.y])

    # Split the data into training/testing sets
    X_train = X[:-20]
    X_test = X[-20:]

    # Split the targets into training/testing sets
    Y_train = Y[:-20]
    Y_test = Y[-20:]

    # Create a linear regression on the indv. light
    clf = linear_model.LinearRegression()
    clf.fit(X_train, Y_train)

    # Print some useful information
    if total_rows < 10000:
        print 'Using features "hue" and "bri"'
    elif total_rows >= 10000 and total_rows < 50000:
        print 'Using features "hue", "bri", "sat", and "state_on"'
    else:
        print 'Using features "hue", "bri", "sat", "state_on", "x", and "y"'

    print("Residual sum of squares: %.2f" % np.mean((clf.predict(X_test) - Y_test) ** 2))
    print('Variance score: %.2f' % clf.score(X_test, Y_test)) # 1 is perfect prediction

# Done!
print 'Done!'
end_time = time.time()
total_time = end_time - start_time
print 'Ran in %s seconds' % total_time
