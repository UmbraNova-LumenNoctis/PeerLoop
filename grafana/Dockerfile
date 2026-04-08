FROM grafana/grafana:latest

# Switch to root to install curl and copy the entrypoint
USER root

RUN apk add --no-cache curl

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Return to the default grafana user
USER grafana

ENTRYPOINT ["/entrypoint.sh"]
