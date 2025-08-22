# Use Node 20 on a small Alpine image
FROM node:20-alpine

# Create app directory
WORKDIR /app

# Install deps
COPY package*.json ./
RUN npm ci --omit=dev || npm install --omit=dev

# Copy the rest
COPY . .

# Railway will inject PORT; your server uses process.env.PORT
EXPOSE 3000

# Start the server
CMD ["node", "server.mjs"]
