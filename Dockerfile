FROM python:3.12.5-alpine AS builder

LABEL org.opencontainers.image.source=https://github.com/sergey-vernyk/ProxyManagement
LABEL org.opencontainers.image.description="Image with backend and frontend implementation for proxy management"
LABEL org.opencontainers.image.licenses=MIT

ENV PYTHONUNBUFFERED=1 
ENV PYTHONDONTWRITEBYTECODE=1

RUN apk update && \
    apk add --update --no-cache \
    build-base postgresql-dev linux-headers curl

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /usr/src/app
COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.in-project true && \
    poetry lock && \
    poetry install --no-root --no-cache --no-interaction --without dev

FROM python:3.12.5-alpine AS prod

ARG user=proxy
RUN adduser $user --disabled-password

WORKDIR /usr/src/app

COPY . .
COPY --from=builder /usr/src/app/.venv .venv

RUN mkdir -p ./assets && chown -R $user ./assets
ENV PATH="/usr/src/app/backend/.venv/bin:$PATH"

USER $user
EXPOSE 8000