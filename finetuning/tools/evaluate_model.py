"""
JARVIS Model Evaluation Tools
Compare fine-tuned model against base model
"""

import json
from pathlib import Path
from typing import List, Dict, Any


class ModelEvaluator:
    """
    Evaluate fine-tuned model against base model
    """
    
    def __init__(
        self,
        base_model: str = "qwen2.5-coder:3b",
        finetuned_model: str = "jarvis-finetuned"
    ):
        self.base_model = base_model
        self.finetuned_model = finetuned_model
        
    def load_test_set(self, test_file: Path) -> List[Dict]:
        """Load test examples"""
        tests = []
        with open(test_file, 'r') as f:
            for line in f:
                tests.append(json.loads(line))
        return tests
    
    def evaluate_response(
        self,
        user_input: str,
        expected_output: str,
        model_output: str
    ) -> Dict[str, float]:
        """
        Evaluate a single response
        Returns scores for different metrics
        """
        scores = {}
        
        scores['exact_match'] = 1.0 if model_output.strip() == expected_output.strip() else 0.0
        
        expected_keywords = set(expected_output.lower().split())
        model_keywords = set(model_output.lower().split())
        
        if expected_keywords:
            overlap = expected_keywords & model_keywords
            scores['keyword_overlap'] = len(overlap) / len(expected_keywords)
        else:
            scores['keyword_overlap'] = 0.0
        
        if '```bash' in expected_output:
            expected_cmd = expected_output.split('```bash')[1].split('```')[0].strip()
            if '```bash' in model_output:
                model_cmd = model_output.split('```bash')[1].split('```')[0].strip()
                scores['command_match'] = 1.0 if expected_cmd == model_cmd else 0.0
            else:
                scores['command_match'] = 0.0
        
        return scores
    
    def run_evaluation(
        self,
        test_file: Path,
        output_file: Path = None
    ) -> Dict[str, float]:
        """
        Run full evaluation
        
        Returns:
            Aggregate scores comparing base vs fine-tuned
        """
        try:
            import ollama
        except ImportError:
            print("Error: ollama package not installed. Run: pip install ollama")
            raise
        
        tests = self.load_test_set(test_file)
        
        results = {
            'base_model': [],
            'finetuned_model': []
        }
        
        for i, test in enumerate(tests):
            user_input = test['messages'][0]['content']
            expected = test['messages'][1]['content']
            
            print(f"Evaluating example {i+1}/{len(tests)}...")
            
            base_response = ollama.generate(
                model=self.base_model,
                prompt=user_input
            )['response']
            
            ft_response = ollama.generate(
                model=self.finetuned_model,
                prompt=user_input
            )['response']
            
            base_scores = self.evaluate_response(user_input, expected, base_response)
            ft_scores = self.evaluate_response(user_input, expected, ft_response)
            
            results['base_model'].append(base_scores)
            results['finetuned_model'].append(ft_scores)
        
        avg_scores = {}
        for metric in ['exact_match', 'keyword_overlap', 'command_match']:
            base_avg = sum(r.get(metric, 0) for r in results['base_model']) / len(results['base_model'])
            ft_avg = sum(r.get(metric, 0) for r in results['finetuned_model']) / len(results['finetuned_model'])
            
            avg_scores[f'base_{metric}'] = base_avg
            avg_scores[f'finetuned_{metric}'] = ft_avg
            avg_scores[f'{metric}_improvement'] = ft_avg - base_avg
        
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump({
                    'aggregate_scores': avg_scores,
                    'detailed_results': results
                }, f, indent=2)
        
        return avg_scores


def ab_test(prompt: str, base_model: str = "qwen2.5-coder:3b", ft_model: str = "jarvis-finetuned"):
    """Compare base model vs fine-tuned model side-by-side"""
    try:
        import ollama
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        print("Error: Required packages not installed. Run: pip install ollama rich")
        raise
    
    console = Console()
    
    base_response = ollama.generate(model=base_model, prompt=prompt)
    ft_response = ollama.generate(model=ft_model, prompt=prompt)
    
    table = Table(title=f"Prompt: {prompt}")
    table.add_column("Base Model", style="cyan")
    table.add_column("Fine-Tuned Model", style="green")
    
    table.add_row(
        base_response['response'][:500] + "..." if len(base_response['response']) > 500 else base_response['response'],
        ft_response['response'][:500] + "..." if len(ft_response['response']) > 500 else ft_response['response']
    )
    
    console.print(table)
    
    choice = input("\nWhich response is better? (base/ft/equal): ")
    return choice


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate JARVIS fine-tuned model")
    parser.add_argument(
        "--test-file",
        type=str,
        default=str(Path.home() / "jarvis/finetuning/data/dataset_val.jsonl"),
        help="Test/validation file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(Path.home() / "jarvis/finetuning/evals/results.json"),
        help="Output file for results"
    )
    parser.add_argument(
        "--base-model",
        type=str,
        default="qwen2.5-coder:3b",
        help="Base model name"
    )
    parser.add_argument(
        "--ft-model",
        type=str,
        default="jarvis-finetuned",
        help="Fine-tuned model name"
    )
    parser.add_argument(
        "--ab-test",
        type=str,
        nargs="+",
        help="Run A/B test on given prompts"
    )
    
    args = parser.parse_args()
    
    if args.ab_test:
        results = {"base": 0, "ft": 0, "equal": 0}
        for prompt in args.ab_test:
            choice = ab_test(prompt, args.base_model, args.ft_model)
            if choice in results:
                results[choice] += 1
        
        print(f"\n=== A/B Test Results ===")
        print(f"Base model preferred: {results['base']}")
        print(f"Fine-tuned model preferred: {results['ft']}")
        print(f"Equal: {results['equal']}")
    else:
        evaluator = ModelEvaluator(
            base_model=args.base_model,
            finetuned_model=args.ft_model
        )
        
        test_file = Path(args.test_file)
        if not test_file.exists():
            print(f"Error: Test file not found: {test_file}")
            exit(1)
        
        print("=== JARVIS Model Evaluation ===")
        print(f"Test file: {test_file}")
        print(f"Base model: {args.base_model}")
        print(f"Fine-tuned model: {args.ft_model}")
        print()
        
        scores = evaluator.run_evaluation(
            test_file=test_file,
            output_file=Path(args.output)
        )
        
        print("\n=== Evaluation Results ===")
        for metric, score in scores.items():
            print(f"{metric}: {score:.3f}")
