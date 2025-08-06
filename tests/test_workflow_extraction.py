#!/usr/bin/env python3
"""
Test workflow extraction with a single tutorial
"""
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from workflow_extractor import WorkflowExtractor


def main():
    """Test workflow extraction"""
    tutorials_path = "/home/danilopezmella/flopy_expert/flopy/.docs/Notebooks"
    extractor = WorkflowExtractor(tutorials_path)
    
    # Test with MF6 tutorial
    test_file = Path(tutorials_path) / "mf6_tutorial01.py"
    
    print(f"Testing workflow extraction with: {test_file.name}")
    print("=" * 60)
    
    if test_file.exists():
        workflow = extractor.extract_workflow(test_file)
        if workflow:
            print(f"\n📋 Extracted Workflow")
            print(f"Title: {workflow.title}")
            print(f"Description: {workflow.description[:200]}...")
            print(f"Model Type: {workflow.model_type}")
            print(f"Packages Used: {', '.join(workflow.packages_used)}")
            print(f"Number of Steps: {len(workflow.workflow_steps)}")
            print(f"Complexity: {workflow.complexity}")
            print(f"Tags: {', '.join(workflow.tags)}")
            print(f"Total Lines: {workflow.total_lines}")
            
            print("\n📊 Workflow Steps:")
            for step in workflow.workflow_steps[:5]:  # First 5 steps
                print(f"\nStep {step.step_number}: {step.description}")
                print(f"  FloPy Classes: {', '.join(step.flopy_classes) if step.flopy_classes else 'None'}")
                print(f"  Parameters: {list(step.parameters.keys())[:5] if step.parameters else 'None'}")
                print(f"  Code Preview: {step.code_snippet[:100]}...")
            
            if len(workflow.workflow_steps) > 5:
                print(f"\n... and {len(workflow.workflow_steps) - 5} more steps")
        else:
            print("❌ Failed to extract workflow")
    else:
        print(f"❌ Test file not found: {test_file}")


if __name__ == "__main__":
    main()