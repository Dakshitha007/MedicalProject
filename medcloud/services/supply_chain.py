import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

SBOM_OUTPUT = Path(os.getenv('SBOM_OUTPUT_PATH', '/var/medcloud/sbom.json'))
SIGNED_BUILD_DIR = Path(os.getenv('SIGNED_BUILD_DIR', '/var/medcloud/signed_builds'))


def generate_sbom(project_root: Path, output_path: Optional[Path] = None) -> Path:
    output_path = output_path or SBOM_OUTPUT
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        dependencies = []
        requirements = project_root / 'requirements.txt'
        if requirements.exists():
            for line in requirements.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                dependencies.append(line)

        sbom = {
            'project': project_root.name,
            'dependencies': dependencies,
        }
        output_path.write_text(json.dumps(sbom, indent=2), encoding='utf-8')
        return output_path
    except Exception as exc:
        logger.exception('Failed to generate SBOM: %s', exc)
        raise


def sign_build(artifact_path: Path, signature_path: Optional[Path] = None) -> Path:
    signature_path = signature_path or SIGNED_BUILD_DIR / f'{artifact_path.name}.sig'
    signature_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with artifact_path.open('rb') as f:
            content = f.read()
        import hashlib
        digest = hashlib.sha256(content).hexdigest()
        signature_path.write_text(digest, encoding='utf-8')
        return signature_path
    except Exception as exc:
        logger.exception('Failed to sign build artifact: %s', exc)
        raise


def verify_dependency_hashes(requirements_path: Path) -> List[str]:
    issues = []
    try:
        if not requirements_path.exists():
            return ['requirements.txt not found']
        for line in requirements_path.read_text(encoding='utf-8').splitlines():
            if not line or line.startswith('#'):
                continue
            if '==' not in line:
                issues.append(f'Version pin missing for dependency: {line}')
        return issues
    except Exception as exc:
        logger.exception('Failed to validate dependencies: %s', exc)
        raise
