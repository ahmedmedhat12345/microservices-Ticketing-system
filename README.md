# 🎫 Customer Support Ticketing System — Microservices Architecture

An enterprise-grade, microservices-based Customer Support Ticketing System deployed on a Linux VM (Ubuntu) using VirtualBox.  
This project demonstrates a complete DevOps lifecycle featuring containerized Python/Flask services, multi-environment Docker Compose orchestration, and scalable Kubernetes cluster deployment.

---

# 🏗️ System Architecture

The application is decomposed into isolated and independent microservices:

- **Frontend Service**  
  Main entry point and UI dashboard.

- **Ticket Service**  
  Handles ticket creation, updates, and retrieval.

- **Support Service**  
  Manages admin responses and ticket resolution workflows.

- **Reporting Service**  
  Aggregates real-time system metrics and performance statistics.

- **Notification Service**  
  Automatically alerts users when ticket statuses change.

---

# ⚙️ Multi-Environment Setup (Docker Compose)

The system supports running **3 fully isolated environments simultaneously** on the same machine:

| Environment | URL | Description |
|---|---|---|
| 🟢 Development | `http://localhost:3000` | Green badge |
| 🟠 Testing | `http://localhost:3001` | Orange badge |
| 🔴 Production | `http://localhost:8080` | Red badge |

---

# 🚀 Running the Environments

Run the following commands to build and start all environments:

```bash
docker-compose -p dev  -f docker-compose.dev.yml  up --build -d
docker-compose -p test -f docker-compose.test.yml up --build -d
docker-compose -p prod -f docker-compose.prod.yml up --build -d
```

---

# 🔍 Data Independence Verification

You can verify complete database isolation between environments:

1. Submit a ticket in the **Development Environment** (`Port 3000`).
2. Copy the generated ticket ID.
3. Search for the same ticket ID in the **Testing Environment** (`Port 3001`).

You should receive a **"Not Found"** result, proving that each environment has its own isolated database.

---

# ☸️ Kubernetes Orchestration (Minikube)

For production-grade orchestration, the system is fully configured to run on Kubernetes using Minikube.

---

## 1️⃣ Prerequisites

Install the required Kubernetes CLI tools:

- `kubectl`
- `minikube`

---

## 2️⃣ Deployment Steps

### Start Minikube

```bash
minikube start --driver=docker
eval $(minikube docker-env)
```

---

### Build Docker Images Inside Minikube

```bash
docker build -t ticket-image:latest ./ticket_service
docker build -t support-image:latest ./support_service
docker build -t reporting-image:latest ./reporting_service
docker build -t notification-image:latest ./notification_service
docker build -t frontend-image:latest ./frontend
```

---

### Apply Kubernetes Manifests

```bash
kubectl apply -f k8s/
```

This deploys:

- Persistent Volume Claims (PVCs)
- Deployments
- Services

---

## 3️⃣ Accessing the Application

Wait until all pods show:

```bash
1/1 Running
```

Then expose the frontend service:

```bash
minikube service frontend-service --url
```

Open the generated URL in your browser to access the dashboard running inside Kubernetes.

---

# 🧹 Cleanup

To cleanly tear down the Kubernetes infrastructure:

```bash
kubectl delete -f k8s/
minikube stop
```
