import subprocess
import sys
import logging
import time

def run_script(script_name):

    try:
        subprocess.run(['python', script_name], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Script '{script_name}' exited with an error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        logging.error(f"Script '{script_name}' not found. Please ensure it exists in the current directory.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred while running '{script_name}': {e}")
        sys.exit(1)

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,  # Change to DEBUG for more detailed logs
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

    num_objects = 2  # Number of objects to pick

    for i in range(1, num_objects + 1):
        logging.info(f"\n=== Starting Process for Object {i} ===")

        # Step 1: Run selection.py to select the object
        logging.info(f"Running 'selection.py' to select object {i}...")
        run_script('selection.py')

        time.sleep(1)

        # Step 2: Run pipeline.py to pick up the selected object
        logging.info(f"Running 'pipeline.py' to pick up object {i}...")
        run_script('pipeline.py')

        logging.info(f"=== Completed Process for Object {i} ===\n")

    logging.info("All objects have been picked successfully.")

if __name__ == "__main__":
    main()
