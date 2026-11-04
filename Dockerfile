FROM anonghostid/cloudbot-base:latest AS runtime

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libmagic1 python3-venv \
    && rm -rf /var/lib/apt/lists/*
ENV PATH="/opt/venv/bin:${PATH}"

FROM runtime AS builder
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

FROM runtime
COPY --from=builder /opt/venv /opt/venv
COPY . .

CMD ["bash", "start.sh"]
