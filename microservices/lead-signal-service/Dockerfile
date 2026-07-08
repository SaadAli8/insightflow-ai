FROM golang:1.22-alpine AS build

WORKDIR /src
COPY go.mod .
COPY cmd ./cmd
RUN go build -o /out/lead-signal-service ./cmd/server

FROM alpine:3.20

WORKDIR /app
COPY --from=build /out/lead-signal-service /app/lead-signal-service
EXPOSE 8090

CMD ["/app/lead-signal-service"]
