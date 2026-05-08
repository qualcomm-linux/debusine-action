ARG SUITE=bookworm
FROM debian:${SUITE}

ARG BACKPORTS_SUITE=
ENV DEBIAN_FRONTEND=noninteractive

COPY base-packages.txt /tmp/base-packages.txt
COPY *.sources /tmp/debusine-builder-sources/

RUN set -eux; \
    client_suffix=""; \
    if [ -n "$BACKPORTS_SUITE" ]; then \
        cp "/tmp/debusine-builder-sources/${BACKPORTS_SUITE}-backports.sources" \
           "/etc/apt/sources.list.d/${BACKPORTS_SUITE}-backports.sources"; \
        client_suffix="/${BACKPORTS_SUITE}-backports"; \
    fi; \
    apt-get update; \
    apt-get install --no-install-recommends -y \
        $(tr '\n' ' ' < /tmp/base-packages.txt) \
        "debusine-client${client_suffix}" \
        "python3-debusine${client_suffix}"; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/* /tmp/base-packages.txt /tmp/debusine-builder-sources

WORKDIR /workspace

CMD ["bash"]
