"""
JARVIS Model Deployment Tools
Convert fine-tuned model to Ollama format and deploy
"""

import subprocess
from pathlib import Path
from datetime import datetime


class ModelDeployer:
    """Deploy fine-tuned model to Ollama"""
    
    def __init__(self, model_dir: Path = None):
        self.model_dir = model_dir or Path.home() / "jarvis" / "finetuning" / "models"
        
    def create_modelfile(self, gguf_path: Path, output_path: Path, model_name: str = "jarvis-finetuned", version: str = "v1"):
        """Create Ollama Modelfile"""
        content = f"""FROM {gguf_path}

TEMPLATE \"\"\"<|im_start|>system
{{{{ .System }}}}<|im_end|>
<|im_start|>user
{{{{ .Prompt }}}}<|im_end|>
<|im_start|>assistant
\"\"\"

PARAMETER temperature 0.3
PARAMETER num_ctx 8192
PARAMETER top_p 0.9
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|im_start|>"
"""
        output_path.write_text(content)
        return output_path
    
    def deploy_to_ollama(self, model_name: str, version: str, modelfile_path: Path) -> bool:
        """
        Deploy model to Ollama
        
        Args:
            model_name: Name for the model
            version: Version tag
            modelfile_path: Path to Modelfile
            
        Returns:
            True if successful
        """
        tag = f"{model_name}:{version}"
        
        cmd = ["ollama", "create", tag, "-f", str(modelfile_path)]
        print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error deploying: {result.stderr}")
            return False
        
        print(f"Successfully deployed {tag}")
        return True
    
    def deploy(self, gguf_path: Path, model_name: str = "jarvis-finetuned", version: str = "v1") -> bool:
        """
        Full deployment pipeline
        
        Args:
            gguf_path: Path to GGUF model file
            model_name: Name for the model
            version: Version tag
            
        Returns:
            True if successful
        """
        modelfile_path = self.model_dir / "Modelfile"
        
        print(f"Creating Modelfile at {modelfile_path}...")
        self.create_modelfile(gguf_path, modelfile_path, model_name, version)
        
        print(f"Deploying to Ollama as {model_name}:{version}...")
        return self.deploy_to_ollama(model_name, version, modelfile_path)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy JARVIS fine-tuned model to Ollama")
    parser.add_argument(
        "--gguf",
        type=str,
        required=True,
        help="Path to GGUF model file"
    )
    parser.add_argument(
        "--name",
        type=str,
        default="jarvis-finetuned",
        help="Model name"
    )
    parser.add_argument(
        "--version",
        type=str,
        default="v1",
        help="Model version"
    )
    
    args = parser.parse_args()
    
    deployer = ModelDeployer()
    
    success = deployer.deploy(
        gguf_path=Path(args.gguf),
        model_name=args.name,
        version=args.version
    )
    
    if success:
        print(f"\nDeployment complete! Test with: ollama run {args.name}:{args.version}")
    else:
        print("\nDeployment failed!")
        exit(1)
