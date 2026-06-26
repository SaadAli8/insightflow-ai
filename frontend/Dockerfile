FROM node:22-alpine

WORKDIR /ui

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build

EXPOSE 5173

CMD ["npm", "run", "preview"]
