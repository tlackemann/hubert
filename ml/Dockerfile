FROM ubuntu:14.04.3

# Install necessary packages
RUN apt-get update && apt-get install -y \
  build-essential \
  curl \
  python-numpy \
  python-pip \
  python-scipy \
  git
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*

# Install pip
RUN curl -O https://bootstrap.pypa.io/get-pip.py && python get-pip.py && \
  rm get-pip.py

# Install cassandra-driver
RUN pip install cassandra-driver

# Install scikit-learn
RUN pip install scikit-learn

# Install Hue package
RUN pip install phue

# Install daemon package
RUN pip install python-daemon

RUN pip install pika

# Setup the application
WORKDIR /usr/src/app
RUN mkdir -p /usr/src/app

COPY index.py /usr/src/app

# Add crontab file in the cron directory
ADD crontab /etc/cron.d/ml-cron
RUN chmod 0644 /etc/cron.d/ml-cron
RUN /usr/bin/crontab /etc/cron.d/ml-cron
RUN touch /var/log/cron.log

CMD cron && tail -f /var/log/cron.log
