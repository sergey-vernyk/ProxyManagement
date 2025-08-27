# Proxy Management Application

## Table of Contents
- [Proxy Management Application](#proxy-management-application)
  - [Description](#description)
  - [Features](#features)
  - [Installation](#installation)
  - [Endpoints](#endpoints)
    - [Authentication](#authentication)
    - [Modems](#modems)
    - [Users](#users)
  - [Command Line Interface (CLI)](#command-line-interface-cli)
      - [*CRUD operations for user proxy credentials*](#crud-operations-for-user-proxy-credentials)
      - [*Start the socket server, stop the server, show its logs and accepted connections*](#start-the-socket-server-stop-the-server-show-its-logs-and-accepted-connections)
      - [*Create different connection protocol types for proxy (http, socks, ftp, etc.)*](#create-different-connection-protocol-types-for-proxy-http-socks-ftp-etc)
    - [*Run uvicorn server with parameters*](#run-uvicorn-server-with-parameters)
  - [Run the FastAPI server](#run-the-fastapi-server)
  - [Project Structure](#project-structure)
  - [Docker Deployment With PostgreSQL](#docker-deployment-with-postgresql)
  - [Contributing](#contributing)
  - [License](#license)
  - [Authors](#authors)

## Description

Proxy Management System for interactions with proxies based on LTE modems using 3proxy. This application provides efficient way to manage and interact with LTE Huawei modems, allowing for seamless proxy management.

## Features

- FastAPI for building APIs
- SQLAlchemy for database interactions
- Alembic for database migrations
- Authentication with JWT and Google OAuth2
- WebSocket to handle IP address changes with long modem response times
- Command-line interface (Click) for both client and server
- Lightweight web interface (Jinja2, HTML, CSS, and jQuery). API ready for any JS framework

## Installation

1. Clone the repository:
    ```sh
    $ git clone https://github.com/sergey-vernyk/ProxyManagement.git
    $ cd ProxyManagement
    ```

2. Install dependencies using Poetry:
    ```sh
    $ poetry install
    ```

3. Create and configure the environment file:
    ```sh
    $ cp .env.example src/proxy_management/.env
    ```

4. Apply database migrations:
    ```sh
    $ poetry run alembic upgrade head
    ```

## Endpoints

### Authentication

- `POST /auth/login`: User basic login (email, password)
- `GET /auth/login/google`: Initiate Google authorization (redirects to the Google authorization page after the user clicks on the button)
- `GET /auth/callback`: Handles Google authorization after a user authorizes in Google with their Google credentials
- `POST /auth/revoke/google`: Revoke Google authentication
- `POST /auth/registration`: User registration
- `POST /auth/reset_password`: Initiate password reset
- `POST /auth/reset_password_confirm`: Confirm password reset
- `POST /auth/send_verification_email/`: Send an email with OTP for verification after registration
- `POST /auth/compare_codes/`: Compare OTP from the user and OTP saved in the database
- `POST /auth/verify_captcha`: Backend Cloudflare reCaptcha verification
- `POST /auth/logout`: User logout

### Modems

- `GET /modems/`: List all modems
- `POST /modems/`: Create a new modem
- `GET /modems/{ip}`: Get details of a specific modem by IP
- `PUT /modems/{ip}`: Update a specific modem by IP
- `DELETE /modems/{ip}`: Delete a specific proxy
- `GET /modems/change_ip_urls/{email}`: Get URL for a modem (for rebooting it) for a user with specific email

### Users

- `POST /users/`: Create a user
- `GET /users/`: Get all users
- `GET /users/{email}`: Get details of a specific user by email
- `PUT /users/{email}`: Update a specific user by email
- `DELETE /users/{email}`: Delete a specific user by email

## Command Line Interface (CLI)

#### *CRUD operations for user proxy credentials*
```sh
$ proxy-conf-users [OPTIONS] ENV_FILE COMMAND [ARGS]
```
Arguments:
- `env_file`: Location or URL of the environment configuration file

Commands:
- `create-user-list`: Create a user list file with proxy credentials
- `delete-from-user-list`: Delete user credentials from the user list file
- `get-from-user-list`: Display user credentials from the user list file
- `insert-into-user-list`: Insert new credentials into the user list file
  
Options:
- `-u, --username TEXT`: Username for authenticating if the provided 'env_file' is URL
- `-pass, --password TEXT`: Password for authenticating if the provided 'env_file' is URL

#### *Start the socket server, stop the server, show its logs and accepted connections*
```sh
$ socket-server [OPTIONS] ENV_FILE COMMAND [ARGS]
```
Commands:
- `connection-number`: Show the current numbers of accepted connection to the socket server
- `logs`: Show logs for the socket server
- `run`: Run the socket server with provided host and port
- `stop`: Stop the running socket server

Options:
- `-u, --username TEXT`: Username for authenticating if the provided 'env_file' is URL
- `--pass, --password TEXT`: Password for authenticating if the provided 'env_file' is URL

#### *Create different connection protocol types for proxy (http, socks, ftp, etc.)*
```sh
$ proxy-conf-protocols [OPTIONS] COMMAND [ARGS]
```
Commands:
- `create-connection-protocol`: Create one line for protocol in the proxy conf file (e.g. proxy -n -a -p49153 -i192.168.1.105 -e192.168.8.100)

Options:
- `--env-file TEXT`: Location or URL of the environment configuration file
- `-u, --username TEXT`: Username for authenticating if the provided 'env_file' is URL
- `-pass, --password TEXT`: Password for authenticating if the provided

### *Run uvicorn server with parameters*
```sh
$ web-server [OPTIONS] COMMAND [ARGS]
```
Commands:
- `runserver`: Run the FastAPI server with the provided options

## Run the FastAPI server

1. Run the application:
    ```sh
    $ cd src/proxy_management
    $ uvicorn main:app --reload
    ```

2. Access the application at `http://127.0.0.1:8000`.

## Project Structure
```sh
.
├── alembic.ini
├── Dockerfile
├── LICENSE
├── poetry.lock
├── pyproject.toml
├── README.md
├── ruff.toml
├── src
│   └── proxy_management
│       ├── auth
│       │   ├── auth_bearer.py
│       │   ├── crud.py
│       │   ├── __init__.py
│       │   ├── otp
│       │   │   ├── crud.py
│       │   │   ├── __init__.py
│       │   │   ├── models.py
│       │   │   ├── schemas.py
│       │   │   └── utils.py
│       │   ├── router_api.py
│       │   ├── router_templates.py
│       │   ├── schemas.py
│       │   ├── tasks.py
│       │   └── utils.py
│       ├── cli
│       │   ├── __init__.py
│       │   ├── proxy_protocol_types.py
│       │   ├── proxy_userlist.py
│       │   ├── schemas.py
│       │   ├── socket_server.py
│       │   ├── utils.py
│       │   └── web_server.py
│       ├── common
│       │   ├── decorators.py
│       │   ├── __init__.py
│       │   ├── sending_email.py
│       │   └── utils.py
│       ├── config.py
│       ├── conn_utils.py
│       ├── db_connection.py
│       ├── dependencies.py
│       ├── exceptions.py
│       ├── __init__.py
│       ├── logs
│       │   ├── __init__.py
│       │   └── logging_conf.py
│       ├── main.py
│       ├── migrations
│       │   ├── env.py
│       │   ├── README
│       │   └── script.py.mako
│       ├── modem_api.py
│       ├── modems
│       │   ├── crud.py
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── router.py
│       │   ├── router_templates.py
│       │   ├── router_ws.py
│       │   └── schemas.py
│       ├── security.py
│       ├── sockets
│       │   ├── async_client.py
│       │   ├── async_server.py
│       │   └── __init__.py
│       ├── static
│       │   ├── css
│       │   │   ├── authentication.css
│       │   │   ├── base.css
│       │   │   ├── change_ip.css
│       │   │   ├── index.css
│       │   │   ├── proxies.css
│       │   │   ├── registration.css
│       │   │   ├── reset_password_confirm.css
│       │   │   ├── reset_password.css
│       │   │   └── verify_otp.css
│       │   ├── img
│       │   │   └── favicon.png
│       │   └── js
│       │       ├── authentication.js
│       │       ├── change_ip.js
│       │       ├── check_opened_modal_windows.js
│       │       ├── delete_account.js
│       │       ├── disconnect_google_account.js
│       │       ├── get_cookies.js
│       │       ├── logout.js
│       │       ├── registration.js
│       │       ├── reset_password_confirm.js
│       │       ├── reset_password.js
│       │       ├── verify_cf_captcha.js
│       │       └── verify_otp.js
│       ├── templates
│       │   ├── authentication.html
│       │   ├── base.html
│       │   ├── change_ip.html
│       │   ├── email_verification.html
│       │   ├── index.html
│       │   ├── proxies.html
│       │   ├── registration.html
│       │   ├── reset_password_confirm.html
│       │   ├── reset_password_email.html
│       │   ├── reset_password.html
│       │   ├── verify_email_deferred.html
│       │   └── verify_otp.html
│       ├── users
│       │   ├── crud.py
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── router.py
│       │   ├── schemas.py
│       │   └── utils.py
│       ├── validators.py
│       └── wait-for.sh
└── tests
    ├── conftest.py
    ├── __init__.py
    ├── mocks.py
    └── test_auth.py
```

## Docker Deployment with PostgreSQL

1. Build the Docker image:
  ```sh
  $ docker build -t proxy-management .
  ```
2. Create docker network:
  ```sh
  $ docker network create proxy-management-network
  ```
  it will create the `bridge` type of docker network that we need to use for the FastAPI server connections with the PostgreSQL server.

3. Run PostgreSQL server:
  ```sh
  $ docker run \
      --name proxy-management-db \
      -e POSTGRES_PASSWORD=mysecretpassword \
      -e PGDATA=/var/lib/postgresql/data/pgdata \
      -v /tmp/postgres_data:/var/lib/postgresql/data \
      -e POSTGRES_USER=proxy_admin \
      -e POSTGRES_DB=proxies \
      --network=proxy-management-network postgres:16.3-alpine
  ```
  **Note:** is required to assign to `DATABASE_URL` environment variable the value: `postgresql://proxy_admin:mysecretpassword@proxy-management-db:5432/proxies` where `proxy-management-db` is the value defined while running PostgreSQL server above. With `127.0.0.1` it won't work as expected. The FastAPI server won't be able to connect to PostgreSQL server. You can choose any credentials for the PostgreSQL server as you want.
  `/tmp/postgres_data` in `-v /tmp/postgres_data:/var/lib/postgresql/data` can be mount to other places you want.

4. Run the Docker container:
  ```sh
  $ docker run \
      -w /app/src/proxy_management \
      -p 8000:8000 \
      --name proxy-management-fastapi \
      --network=proxy-management-network \
      --env-file src/proxy_management/.env proxy-management uvicorn main:app --host 0.0.0.0
  ```
  You can chose `.env` file from other location where actual `.env` file is located.

5. And after this you will see:
  ```sh
  INFO:     Started server process [1]
  INFO:     Waiting for application startup.
  INFO:     Application startup complete.
  INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
  ```

  Open a browser on `http://127.0.0.1:8000` and you will see the home page.

## Contributing
We welcome contributions of all kinds — bug fixes, new features, documentation improvements, or suggestions!

**To contribute:**
- Fork this repository to your own GitHub account.
- Clone your fork locally and create a new branch:

```bash
$ git clone https://github.com/sergey-vernyk/ProxyManagement.git
$ git checkout -b my-feature-branch
```
- Make your changes and follow the existing coding style.
- Test your changes if applicable.
- Commit your changes with a clear message:

```bash
$ git commit -m "Add brief description of changes"
```
- Push your branch to your fork:

```bash
$ git push origin my-feature-branch
```
- Open a **Pull Request** from your branch to the main repository, explaining what you changed and why.

We appreciate all contributions and will review pull requests as quickly as possible. Be respectful and constructive when interacting with others in this project.

## License
This project is licensed under the MIT License. See the LICENSE file for details.