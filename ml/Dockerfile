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

# Setup the application
WORKDIR /usr/src/app
RUN mkdir -p /usr/src/app

COPY index.py /usr/src/app

CMD [ "python", "./index.py" ]
