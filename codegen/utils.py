"""Shared utilities for codegen scripts."""

import gzip
import json
import os
from pathlib import Path


def botocore_metadata() -> dict[str, dict[str, str]]:
    """Load metadata for all botocore services.

    Returns:
        dict: Mapping of sdk_service -> metadata dict (signingName, endpointPrefix, serviceId, etc.)
    """
    import botocore

    botocore_data = Path(botocore.__file__).parent / "data"
    metadata = {}

    for sdk_service in os.listdir(botocore_data):
        client_path = botocore_data / sdk_service
        if not client_path.is_dir():
            continue

        # Find latest version
        versions = sorted(
            [d for d in os.listdir(client_path) if d[0].isdigit()],
            reverse=True,
        )
        if not versions:
            continue

        # Load service metadata
        service_file = client_path / versions[0] / "service-2.json.gz"
        if not service_file.exists():
            continue

        with gzip.open(service_file) as f:
            meta = json.load(f)["metadata"]
            metadata[sdk_service] = {
                "endpointPrefix": meta["endpointPrefix"],
                "serviceFullName": meta["serviceFullName"],
                "serviceId": meta["serviceId"],
                "signingName": meta.get("signingName"),
            }

    return metadata
