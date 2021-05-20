FROM python:3.9.5-alpine3.13

# can't get cryptography==3.4.7 to install successfully
# with rust
ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1

RUN apk add --no-cache \
    bash \
    build-base \
    libffi-dev \
    musl-dev \
    openssl-dev \
    python3-dev

COPY requirements.txt /app/

RUN pip3 install -r /app/requirements.txt

COPY . /app/

RUN ln -s /app/Binance\ Detect\ Moonings.py /app/bot.py

WORKDIR /app

CMD ["sh", "-c", "bash docker/prep.sh && python3 bot.py --debug"]
