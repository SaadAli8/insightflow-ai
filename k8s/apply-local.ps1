param(
    [ValidateSet("docker-desktop", "minikube")]
    [string] $Context = "docker-desktop",
    [switch] $SkipBuild
)

$ErrorActionPreference = "Stop"

function Test-Command($Name) {
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Test-Command "kubectl")) {
    throw "kubectl is not installed or not available in PATH."
}

if (-not $SkipBuild) {
    if ($Context -eq "minikube") {
        if (-not (Test-Command "minikube")) {
            throw "minikube is not installed or not available in PATH."
        }
        minikube image build -t local/insightflow-ai:latest backend
        minikube image build -t local/insightflow-ai-ui:latest frontend
    }
    else {
        docker build -t local/insightflow-ai:latest backend
        docker build -t local/insightflow-ai-ui:latest frontend
    }
}

$contexts = kubectl config get-contexts -o name 2>$null
if (-not ($contexts -contains $Context)) {
    if ($Context -eq "docker-desktop") {
        throw "Kubernetes context 'docker-desktop' was not found. Enable Kubernetes in Docker Desktop Settings, wait until it is running, then rerun this script."
    }
    throw "Kubernetes context '$Context' was not found. Run 'minikube start --driver=docker' first, then rerun this script."
}

kubectl config use-context $Context | Out-Host
kubectl apply -f k8s/
kubectl -n insightflow-ai get pods,svc,hpa,pdb

Write-Host ""
Write-Host "To open the app, run:"
Write-Host "kubectl -n insightflow-ai port-forward svc/frontend 5173:5173"

