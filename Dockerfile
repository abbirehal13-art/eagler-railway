FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
        wget \
        curl \
        git \
        python3 \
        python3-pip \
        neofetch && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN wget -qO /bin/ttyd \
    https://github.com/tsl0922/ttyd/releases/download/1.7.3/ttyd.x86_64 && \
    chmod +x /bin/ttyd

RUN pip3 install --break-system-packages websockets==15.0.1

RUN echo "neofetch" >> /root/.bashrc && \
    echo "cd /root" >> /root/.bashrc

COPY bridge.py /app/bridge.py

EXPOSE 8000

CMD ["python3", "/app/bridge.py"]
