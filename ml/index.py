#!/usr/bin/python

import time
import calendar
from datetime import datetime, timedelta
from time import sleep
import numpy as np
import cassandra
from sklearn import linear_model, datasets
from cassandra.cluster import Cluster

# Helper function to get as timezone
def utc_to_local(utc_dt):
    # get integer timestamp to avoid precision lost
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)

print 'Initializing ...'
start_time = time.time()
LR_LOWER_LIMIT = 20158
LR_UPPER_LIMIT = 40316

print 'Connecting to Cassandra ...'
# Connect to Cassandra
cluster = Cluster(['cassandra'])
session = cluster.connect('hue_app')

print 'Fetching lights ...'
lights = session.execute('SELECT * FROM lights')
print 'Fetched %s lights from database ...' % len(lights.current_rows)

for light in lights:
    print '"%s">> Processing light' % light.name
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
        # Light is ON if it's both reachable and declared on
        event_state = 1 if (event.reachable and event.state_on) else 0

        # Depending on the amount of data we have, we're going to build the
        # linear regression model slightly different to get the best performance
        # out of the model.
        #
        # <= LR_LOWER_LIMIT - Look at predictions by 'hour'
        # >= LR_UPPER_LIMIT - Look at predictions by 'week_hour'
        if total_rows < LR_LOWER_LIMIT:
            # X - hour
            X.append([current_hour])
            # Features: state
            Y.append([event_state])
        elif total_rows >= LR_LOWER_LIMIT and total_rows < LR_UPPER_LIMIT:
            # X - hour
            X.append([current_hour])
            # Features: state, hue, bri, sat
            Y.append([event_state, event.hue, event.bri, event.sat])
        else:
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
            # Features: state, hue, bri, sat, x, y
            Y.append([event_state, event.hue, event.bri, event.sat, event.x, event.y])

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
    rss = np.mean((clf.predict(X_test) - Y_test) ** 2)
    variance = clf.score(X_test, Y_test)
    print '"%s">> Coefficients: %s' % (light.name, clf.coef_)
    print '"%s">> Residual sum of squares: %.2f' % (light.name, rss)
    print '"%s">> Variance score: %.2f' % (light.name, variance) # 1 is perfect prediction

    # EXPERIMENTAL
    # 70% is passing by my standards, try and alter the state of this light
    if rss < 0.3:
        # If we have enough observations, start to play with the lights
        if total_rows >= LR_LOWER_LIMIT and total_rows < LR_UPPER_LIMIT:
            print '"%s">> Modifying state of light ...' % light.name
            right_now = utc_to_local(datetime.now())
            print '"%s">> The time is %s' % (light.name, right_now)
            print '"%s">> Predicting for hour %s' % (light.name, right_now.hour)
            print clf.predict(right_now.hour)
        elif total_rows >= LR_UPPER_LIMIT:
            print '"%s">> Modifying state of light ...' % light.name
            right_now = utc_to_local(datetime.now())
            print '"%s">> The time is %s' % (light.name, right_now)
            print '@todo'
        else:
            print '"%s">> Not enough data, nothing to do (%d observations)' % (light.name, total_rows)
    else:
        print '"%s">> RSS too high, nothing to do' % (light.name)


# Done!
end_time = time.time()
total_time = end_time - start_time
print 'Done! (Ran in %.6f seconds)' % total_time
