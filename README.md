# Proxy Management Application

## Table of Contents
- [Proxy Management Application](#proxy-management-application)
  - [Table of Contents](#table-of-contents)
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
  - [Usage](#usage)
  - [Project Structure](#project-structure)
    - [Packages](#packages)
    - [Modules](#modules)
  - [Docker Deployment](#docker-deployment)
  - [Contributing](#contributing)
  - [License](#license)
  - [Authors](#authors)

## Description

Proxy Management System for interactions with proxies based on LTE modems. This application provides a robust and efficient way to manage and interact with LTE modems, allowing for seamless proxy management.

## Features

- FastAPI for building APIs
- SQLAlchemy for database interactions
- Alembic for database migrations
- Authentication using JWT and OAuth
- WebSocket support
- Environment configuration using `python-dotenv`
- Command-line interface using Click
- Templating with Jinja2
- HTTP client with HTTPX
- Google authentication

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/sergey-vernyk/proxy-management.git
    cd proxy-management/backend
    ```

2. Install dependencies using Poetry:
    ```sh
    poetry install
    ```

3. Create and configure the environment file:
    ```sh
    cp .env.example .env
    ```

4. Apply database migrations:
    ```sh
    poetry run alembic upgrade head
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
    poetry run proxy-conf-users [OPTIONS] COMMAND [ARGS]
```
Commands:
- `create-user-list`: Create a user list file with proxy credentials
- `delete-from-user-list`: Delete user credentials from the user list file
- `get-from-user-list`: Display user credentials from the user list file
- `insert-into-user-list`: Insert new user credentials into the user list
  
Options:
- `--env-file TEXT`: Location or URL of the environment configuration file
- `-u, --username TEXT`: Username for authenticating if the provided 'env_file' is URL.
- `-pass, --password TEXT`: Password for authenticating if the provided

#### *Start the socket server, stop the server, show its logs and accepted connections*
```sh
    poetry run socket-server [OPTIONS] ENV_FILE COMMAND [ARGS]
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
    poetry run proxy-conf-protocols [OPTIONS] COMMAND [ARGS]
```
Commands:
- `create-connection-protocol`: Create one line for protocol in the proxy conf file (e.g. proxy -n -a -p49153 -i192.168.1.105 -e192.168.8.100)

Options:
- `--env-file TEXT`: Location or URL of the environment configuration file
- `-u, --username TEXT`: Username for authenticating if the provided 'env_file' is URL
- `-pass, --password TEXT`: Password for authenticating if the provided

### *Run uvicorn server with parameters*
```sh
    poetry run web-server [OPTIONS] COMMAND [ARGS]
```
Commands:
- `runserver`: Run the FastAPI server with the provided options

## Usage

1. Run the application:
    ```sh
    poetry run uvicorn main:app --reload
    ```

2. Access the application at `http://127.0.0.1:8000`.

## Project Structure
### Packages
- `auth/`: Authentication module
- `cli/`: Command-line interface module
- `modems/`: Modems module
- `users/`: Users module
- `common/`: Common utilities and helpers
- `sockets/`: Modules with SocketClient and SocketServer classes and related functions
- `logs/`: Logging configuration and files with logging data
- `migrations/`: Database migrations files and configuration
- `static/`: JavaScript, CSS and images
- `templates/`: HTML files
- `deploy_config/`: Files used for deployment

### Modules
- `config.py`: Configuration settings
- `conn_utils.py`: Connection utilities
- `db_connection.py`: Database connection setup
- `main.py`: Main entry point of the application
- `security.py`: Security functions (passwords, tokens, encrypting, etc)
- `validators.py`: Custom validators
- `modem_api.py`: API for LTE modem control
- `dependencies.py`: Functions and classes used as dependency (DI) in the FastAPI routers
- `conftest.py`: Configuration file for Pytest
- `exceptions.py`: Custom exceptions

## Docker Deployment

1. Build the Docker image:
    ```sh
    docker build -t proxy-management .
    ```

2. Run the Docker container:
    ```sh
    docker run -d -p 8000:8000 --env-file .env proxy-management
    ```

## Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature-branch`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature-branch`)
5. Create a new Pull Request

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Authors

Sergey Vernigora volt.awp.dev@gmail.com