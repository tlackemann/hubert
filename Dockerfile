FROM node:5.1.1

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

RUN npm install nodemon -g

COPY package.json /usr/src/app
RUN npm install
COPY src/ /usr/src/app/src
COPY bin/ /usr/src/app/bin
COPY config /usr/src/app/config
COPY .babelrc /usr/src/app/
COPY nodemon.json /usr/src/app/
COPY index.js /usr/src/app/
RUN npm run build

CMD [ "npm", "start" ]
