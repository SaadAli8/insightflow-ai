# Kubernetes HPA And PDB

This folder is a Kubernetes starter for the InsightFlow AI. It keeps Docker Compose
for local full-stack development, and adds Kubernetes manifests for trying:

- HPA: HorizontalPodAutoscaler, which changes replica counts from CPU usage.
- PDB: PodDisruptionBudget, which protects availability during voluntary node
  disruptions such as drains or upgrades.

Kafka is disabled in this starter config so the core API and worker flow can run
without adding a Kafka StatefulSet first.

## Build Images

From the project root:

```powershell
docker build -t local/insightflow-ai:latest backend
docker build -t local/insightflow-ai-ui:latest frontend
docker build -t local/insightflow-ai-lead-service:latest microservices/lead-service
docker build -t local/insightflow-ai-lead-signal:latest microservices/lead-signal-service
```

If you use Minikube instead of Docker Desktop Kubernetes:

```powershell
minikube image build -t local/insightflow-ai:latest backend
minikube image build -t local/insightflow-ai-ui:latest frontend
minikube image build -t local/insightflow-ai-lead-service:latest microservices/lead-service
minikube image build -t local/insightflow-ai-lead-signal:latest microservices/lead-signal-service
```

## Apply Kubernetes Manifests

First make sure your Kubernetes context exists:

```powershell
kubectl config get-contexts
```

For Docker Desktop, enable Kubernetes in Docker Desktop settings. After it is
ready, you should see a `docker-desktop` context.

For Minikube:

```powershell
minikube start --driver=docker
kubectl config use-context minikube
```

You can use the helper script:

```powershell
.\k8s\apply-local.ps1 -Context docker-desktop
```

Or apply manually:

```powershell
kubectl config use-context docker-desktop
kubectl apply -f k8s/
```

Check the workloads:

```powershell
kubectl -n insightflow-ai get pods,svc,hpa,pdb
```

The lead-generation API is exposed inside the cluster as `lead-service:8100`.
The Go website signal service is exposed inside the cluster as
`lead-signal-service:8090` and is called by `lead-service`.
If you deploy Kong in front of the cluster, route `/lead/v1` to that service.

Open the frontend locally:

```powershell
kubectl -n insightflow-ai port-forward svc/frontend 5173:5173
```

Then open:

```text
http://localhost:5173
```

## HPA Notes

HPA needs metrics-server. Check it with:

```powershell
kubectl top nodes
```

If that command does not work, install or enable metrics-server for your local
cluster first.

## Useful Commands

Watch scaling:

```powershell
kubectl -n insightflow-ai get hpa -w
kubectl -n insightflow-ai get pods -w
```

Manually test scaling:

```powershell
kubectl -n insightflow-ai scale deployment/api --replicas=4
kubectl -n insightflow-ai get pdb
```

Clean up:

```powershell
kubectl delete -f k8s/
```
