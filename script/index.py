#!/usr/bin/python

##
# Hubert
# This script fetches light event data from Cassandra, normalizes it, and runs
# it against a ridge regresssion model to gain predictive intelligence on
# future light events.
#
# The algorithm searches for the best polynomial fit and ridge alpha based on
# the mean_squared_error. The degree and alpha with the lowest
# mean_squared_error is then used to make a prediction for a light based on the
# current hour.
#
# Disclaimer: I am an absolute beginner at machine learning. For all I know
# this algorithm is fundamentally flawed. I'm open to feedback and suggestions
# via pull requests or by opening an issue on GitHub.
##

import operator
import json
import time
import calendar
import numpy as np
import cassandra
import pika
from datetime import datetime, timedelta
from time import sleep
from sklearn.metrics import mean_squared_error
from sklearn import datasets
from sklearn.linear_model import LinearRegression
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from cassandra.cluster import Cluster

start_time = time.time()
print '%.2f - Initializing ...' % (time.time())

RABBITMQ_QUEUE = 'hubert_events'
LR_LOWER_LIMIT = 20158
LR_UPPER_LIMIT = 40316

print '%.2f - Connecting to RabbitMQ ...' % (time.time())
rmq_credentials = pika.PlainCredentials('hubert', 'hubert')
rmq = pika.BlockingConnection(pika.ConnectionParameters('hubert.rabbitmq', credentials=rmq_credentials))
rmq_channel = rmq.channel()
rmq_channel.queue_declare(queue=RABBITMQ_QUEUE)

print '%.2f - Connecting to Cassandra ...' % (time.time())
# Connect to Cassandra
cluster = Cluster(['cassandra'])
session = cluster.connect('hubert')

print '%.2f - Fetching lights ...' % (time.time())
lights = session.execute('SELECT * FROM lights')
print '%.2f - Fetched %s lights from database ...' % (time.time(), len(lights.current_rows))

for light in lights:
    print '%.2f - "%s">> Processing light ...' % (time.time(), light.name)
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

    print '%.2f - "%s">> Fetched %s total rows' % (time.time(), light.name, total_rows)

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

    # Find the optimal polynomial degree
    final_est = False
    final_degree = 0
    final_alpha = 0.
    final_train_error = False
    final_test_error = False

    print '%.2f - "%s">> Starting algorithm ...' % (time.time(), light.name)
    for degree in range(10):
        # Find the optimal l2_penalty/alpha
        tmp_train_error = False
        tmp_test_error = False
        for alpha in [0.0, 1e-8, 1e-5, 1e-1]:
            est = make_pipeline(PolynomialFeatures(degree), Ridge(alpha=alpha))
            est.fit(X_train, Y_train)
            # Training error
            tmp_alpha_train_error = mean_squared_error(Y_train, est.predict(X_train))
            # Test error
            tmp_alpha_test_error = mean_squared_error(Y_test, est.predict(X_test))
            # Is it the lowest one?
            if final_est == False or abs(tmp_alpha_test_error) < final_test_error:
                final_est = est
                final_alpha = alpha
                final_degree = degree
                final_test_error = tmp_alpha_test_error
                final_train_error = tmp_alpha_train_error

    print '%.2f - "%s">> Best training error: %.6f' % (time.time(), light.name, final_train_error)
    print '%.2f - "%s">> Best test error: %.6f' % (time.time(), light.name, final_test_error)
    print '%.2f - "%s">> Using degree=%s and alpha=%s for ridge regression algorithm' % (time.time(), light.name, final_degree, final_alpha)
    # print test_error
    # Print some useful information
    rss = final_test_error
    # rss = np.mean((clf.predict(X_test) - Y_test) ** 2)
    # print '%.2f - "%s">> Coefficients: %s' % (time.time(), light.name, final_est.coef_)
    print '%.2f - "%s">> Residual sum of squares: %.2f' % (time.time(), light.name, rss)

    # EXPERIMENTAL
    right_now = datetime.now()
    # 70% is passing by my standards, try and alter the state of this light
    if rss < 0.3:
        # If we have enough observations, start to play with the lights
        if total_rows >= LR_LOWER_LIMIT and total_rows < LR_UPPER_LIMIT:
            print '%.2f - "%s">> Modifying state of light ...' % (time.time(), light.name)
            print '%.2f - "%s">> The time is %s' % (time.time(), light.name, right_now)
            print '%.2f - "%s">> Predicting for hour %s' % (time.time(), light.name, right_now.hour)
            print final_est.predict(right_now.hour)
            # @todo - Send a message to RabbitMQ to change the state of the light
            # A worker will then pick up the message and process the result
            # state_message = json.dumps({ 'id': light.light_id, 'on': state_int })
            # rmq_channel.basic_publish(exchange='',routing_key=RABBITMQ_QUEUE,body=state_message)
        # Also alter the sat, hue, bri, etc
        elif total_rows >= LR_UPPER_LIMIT:
            print '%.2f - "%s">> Modifying state of light ...' % (time.time(), light.name)
            print '%.2f - "%s">> The time is %s' % (time.time(), light.name, right_now)
            print '@todo'
        else:
            print '%.2f - "%s">> Not enough data, nothing to do (%d observations)' % (time.time(), light.name, total_rows)


    else:
        print '%.2f - "%s">> RSS too high, nothing to do' % (time.time(), light.name)

    # @todo this will be moved above under total_rows >= LR_UPPER_LIMIT
    # this is for testing with all amounts of data
    prediction = final_est.predict(right_now.hour)
    state_int = int(round(prediction[0][0]))
    predict_state = 'ON' if state_int else 'OFF'
    confidence = final_est.score(X_test, Y_test) # 1 is perfect prediction
    print '%.2f - "%s">> Predicting state of light is: %s (Confidence: %.2f)' % (time.time(), light.name, predict_state, confidence)
    print '%.2f - "%s">> Done processing light' % (time.time(), light.name)

# Done!
end_time = time.time()
total_time = end_time - start_time
rmq.close()
cluster.shutdown()
print '%.2f - Done! (Ran in %.6f seconds)' % (time.time(), total_time)
