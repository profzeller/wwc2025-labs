# WWC 2025 Labs

WWC 2025 Labs is a portable, Docker-based lab environment designed for hands-on cybersecurity instruction during the Winter Working Connections (WWC) 2025 workshop.

The project provides:

- A centralized Lab Hub web interface
- Multiple self-contained lab containers
- A simple startup workflow for instructors and students
- No per-machine configuration or environment variables

All labs are started and stopped through the Hub to ensure consistency and reliability across systems.

## Requirements

Before starting, you need:

- Git
- Docker Desktop
  - Windows / macOS: Docker Desktop 
  - Linux: Docker Engine + Docker Compose plugin

Verify installation:

```bash
docker version
docker compose version
```

## Quick Start

1. Clone the Repository

```bash
git clone https://github.com/profzeller/wwc2025-labs.git
cd wwc2025-labs
```

2. Build the Lab Images

```bash
docker compose --profile labs build
```

This builds the Hub and all lab images.
You only need to rebuild if the labs change.

3. Start the Lab Hub

```bash
docker compose up -d hub
```

Open your browser:

http://localhost:8080

## Running Labs

- Use the Lab Hub interface to start and stop labs
- Click Start & Launch to run a lab
- Only one lab can run at a time
- The Hub automatically stops other labs when starting a new one

Do **not** start lab containers manually with **docker run**.

## Stopping Everything

To stop all labs and the hub:

```bash
docker compose down
```


## Design Principles

- Portability first: works on Windows, macOS, and Linux
- No hidden configuration
- Instructor-friendly pacing
- Clear separation between control plane (Hub) and lab environments
- Open source by default

## License

This project is licensed under the **Apache License, Version 2.0**.

You are free to:

- Use the software
- Modify it
- Distribute it

Attribution is required.
See the **LICENSE** file for full details.

## Author

Created by Jason Zeller
for Winter Working Connections (WWC) 2025