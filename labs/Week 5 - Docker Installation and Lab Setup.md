# Docker Installation and Lab Setup

Install Docker and Docker Compose, verify that both are available, and then start the lab you are working on.

You need permission to install software on the computer. Use only the section for your operating system.

## Windows

Docker Desktop uses the Windows Subsystem for Linux 2 (WSL 2) backend for Linux containers.

### 1. Check virtualization

Open **Task Manager**, select **Performance**, and then select **CPU**.

Confirm that **Virtualization** is shown as **Enabled**.

### 2. Install or update WSL

Open **PowerShell as Administrator** and run:

```powershell
wsl --install
```

If Windows asks for a restart, restart the computer before continuing.

After restarting, open PowerShell and run:

```powershell
wsl --update
wsl --version
```

If `wsl --install` reports that WSL is already installed, continue with `wsl --update`.

### 3. Install Docker Desktop

1. Open the official installation page:  
   https://docs.docker.com/desktop/setup/install/windows-install/
2. Download **Docker Desktop for Windows** for the computer's processor.
3. Run `Docker Desktop Installer.exe`.
4. Use the WSL 2 backend when the installer offers a choice.
5. Finish the installation and restart or sign out if requested.
6. Start **Docker Desktop** from the Start menu.
7. Accept the licence agreement.
8. Wait until Docker Desktop reports that the engine is running.

Use **Linux containers** for these labs. A Docker account is not required.

## macOS

Docker Desktop runs Linux containers in a virtual machine managed by Docker.

### 1. Identify the processor

Open **Terminal** and run:

```console
uname -m
```

- `arm64` means Apple silicon.
- `x86_64` means an Intel processor.

### 2. Install Docker Desktop

1. Open the official installation page:  
   https://docs.docker.com/desktop/setup/install/mac-install/
2. Download the installer matching the processor: **Apple silicon** or **Intel**.
3. Open `Docker.dmg`.
4. Drag **Docker** to the **Applications** folder.
5. Open **Docker** from Applications.
6. Approve the requested permissions and use the recommended settings.
7. Accept the licence agreement.
8. Wait until Docker Desktop reports that the engine is running.

A Docker account is not required.

## Linux

The commands below install Docker Engine, the Docker command-line tools, Buildx, and the Docker Compose plugin.

### 1. Check for an existing installation

Run:

```console
docker version
docker compose version
```

If both commands work and `docker version` shows a **Server** section, continue to [Verify the installation](#verify-the-installation).

### 2. Check the Linux distribution

Run:

```console
cat /etc/os-release
```

Use the installation instructions for the installed distribution:

- Ubuntu: https://docs.docker.com/engine/install/ubuntu/
- Debian: https://docs.docker.com/engine/install/debian/
- Fedora: https://docs.docker.com/engine/install/fedora/
- Other supported distributions: https://docs.docker.com/engine/install/

### 3. Install Docker Engine

Download Docker's installation script:

```console
curl -fsSL https://get.docker.com -o get-docker.sh
```

Run it with administrator privileges:

```console
sudo sh get-docker.sh
```

Start Docker and configure it to start automatically:

```console
sudo systemctl enable --now docker
```

### 4. Allow the current user to run Docker

Run:

```console
sudo usermod -aG docker "$USER"
newgrp docker
```

Membership in the `docker` group grants root-equivalent access to the machine.

If `newgrp docker` does not apply the change, sign out completely and sign back in.

Docker's Linux post-installation documentation:  
https://docs.docker.com/engine/install/linux-postinstall/

## Verify the installation

Open a new PowerShell window on Windows or a new Terminal window on macOS or Linux.

Run:

```console
docker version
docker compose version
```

The installation is ready when:

- `docker version` shows both **Client** and **Server** sections;
- `docker compose version` reports Docker Compose v2.

If only the Docker client is shown, start Docker Desktop or the Docker service and run the commands again.

## Lab environments

Complete the labs in this order:

1. **Lab: Getting Started with Docker**
2. **Lab: Docker Compose Quickstart**
3. **Lab: Building Container Images**
4. **Lab: Container-Supported Development**
5. **Lab: The Containerized SDLC**

Labs 1-4 use `http://localhost:3030`. Lab 5 uses `http://dockerlabs.xyz`. All labs use the Compose project name `labspace`. Stop the current lab before starting the next one.

### Lab 1: Getting Started with Docker

Lab instructions:  
https://docs.docker.com/guides/lab-container-getting-started/

Start the lab environment:

```console
docker compose -p labspace -f oci://dockersamples/labspace-container-getting-started up -d
```

Check that the containers are running:

```console
docker ps
```

Open:

http://localhost:3030

If the page does not open after approximately 30 seconds, inspect the container output:

```console
docker compose -p labspace -f oci://dockersamples/labspace-container-getting-started logs --tail 50
```

When finished, stop and remove the lab containers:

```console
docker compose -p labspace -f oci://dockersamples/labspace-container-getting-started down
```

### Lab 2: Docker Compose Quickstart

Lab instructions:  
https://docs.docker.com/guides/lab-compose-quickstart/

Start the lab environment:

```console
docker compose -p labspace -f oci://dockersamples/labspace-compose-quickstart up -d
```

Check that the containers are running:

```console
docker ps
```

Open:

http://localhost:3030

If the page does not open after approximately 30 seconds, inspect the container output:

```console
docker compose -p labspace -f oci://dockersamples/labspace-compose-quickstart logs --tail 50
```

When finished, stop and remove the lab containers:

```console
docker compose -p labspace -f oci://dockersamples/labspace-compose-quickstart down
```

### Lab 3: Building Container Images

This lab covers image layers, build caching, `.dockerignore`, non-root users, multi-stage builds, base images, and build secrets.

Lab instructions:  
https://docs.docker.com/guides/lab-building-images/

Start the lab environment:

```console
docker compose -p labspace -f oci://dockersamples/labspace-building-images up -d
```

Check that the containers are running:

```console
docker ps
```

Open:

http://localhost:3030

If the page does not open after approximately 30 seconds, inspect the container output:

```console
docker compose -p labspace -f oci://dockersamples/labspace-building-images logs --tail 50
```

When finished, stop and remove the lab containers:

```console
docker compose -p labspace -f oci://dockersamples/labspace-building-images down
```

### Lab 4: Container-Supported Development

This lab covers running PostgreSQL in a container, bind mounts, Compose configuration, and a pgAdmin container for database inspection.

Lab instructions:  
https://docs.docker.com/guides/lab-container-supported-development/

Start the lab environment:

```console
docker compose -p labspace -f oci://dockersamples/labspace-container-supported-development up -d
```

Check that the containers are running:

```console
docker ps
```

Open:

http://localhost:3030

If the page does not open after approximately 30 seconds, inspect the container output:

```console
docker compose -p labspace -f oci://dockersamples/labspace-container-supported-development logs --tail 50
```

When finished, stop and remove the lab containers:

```console
docker compose -p labspace -f oci://dockersamples/labspace-container-supported-development down
```

### Lab 5: The Containerized SDLC

This lab covers Compose-based development, Testcontainers integration tests, a CI/CD pipeline, and deployment to a Kubernetes cluster.

Lab instructions:  
https://docs.docker.com/guides/lab-containerized-sdlc/

Start the lab environment:

```console
docker compose -p labspace -f oci://dockersamples/labspace-containerized-sdlc up -d
```

Check that the containers are running:

```console
docker ps
```

Open:

http://dockerlabs.xyz

If the page does not open after approximately 30 seconds, inspect the container output:

```console
docker compose -p labspace -f oci://dockersamples/labspace-containerized-sdlc logs --tail 50
```

When finished, stop and remove the lab containers:

```console
docker compose -p labspace -f oci://dockersamples/labspace-containerized-sdlc down
```

## Common problems

### `docker` is not recognized or not found

Close and reopen PowerShell or Terminal. If the problem remains, restart Docker Desktop or sign out and sign back in.

### Cannot connect to the Docker daemon

- Windows or macOS: start Docker Desktop and wait for the engine to finish starting.
- Linux: run `sudo systemctl status docker`. If it is stopped, run `sudo systemctl start docker`.

### WSL requires an update

Open PowerShell as Administrator and run:

```powershell
wsl --update
wsl --shutdown
```

Restart Docker Desktop afterward.

### Port 3030 is already in use

Run:

```console
docker ps
```

If another container is using port `3030`, stop the lab or container that is using it before starting the required lab.

## Official documentation

- Get Docker: https://docs.docker.com/get-started/get-docker/
- Install Docker Desktop on Windows: https://docs.docker.com/desktop/setup/install/windows-install/
- Install Docker Desktop on macOS: https://docs.docker.com/desktop/setup/install/mac-install/
- Install Docker Engine on Linux: https://docs.docker.com/engine/install/
- Install Docker Compose: https://docs.docker.com/compose/install/
- Lab: Getting Started with Docker: https://docs.docker.com/guides/lab-container-getting-started/
- Lab: Docker Compose Quickstart: https://docs.docker.com/guides/lab-compose-quickstart/
- Lab: Building Container Images: https://docs.docker.com/guides/lab-building-images/
- Lab: Container-Supported Development: https://docs.docker.com/guides/lab-container-supported-development/
- Lab: The Containerized SDLC: https://docs.docker.com/guides/lab-containerized-sdlc/
