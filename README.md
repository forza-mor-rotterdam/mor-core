# MOR Core

Voor het organiseren en beheren van Meldingen Openbare Ruimte

## Tech Stack

[Django](https://www.djangoproject.com/start/), [Turbo JS](https://turbo.hotwired.dev/), [SCSS](https://sass-lang.com/)

## Get Started 🚀

To get started, install [Docker](https://www.docker.com/)

#### We use the Makefile for commonly used commands

### Start MOR core application

https://github.com/forza-mor-rotterdam/mor-core

### Create local dns entry

Add '127.0.0.1 core.mor.local' to your hosts file

### create docker networks

Use the Makefile command:

```bash
    make create_docker_networks
```

or:

```bash
    docker network create mor_network
    docker network create mor_bridge_network
```

### Build and run Docker container

Use the Makefile command:

```bash
    make run_and_build
```

or:

```bash
    docker compose build
    docker compose up
```

To only run the docker container use:

```bash
    make run
```

This will start a webserver.
Authorize via the Django admin: http://core.mor.local:8002/admin/
You can login with the following credentials:
  - Email: admin@admin.com
  - Password: insecure
You can view the website on http://core.mor.local:8002

### Frontend

Use the Makefile command:

```bash
    make run_frontend
```

or in terminal go to 'app/frontend' and start front-end and watcher by typing

```bash
    npm install
    npm run watch
```

### Code style
Pre-commit is used for formatting and linting
Make sure pre-commit is installed on your system
```bash
    brew install pre-commit
```
and run
```bash
    pre-commit install
```

To manually run the pre-commit formatting run

```bash
    make format
```
Pre-commit currently runs black, flake8, autoflake, isort and some pre-commit hooks. Also runs prettier for the frontend.

### Linking other applications to MOR-CORE

To link the other applications to MOR-CORE you need to create the users for those applications and the application-links in MOR-CORE.
Applications should be created automatically with the "create_applicaties" command. You can also run this command using:
```
make create_applicaties
```

#### Manual steps
 - Go to the Django Admin in MOR-CORE
 - Users - Add new users for the applications, for example: fixer_username@forzamor.nl for fixer, the password is the default we use.
 - Applicaties -  Create a new application with the following data (fixer in this example):
   * name: FixeR
   * basis url: http://fixer.mor.local:8004
   * gebruiker: fixer_username@forzamor.nl
   * applicatie gebruiker naam: core_username@forzamor.nl
   * applicatie gebruiker wachtwoord: default password

In the corresponsing application you need to create a user for MOR-CORE
So in this example go to the FixeR Django Admin
 - Users - Add a new user with email: core_username@forzamor.nl , password: default password

After adding these 3 things you should be able to "click save and continue editing" on the MOR-CORE application-link and see the "Connectie met de applicatie is gelukt" message.
