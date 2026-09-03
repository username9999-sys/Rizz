# Quickstart: monitoring

Kubernetes manifests.

## Apply

```bash
kubectl apply -f monitoring/
```

## Verify

```bash
kubectl get all -l app=monitoring
```

## Remove

```bash
kubectl delete -f monitoring/
```

> These manifests are for learning. See [../DEPLOYMENT.md](../DEPLOYMENT.md)
> for production hardening guidance.
