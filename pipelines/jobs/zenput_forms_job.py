from extract.zenput.zenput_forms import extract_zenput_forms


def run_zenput_forms_job():
    print("=== Starting job: ZENPUT FORMS ===")
    extract_zenput_forms()
    print("=== Finished job: ZENPUT FORMS ✅ ===")