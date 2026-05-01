# GitOps Manifests Repository

This folder is the Kubernetes source of truth watched by Argo CD.

Production flow:

1. CI publishes an image.
2. A manifest PR updates the deployment image or configuration.
3. Human review merges the PR.
4. Argo CD syncs the Git state into the cluster.

The broken starting state is intentional: `deployment.yaml` does not include `REQUIRED_GREETING`.
