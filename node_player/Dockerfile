# Start with the latest LTS version of Node.js
FROM node:18 

# Create app directory
WORKDIR /usr/src/app

# Install app dependencies
# A wildcard is used to ensure both package.json AND package-lock.json are copied where available (npm@5+)
COPY package*.json ./
RUN npm ci --only=production

# Bundle app source
COPY . .

EXPOSE 80

# Run the app
ENTRYPOINT [ "node", "--require", "@opentelemetry/auto-instrumentations-node/register", "node_player.js" ]