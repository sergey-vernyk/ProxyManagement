FROM python:3.12.5-alpine

LABEL org.opencontainers.image.source=https://github.com/sergey=vernyk/ProxyManagement
LABEL org.opencontainers.image.description="Image with backend and frontend implementation for proxy management."
LABEL org.opencontainers.image.licenses=MIT

ENV PYTHONUNBUFFERED=1 
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /usr/src/app/backend
EXPOSE 8000

ARG user=proxy

RUN adduser $user --disabled-password

RUN mkdir -p /usr/src/app/backend/static && \
    chown -R $user /usr/src/app/backend /usr/src/app/backend/static
    
RUN apk update && \
    apk add --update --no-cache postgresql-client \
    build-base postgresql-dev linux-headers curl vim && \
    pip install --upgrade pip && \
    pip install poetry
    
ENV PATH "$PATH:/home/$user/.local/bin"
COPY . /usr/src/app/backend

USER $user
RUN poetry install --no-root --no-cache --no-interaction

CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--reload"]