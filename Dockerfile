FROM anonghostid/cloudbot-base:latest

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libmagic1 python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]
