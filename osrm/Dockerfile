# syntax=docker/dockerfile:1
#
# Builds OSRM pedestrian-routing data for Czech Republic directly in the
# image at build time. This replaces the manual scripts/prepare-osrm-cz.sh
# step — no local Docker run / pre-processing is required before deploying.
#
# Build resources: this downloads a ~300-400 MB OSM extract and runs
# osrm-extract/partition/customize, which needs a few GB of RAM and a few
# minutes. Fine for local `docker compose build` or a cloud build service;
# too heavy for constrained/free build environments.

FROM ghcr.io/project-osrm/osrm-backend:v5.27.1 AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /data

RUN curl -L --fail --retry 3 -o czech-republic-latest.osm.pbf \
    https://download.geofabrik.de/europe/czech-republic-latest.osm.pbf

RUN osrm-extract -p /opt/foot.lua czech-republic-latest.osm.pbf \
    && osrm-partition czech-republic-latest.osrm \
    && osrm-customize czech-republic-latest.osrm \
    && rm -f czech-republic-latest.osm.pbf

FROM ghcr.io/project-osrm/osrm-backend:v5.27.1

WORKDIR /data
COPY --from=builder /data/czech-republic-latest.osrm* /data/

EXPOSE 5000

CMD ["osrm-routed", "--algorithm", "mld", "--max-table-size", "1000", "/data/czech-republic-latest.osrm"]
