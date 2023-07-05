docker run \
  -e AGENT_MODE=flow \
  -e GRAFANA_CLOUD_API_KEY="<cloud_api_key>" \
  -e GRAFANA_CLOUD_PROMETHEUS_URL="<cloud_prom_url>" \
  -e GRAFANA_CLOUD_PROMETHEUS_USERNAME="<cloud_prom_username>" \
  -e GRAFANA_CLOUD_LOKI_URL="<cloud_loki_url>" \
  -e GRAFANA_CLOUD_LOKI_USERNAME="<cloud_loki_username>" \
  -e GRAFANA_CLOUD_TEMPO_ENDPOINT="<cloud_tempo_endpoint>" \
  -e GRAFANA_CLOUD_TEMPO_USERNAME="<cloud_tempo_username>" \
  -v "$(pwd)"/agent.river:/etc/agent/config.river \
  -p 12345:12345 \
  grafana/agent:latest \
    run --server.http.listen-addr=0.0.0.0:12345 /etc/agent/config.river
