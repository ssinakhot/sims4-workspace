FROM mcr.microsoft.com/devcontainers/base:noble

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y vim wget && \
    mkdir -p -m 755 /etc/apt/keyrings && \
    wget -nv -O /etc/apt/keyrings/githubcli-archive-keyring.gpg https://cli.github.com/packages/githubcli-archive-keyring.gpg && \
    chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
    apt-get update && \
    apt-get install -y gh && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.7 python3.7-distutils python3.7-dev python3.7-venv && \
    ln -sf /usr/bin/python3.7 /usr/local/bin/python && \
    ln -sf /usr/bin/python3.7 /usr/local/bin/python3 && \
    wget -qO /tmp/get-pip.py https://bootstrap.pypa.io/pip/3.7/get-pip.py && \
    python /tmp/get-pip.py && \
    rm /tmp/get-pip.py && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER vscode

RUN curl -fsSL https://claude.ai/install.sh | bash