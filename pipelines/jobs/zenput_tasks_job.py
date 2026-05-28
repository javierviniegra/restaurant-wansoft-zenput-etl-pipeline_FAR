from extract.zenput.zenput_tasks import extract_zenput_tasks


def run_zenput_tasks_job():
    print("=== Starting job: ZENPUT TASKS ===")
    extract_zenput_tasks()
    print("=== Finished job: ZENPUT TASKS ✅ ===")
