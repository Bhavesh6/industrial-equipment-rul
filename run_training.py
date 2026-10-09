"""
Top-level training runner — required on Windows for multiprocessing safety.
Run this from the project root:
    python run_training.py
"""
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    # Step 1: Generate dataset
    print("=" * 60)
    print("  STEP 1: Generating RS-380 Run-to-Failure Dataset")
    print("=" * 60)
    from src.data.generate_training_data import main as gen_main
    df = gen_main()
    print()

    # Step 2: Train models
    print("=" * 60)
    print("  STEP 2: Training ML Models")
    print("=" * 60)
    from src.models.train import main as train_main
    train_main()

    print()
    print("=" * 60)
    print("  ALL DONE — models saved to models/")
    print("=" * 60)
