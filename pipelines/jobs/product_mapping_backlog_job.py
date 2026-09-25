import os
import subprocess
import sys


def run_product_mapping_backlog_job():
    """
    Weekly job: matches the Wansoft product catalog (getstockinventory_inventario)
    against Odoo's (product.product, via x_wansoft_code/default_code) and upserts
    exact_code / exact_code_base / fuzzy_name matches into
    inventory_mapping_dictionary as 'pending_review' (never auto-'approved',
    except a literal wansoft_code == odoo_code match -- see
    docs/purchases-product-mapping-policy.md). Human review still promotes rows
    to 'approved'; a previously-reviewed row's status is never downgraded on
    re-run.

    This directly feeds the Purchases/Inventory product mapping backlog
    (odoo_purchase_inventory_mapping_backlog) -- more approved dictionary rows
    means more purchase lines resolve out of unmapped_inventory_candidate on
    the next purchases_pipeline_job run.
    """
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    subprocess.run(
        [sys.executable, "-m", "scripts.test_save_product_mapping"],
        env=env,
        check=True,
    )
