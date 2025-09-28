# cli_enhanced.py
"""
Enhanced CLI interface with rich formatting and interactive features
Modern command-line experience for Invisible Plagiarism Toolkit
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional
import json
from datetime import datetime

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    from rich.tree import Tree
    from rich.syntax import Syntax
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    
from invisible_manipulator import InvisibleManipulator
from advanced_analyzer import AdvancedAnalyzer
from logger_config import get_project_logger

class EnhancedCLI:
    """Enhanced command-line interface with rich formatting"""
    
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.logger = get_project_logger()
        
    def print_banner(self):
        """Print application banner"""
        if not RICH_AVAILABLE:
            print("🔮 Invisible Plagiarism Toolkit v1.1")
            print("Advanced Steganographic Document Manipulation")
            return
            
        banner = """
[bold blue]🔮 Invisible Plagiarism Toolkit[/bold blue]
[dim]Advanced Steganographic Document Manipulation System[/dim]

[yellow]⚠️  For Educational and Research Purposes Only[/yellow]
"""
        self.console.print(Panel(banner, border_style="blue"))
    
    def print_status(self, message: str, status: str = "info"):
        """Print status message with appropriate styling"""
        if not RICH_AVAILABLE:
            print(f"[{status.upper()}] {message}")
            return
            
        colors = {
            "info": "blue",
            "success": "green", 
            "warning": "yellow",
            "error": "red",
            "processing": "cyan"
        }
        
        color = colors.get(status, "white")
        self.console.print(f"[{color}]{message}[/{color}]")
    
    def show_processing_progress(self, tasks: List[str]):
        """Show processing progress with spinner"""
        if not RICH_AVAILABLE:
            for task in tasks:
                print(f"Processing: {task}")
            return
            
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            
            for task_name in tasks:
                task = progress.add_task(f"[cyan]{task_name}", total=100)
                for i in range(100):
                    progress.update(task, advance=1)
                    # Simulate work
                    import time
                    time.sleep(0.01)
    
    def display_analysis_results(self, results: dict):
        """Display analysis results in formatted table"""
        if not RICH_AVAILABLE:
            print("\n=== Analysis Results ===")
            for key, value in results.items():
                print(f"{key}: {value}")
            return
            
        table = Table(title="Document Analysis Results", border_style="green")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        table.add_column("Description", style="white")
        
        # Add rows based on results
        metrics = {
            "total_documents": ("Documents Processed", "Number of documents analyzed"),
            "chars_substituted": ("Unicode Substitutions", "Characters replaced with visually identical Unicode"),
            "invisible_chars_inserted": ("Invisible Characters", "Zero-width characters inserted"),
            "headers_modified": ("Headers Modified", "Academic headers that were processed"),
            "processing_time": ("Processing Time", "Total time taken (seconds)"),
            "risk_score": ("Detection Risk", "Estimated risk of detection (0-1)"),
            "invisibility_score": ("Invisibility Score", "How invisible changes are (0-1)")
        }
        
        for key, (name, description) in metrics.items():
            if key in results:
                value = results[key]
                if isinstance(value, float):
                    if key in ['risk_score', 'invisibility_score']:
                        value = f"{value:.2%}"
                    else:
                        value = f"{value:.2f}"
                table.add_row(name, str(value), description)
        
        self.console.print(table)
    
    def display_risk_analysis(self, analysis):
        """Display risk analysis with color coding"""
        if not RICH_AVAILABLE:
            print(f"\nRisk Level: {analysis.risk_level.value}")
            print(f"Overall Risk: {analysis.overall_risk:.1%}")
            return
            
        # Risk level color mapping
        risk_colors = {
            "minimal": "green",
            "low": "yellow", 
            "medium": "orange",
            "high": "red",
            "critical": "bright_red"
        }
        
        risk_color = risk_colors.get(analysis.risk_level.value, "white")
        
        panel_content = f"""
[bold]Risk Level:[/bold] [{risk_color}]{analysis.risk_level.value.upper()}[/{risk_color}]
[bold]Overall Risk Score:[/bold] {analysis.overall_risk:.1%}
[bold]Invisibility Score:[/bold] {analysis.invisibility_score:.1%}

[bold]Detection Patterns Found:[/bold]
"""
        
        for pattern in analysis.detection_patterns:
            panel_content += f"• {pattern}\n"
        
        panel_content += "\n[bold]Recommendations:[/bold]\n"
        for rec in analysis.recommendations:
            panel_content += f"• {rec}\n"
        
        self.console.print(Panel(panel_content, title="Risk Analysis", border_style=risk_color))
    
    def interactive_file_selection(self) -> Optional[str]:
        """Interactive file selection"""
        input_dir = Path("input")
        if not input_dir.exists():
            self.print_status("Input directory not found", "error")
            return None
            
        files = list(input_dir.glob("*.docx"))
        if not files:
            self.print_status("No DOCX files found in input directory", "warning")
            return None
        
        if not RICH_AVAILABLE:
            print("\nAvailable files:")
            for i, file in enumerate(files, 1):
                print(f"{i}. {file.name}")
            
            while True:
                try:
                    choice = int(input("Select file number: ")) - 1
                    if 0 <= choice < len(files):
                        return str(files[choice])
                except ValueError:
                    print("Invalid input. Please enter a number.")
        else:
            # Rich interactive selection
            self.console.print("\n[bold]Available Documents:[/bold]")
            
            tree = Tree("📁 input/")
            for file in files:
                tree.add(f"📄 {file.name}")
            
            self.console.print(tree)
            
            choices = [f"{i+1}. {file.name}" for i, file in enumerate(files)]
            choice = Prompt.ask(
                "Select a file",
                choices=[str(i+1) for i in range(len(files))],
                default="1"
            )
            
            return str(files[int(choice)-1])
    
    def interactive_technique_selection(self) -> dict:
        """Interactive technique configuration"""
        if not RICH_AVAILABLE:
            print("\nTechnique Configuration:")
            unicode_enabled = input("Enable Unicode substitution? (y/n): ").lower() == 'y'
            invisible_enabled = input("Enable invisible characters? (y/n): ").lower() == 'y'
            return {
                "unicode_substitution": {"enabled": unicode_enabled},
                "zero_width_chars": {"enabled": invisible_enabled}
            }
        
        self.console.print("\n[bold]Steganography Technique Configuration[/bold]")
        
        techniques = {}
        
        # Unicode substitution
        unicode_enabled = Confirm.ask("Enable Unicode character substitution?", default=True)
        if unicode_enabled:
            rate = Prompt.ask("Substitution rate (0.01-0.10)", default="0.03")
            techniques["unicode_substitution"] = {
                "enabled": True,
                "substitution_rate": float(rate)
            }
        else:
            techniques["unicode_substitution"] = {"enabled": False}
        
        # Invisible characters
        invisible_enabled = Confirm.ask("Enable invisible character insertion?", default=True)
        if invisible_enabled:
            rate = Prompt.ask("Insertion rate (0.01-0.10)", default="0.05")
            techniques["zero_width_chars"] = {
                "enabled": True,
                "insertion_rate": float(rate)
            }
        else:
            techniques["zero_width_chars"] = {"enabled": False}
        
        return techniques
    
    def show_configuration_summary(self, config: dict):
        """Show current configuration summary"""
        if not RICH_AVAILABLE:
            print("\n=== Configuration Summary ===")
            print(json.dumps(config, indent=2))
            return
            
        config_json = json.dumps(config, indent=2)
        syntax = Syntax(config_json, "json", theme="monokai", line_numbers=True)
        
        self.console.print(Panel(
            syntax,
            title="Configuration Summary",
            border_style="blue"
        ))

def create_enhanced_parser() -> argparse.ArgumentParser:
    """Create enhanced argument parser"""
    parser = argparse.ArgumentParser(
        description="🔮 Invisible Plagiarism Toolkit - Advanced Steganographic Document Manipulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --file document.docx --aggressive
  %(prog)s --interactive --dry-run
  %(prog)s --batch input/*.docx --output results/
  %(prog)s --analyze-risk original.docx modified.docx
        """
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--file", "-f",
        help="Single document to process"
    )
    input_group.add_argument(
        "--batch", "-b",
        help="Process multiple files (glob pattern)"
    )
    input_group.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Interactive mode with file selection"
    )
    
    # Processing options
    parser.add_argument(
        "--output", "-o",
        help="Output directory (default: output/processed_documents/)"
    )
    parser.add_argument(
        "--config", "-c",
        default="config.json",
        help="Configuration file path"
    )
    
    # Technique options
    technique_group = parser.add_mutually_exclusive_group()
    technique_group.add_argument(
        "--stealth",
        action="store_true",
        help="Use stealth mode (minimal changes)"
    )
    technique_group.add_argument(
        "--balanced",
        action="store_true", 
        help="Use balanced mode (default)"
    )
    technique_group.add_argument(
        "--aggressive",
        action="store_true",
        help="Use aggressive mode (maximum changes)"
    )
    
    # Analysis options
    parser.add_argument(
        "--analyze-risk",
        nargs=2,
        metavar=("ORIGINAL", "MODIFIED"),
        help="Analyze detection risk between two documents"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files"
    )
    
    # Utility options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible results"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup files"
    )
    
    return parser

def main():
    """Enhanced main function with rich CLI"""
    parser = create_enhanced_parser()
    args = parser.parse_args()
    
    cli = EnhancedCLI()
    cli.print_banner()
    
    # Set random seed for reproducibility
    if args.seed:
        import random
        random.seed(args.seed)
        cli.print_status(f"Random seed set to: {args.seed}", "info")
    
    try:
        # Risk analysis mode
        if args.analyze_risk:
            original_path, modified_path = args.analyze_risk
            analyzer = AdvancedAnalyzer(logger=cli.logger)
            
            cli.print_status("Analyzing detection risk...", "processing")
            analysis = analyzer.analyze_document_risk(original_path, modified_path)
            
            cli.display_risk_analysis(analysis)
            return
        
        # Interactive mode
        if args.interactive:
            cli.print_status("Starting interactive mode", "info")
            
            # File selection
            selected_file = cli.interactive_file_selection()
            if not selected_file:
                return
            
            # Technique configuration
            techniques = cli.interactive_technique_selection()
            cli.show_configuration_summary(techniques)
            
            # Confirmation
            if RICH_AVAILABLE:
                proceed = Confirm.ask("Proceed with processing?")
                if not proceed:
                    cli.print_status("Operation cancelled", "warning")
                    return
        
        # Initialize manipulator
        manipulator = InvisibleManipulator(
            config_file=args.config,
            verbose=args.verbose
        )
        
        # Process files
        if args.file:
            files_to_process = [args.file]
        elif args.batch:
            import glob
            files_to_process = glob.glob(args.batch)
        elif args.interactive:
            files_to_process = [selected_file]
        else:
            cli.print_status("No input files specified. Use --help for usage.", "error")
            return
        
        cli.print_status(f"Processing {len(files_to_process)} file(s)", "info")
        
        # Process each file
        for file_path in files_to_process:
            cli.print_status(f"Processing: {Path(file_path).name}", "processing")
            
            if args.dry_run:
                cli.print_status("DRY RUN: Would process but not modify files", "warning")
                continue
            
            result = manipulator.apply_invisible_manipulation(file_path)
            
            if result:
                cli.print_status(f"Completed: {result['output_file']}", "success")
                cli.display_analysis_results(result['stats'])
            else:
                cli.print_status(f"Failed to process: {file_path}", "error")
        
        cli.print_status("All processing completed!", "success")
        
    except KeyboardInterrupt:
        cli.print_status("Operation cancelled by user", "warning")
        sys.exit(1)
    except Exception as e:
        cli.print_status(f"Error: {e}", "error")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
