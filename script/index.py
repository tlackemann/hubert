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
CQL_LIMIT = 1000000

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
    light_events = session.execute(sql, [light.light_id, CQL_LIMIT])
    # We need to know how many rows there are, this is stupid but it works
    # The reasone is because of how cassandra driver works - it will not fetch
    # all rows but rather the first 5000 and then rely on fetch_next_page()
    # or require a for loop. Since that is just stupid, there's this ...
    sql_count = 'SELECT count(*) as c FROM light_events WHERE light_id = %s ORDER BY ts DESC LIMIT %s'
    light_event_count = session.execute(sql_count, [light.light_id, CQL_LIMIT])
    total_rows = light_event_count.current_rows[0].c

    print '%.2f - "%s">> Fetched %s total rows' % (time.time(), light.name, total_rows)

    # Loop over each light and store the data in X and Y
    minutes_in_day = 1440
    recordings_per_minute = 6 # @todo - Expects default setting to record every 10 seconds
    recordings_per_day = minutes_in_day * recordings_per_minute

    # Store the conditionals for our phases
    phase_1_condition = total_rows < recordings_per_day * 14
    phase_2_condition = total_rows >= recordings_per_day * 14 and total_rows < recordings_per_day * 60

    # We need at least a week's worth of data before we start predicting
    if total_rows >= recordings_per_day * 7:
        print '%.2f - "%s">> Preparing to format data ...' % (time.time(), light.name)
        for event in light_events:
            # Get the datetime of the event
            event_time = cassandra.util.datetime_from_uuid1(event.ts)
            # Monday is 0 and Sunday is 6
            day_of_week = event_time.weekday()
            current_day = event_time.day
            current_month = event_time.month
            current_year = event_time.year
            current_hour = event_time.hour
            current_minute = event_time.minute
            # Light is ON if it's both reachable and declared on
            event_state = 1 if (event.reachable and event.state_on) else 0

            # Depending on the amount of data we have, we're going to build the
            # linear regression model slightly different to get the best performance
            # out of the model.

            # Phase I: Train by minutes in day (2 days+)
            # X = Total amount of minutes passed on recorded day (0-1439)
            if phase_1_condition:
                X.append([(current_hour * 60) + current_minute])
                # Features: state
                Y.append([event_state])
            # Phase II: Train by minutes in week (14 days+)
            # X = Total amount of minutes passed during recorded week (0-10079)
            elif phase_2_condition:
                if day_of_week > 0:
                    X.append([((current_hour * 60) + current_minute) * day_of_week])
                else:
                    X.append([(current_hour * 60) + current_minute])
                # Features: state, hue, bri, sat
                Y.append([event_state, event.hue, event.bri, event.sat])

            # Phase III: Train by minutes in month (2 months+)
            # X = Total amount of minutes passed during recorded month (0-n)
            else:
                eq = (current_hour * 60) + current_minute
                if current_day > 0:
                    eq = eq * current_day
                X.append([eq])
                # Features: state, hue, bri, sat, x, y
                Y.append([event_state, event.hue, event.bri, event.sat, event.x, event.y])

        # Split the data into training/testing sets
        # We'll do an 80/20 split
        split_80 = int(round(total_rows * 0.8))
        split_20 = total_rows - split_80
        print '%.2f - "%s">> Total rows: %s, Split 80: %s, Split 20: %s ...' % (time.time(), light.name, total_rows, split_80, split_20)
        X_train = X[:-1 * split_20]
        X_test = X[-1 * split_20:]

        # Split the targets into training/testing sets
        Y_train = Y[:-1 * split_20]
        Y_test = Y[-1 * split_20:]

        # Find the optimal polynomial degree
        final_est = False
        final_degree = 0
        final_alpha = 0.
        final_train_error = False
        final_test_error = False

        print '%.2f - "%s">> Finding best fit for ridge regression model ...' % (time.time(), light.name)
        for degree in range(10):
            # Find the optimal l2_penalty/alpha
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

        rss = final_test_error
        print '%.2f - "%s">> Using degree=%s and alpha=%s for ridge regression algorithm' % (time.time(), light.name, final_degree, final_alpha)
        print '%.2f - "%s">> Best training error: %.6f' % (time.time(), light.name, final_train_error)
        print '%.2f - "%s">> Best test error: %.6f' % (time.time(), light.name, final_test_error)
        print '%.2f - "%s">> Residual sum of squares: %.2f' % (time.time(), light.name, rss)

        # Now that we've run our model, let's determine if we should alter the state
        # of the lights
        right_now = datetime.now()

        # We want to be pretty sure we're going to do something right
        if rss < 0.1:
            # Make sure we have enough observations
            if phase_1_condition:
                # Predict based on the current minute
                prediction_minutes = (right_now.hour * 60) + right_now.minute
                prediction = final_est.predict(prediction_minutes)
                predicted_state = {
                    'id': light.light_id,
                    'on': True if int(round(prediction[0][0])) == 1 else False
                }
            elif phase_2_condition:
                # Predict based on the current minute in the week
                prediction_minutes = (right_now.hour * 60) + right_now.minute
                right_now_weekday = right_now.weekday()
                if right_now_weekday > 0:
                    prediction_minutes = prediction_minutes * right_now_weekday
                prediction = final_est.predict(prediction_minutes)
                predicted_state = {
                    'id': light.light_id,
                    'on': True if int(round(prediction[0][0])) == 1 else False,
                    'hue': int(prediction[0][1]),
                    'bri': int(prediction[0][2]),
                    'sat': int(prediction[0][3])
                }
            else:
                # Predict based on the current minute in the month
                prediction_minutes = (right_now.hour * 60) + right_now.minute
                right_now_weekday = right_now.weekday()
                if right_now_weekday > 0:
                    prediction_minutes = prediction_minutes * right_now_weekday
                if right_now.day > 0:
                    prediction_minutes = prediction_minutes * right_now.day
                prediction = final_est.predict(prediction_minutes)
                predicted_state = {
                    'id': light.light_id,
                    'on': True if int(round(prediction[0][0])) == 1 else False,
                    'hue': int(prediction[0][1]),
                    'bri': int(prediction[0][2]),
                    'sat': int(prediction[0][3]),
                    'xy': [ round(prediction[0][4], 4), round(prediction[0][5], 4) ]
                }

            # Features: state, hue, bri, sat, x, y
            confidence = final_est.score(X_test, Y_test) # 1 is perfect prediction
            state_message = json.dumps(predicted_state)
            print '%.2f - "%s">> Modifying state of light ...' % (time.time(), light.name)
            print '%.2f - "%s">> The time is %s' % (time.time(), light.name, right_now)
            print '%.2f - "%s">> Predicting for current minute %s/%s' % (time.time(), light.name, prediction_minutes, minutes_in_day - 1)
            print '%.2f - "%s">> Predicting state: %s (Confidence: %.2f)' % (time.time(), light.name, 'ON' if predicted_state['on'] else 'OFF', confidence)
            if 'hue' in predicted_state:
                print '%.2f - "%s">> Predicting hue: %s (Confidence: %.2f)' % (time.time(), light.name, predicted_state['hue'], confidence)
            if 'bri' in predicted_state:
                print '%.2f - "%s">> Predicting bri: %s (Confidence: %.2f)' % (time.time(), light.name, predicted_state['bri'], confidence)
            if 'sat' in predicted_state:
                print '%.2f - "%s">> Predicting sat: %s (Confidence: %.2f)' % (time.time(), light.name, predicted_state['sat'], confidence)
            if 'xy' in predicted_state:
                print '%.2f - "%s">> Predicting xy: %s (Confidence: %.2f)' % (time.time(), light.name, predicted_state['xy'], confidence)
            # Update the state of our light
            rmq_channel.basic_publish(exchange='', routing_key=RABBITMQ_QUEUE, body=state_message)

        # RSS too high
        else:
            print '%.2f - "%s">> RSS too high, nothing to do' % (time.time(), light.name)

        print '%.2f - "%s">> Done processing light' % (time.time(), light.name)
    else:
        print '%.2f - "%s">> Skipping light, not enough data to significantly train/test' % (time.time(), light.name)
# @todo - Save the weights of the algorithm to feed in later, this is going to
# get *super* expensive to run every single minute for anything over 5+ lights
#
# Testing with 20k+ rows + 5 lights takes ~14 seconds to complete

# Done!
end_time = time.time()
total_time = end_time - start_time
rmq.close()
cluster.shutdown()
print '%.2f - Done! (Ran in %.6f seconds)' % (time.time(), total_time)
