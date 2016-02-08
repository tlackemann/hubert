#!/usr/bin/python
import json
import time
import calendar
from datetime import datetime, timedelta
from time import sleep
import numpy as np
import cassandra
from sklearn import linear_model, datasets
from cassandra.cluster import Cluster
import pika

start_time = time.time()
print '%s - Initializing ...' % (time.time())

RABBITMQ_QUEUE = 'hulux_events'
LR_LOWER_LIMIT = 20158
LR_UPPER_LIMIT = 40316

print '%s - Connecting to RabbitMQ ...' % (time.time())
rmq_credentials = pika.PlainCredentials('hulux', 'hulux')
rmq = pika.BlockingConnection(pika.ConnectionParameters('hulux.rabbitmq', credentials=rmq_credentials))
rmq_channel = rmq.channel()
rmq_channel.queue_declare(queue=RABBITMQ_QUEUE)

print '%s - Connecting to Cassandra ...' % (time.time())
# Connect to Cassandra
cluster = Cluster(['cassandra'])
session = cluster.connect('hue_app')

print '%s - Fetching lights ...' % (time.time())
lights = session.execute('SELECT * FROM lights')
print '%s - Fetched %s lights from database ...' % (time.time(), len(lights.current_rows))

for light in lights:
    print '%s - "%s">> Processing light ...' % (time.time(), light.name)
    # Declare our X input (week hour)
    X = []
    # Declare our Y output (reachable && state_on, bri, hue, sat, x, y)
    Y = []
    # Now load all the events for this light
    sql = 'SELECT light_id, state_on, reachable, bri, hue, sat, x, y, ts FROM light_events WHERE light_id = %s ORDER BY ts DESC LIMIT %s'
    light_events = session.execute(sql, [light.light_id, LR_UPPER_LIMIT])
    # We need to know how many rows there are, this is stupid but it works
    # The reasone is because of how cassandra driver works - it will not fetch
    # all rows but rather the first 5000 and then rely on fetch_next_page()
    # or require a for loop. Since that is just stupid, there's this ...
    sql_count = 'SELECT count(*) as c FROM light_events WHERE light_id = %s ORDER BY ts DESC LIMIT %s'
    light_event_count = session.execute(sql_count, [light.light_id, LR_UPPER_LIMIT])
    total_rows = light_event_count.current_rows[0].c

    print '%s - Fetched %s total rows' % (time.time(), total_rows)

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
    print '%s - "%s">> Coefficients: %s' % (time.time(), light.name, clf.coef_)
    print '%s - "%s">> Residual sum of squares: %.2f' % (time.time(), light.name, rss)
    print '%s - "%s">> Variance score: %.2f' % (time.time(), light.name, variance) # 1 is perfect prediction

    # EXPERIMENTAL
    right_now = datetime.now()
    # 70% is passing by my standards, try and alter the state of this light
    if rss < 0.3:
        # If we have enough observations, start to play with the lights
        if total_rows >= LR_LOWER_LIMIT and total_rows < LR_UPPER_LIMIT:
            print '%s - "%s">> Modifying state of light ...' % (time.time(), light.name)
            print '%s - "%s">> The time is %s' % (time.time(), light.name, right_now)
            print '%s - "%s">> Predicting for hour %s' % (time.time(), light.name, right_now.hour)
            print clf.predict(right_now.hour)
            # @todo - Send a message to RabbitMQ to change the state of the light
            # A worker will then pick up the message and process the result
            # rmq_channel.basic_publish(exchange='',routing_key=RABBITMQ_QUEUE,body='testing')
        elif total_rows >= LR_UPPER_LIMIT:
            print '%s - "%s">> Modifying state of light ...' % (time.time(), light.name)
            print '%s - "%s">> The time is %s' % (time.time(), light.name, right_now)
            print '@todo'
        else:
            print '%s - "%s">> Not enough data, nothing to do (%d observations)' % (time.time(), light.name, total_rows)


    else:
        print '%s - "%s">> RSS too high, nothing to do' % (time.time(), light.name)

    prediction = clf.predict(right_now.hour)
    predict_state = 'ON' if int(round(prediction[0][0])) else 'OFF'
    print '%s - "%s">> Predicting state of light is: %s' % (time.time(), light.name, predict_state)


# Done!
end_time = time.time()
total_time = end_time - start_time
rmq.close()
cluster.shutdown()
print '%s - Done! (Ran in %.6f seconds)' % (time.time(), total_time)
