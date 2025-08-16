FROM python:3.12.5-alpine

LABEL org.opencontainers.image.source=https://github.com/sergey-vernyk/ProxyManagement
LABEL org.opencontainers.image.description="Image with backend and frontend implementation for proxy management"
LABEL org.opencontainers.image.licenses=MIT

ENV PYTHONUNBUFFERED=1 
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /usr/src/app/backend
EXPOSE 8000

RUN apk update && \
    apk add --update --no-cache postgresql-client \
    build-base postgresql-dev linux-headers curl vim

ARG user=proxy

RUN adduser $user --disabled-password

RUN mkdir -p /usr/src/app/backend/static && \
    chown -R $user /usr/src/app/backend /usr/src/app/backend/static

USER $user
ADD ./pyproject.toml ./poetry.lock ./
ENV PATH="$PATH:/home/$user/.local/bin"
    
RUN pip install --upgrade pip && \
    pip install poetry && \
    python -m poetry install --no-root --no-cache --no-interaction
    
COPY . /usr/src/app/backend

CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--reload"]
