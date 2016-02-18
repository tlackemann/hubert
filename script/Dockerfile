FROM gliderlabs/alpine:3.3

RUN apk add --update \
    python \
    python-dev \
    py-pip \
    openssl \
    build-base

# Install scipy
RUN echo "@testing http://dl-4.alpinelinux.org/alpine/edge/testing" >> /etc/apk/repositories
RUN apk add --update py-scipy@testing
RUN apk add --update py-numpy@testing

# Upgrade pip
RUN pip install --upgrade pip

# Install scikit-learn
RUN pip install -U scikit-learn

# Install cassandra-driver
RUN pip install -U cython
RUN pip install -U cassandra-driver

# Install Hue package
RUN pip install -U phue

# Install pika for RabbitMQ
RUN pip install -U pika

RUN rm -rf /var/cache/apk/*

# Setup the application
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY index.py /usr/src/app

CMD [ "python", "index.py" ]
