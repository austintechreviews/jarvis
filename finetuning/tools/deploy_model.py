"""
Model Deployment for JARVIS - Deploy fine-tuned models to Ollama
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class ModelDeployer:
    def __init__(self, models_dir: Path = None):
        self.models_dir = models_dir or Path.home() / "jarvis" / "finetuning" / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.models_dir / "registry.json"
    
    def _get_registry(self) -> Dict:
        if self.registry_file.exists():
            with open(self.registry_file, "r") as f:
                return json.load(f)
        return {}
    
    def _save_registry(self, registry: Dict):
        with open(self.registry_file, "w") as f:
            json.dump(registry, f, indent=2)
    
    def create_modelfile(self, gguf_path: Path, model_name: str = "jarvis-finetuned",
                         version: str = "v1") -> Path:
        modelfile_path = self.models_dir / f"Modelfile_{model_name}_{version}"
        content = f"FROM {gguf_path}\n\n"
        content += "TEMPLATE " + chr(34)*3 + "\n"
        content += "{{ .System }}\n\n"
        content += "{{ .Prompt }}\n\n"
        content += "{{ .Assistant }}\n"
        content += chr(34)*3 + "\n\n"
        content += "PARAMETER temperature 0.3\n"
        content += "PARAMETER top_p 0.9\n"
        content += "PARAMETER top_k 40\n"
        content += "PARAMETER num_ctx 8192\n"
        content += "PARAMETER stop " + chr(34) + "</sys>" + chr(34) + "\n"
        content += "PARAMETER stop " + chr(34) + "</user>" + chr(34) + "\n"
        content += "PARAMETER stop " + chr(34) + "</assistant>" + chr(34)
        with open(modelfile_path, "w") as f:
            f.write(content)
        return modelfile_path
    
    def deploy_to_ollama(self, model_name: str, version: str, modelfile_path: Path) -> bool:
        tag = f"{model_name}:{version}"
        command = ["ollama", "create", tag, "-f", str(modelfile_path)]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error deploying: {result.stderr}")
            return False
        print(f"Successfully deployed {tag}")
        registry = self._get_registry()
        registry[tag] = {
            "name": model_name,
            "version": version,
            "created_at": datetime.now().isoformat(),
            "modelfile": str(modelfile_path)
        }
        self._save_registry(registry)
        return True
    
    def deploy(self, gguf_path: Path, model_name: str = "jarvis-finetuned",
               version: str = "v1") -> bool:
        modelfile_path = self.create_modelfile(gguf_path, model_name, version)
        return self.deploy_to_ollama(model_name, version, modelfile_path)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Deploy JARVIS model to Ollama")
    parser.add_argument("--gguf", type=str, required=True)
    parser.add_argument("--name", type=str, default="jarvis-finetuned")
    parser.add_argument("--version", type=str, default="v1")
    args = parser.parse_args()
    deployer = ModelDeployer()
    success = deployer.deploy(Path(args.gguf), args.name, args.version)
    if success:
        print(f"\nDeployment complete! Test with: ollama run {args.name}:{args.version}")
    else:
        print("\nDeployment failed!")
        exit(1)