FROM node:5.1.1

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

RUN npm install nodemon -g

CMD [ "npm", "start" ]
