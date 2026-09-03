# Quickstart: k8s

Kubernetes manifests.

## Apply

```bash
kubectl apply -f k8s/
```

## Verify

```bash
kubectl get all -l app=k8s
```

## Remove

```bash
kubectl delete -f k8s/
```

> These manifests are for learning. See [../DEPLOYMENT.md](../DEPLOYMENT.md)
> for production hardening guidance.
