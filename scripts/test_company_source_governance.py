from core.config.companies import (
    get_domain_company_source,
    is_company_odoo_source,
    is_company_wansoft_source,
)


TEST_COMPANIES = [
    "FONDA ARGENTINA LAS ANTENAS",
    "FONDA ARGENTINA ENCUENTRO OCEANIA",
    "FONDA ARGENTINA SAN JERONIMO",
    "FONDA ARGENTINA PUEBLA",
    "FONDA ARGENTINA COYOACAN",
    "FONDA ARGENTINA MAQ",
    "Acoxpa",
    "Antenas",
    "Oceanía",
    "Puebla",
]


TEST_DOMAINS = [
    "sales",
    "purchases",
    "inventory",
]


if __name__ == "__main__":
    print("==== TEST COMPANY SOURCE GOVERNANCE ====\n")

    for company_name in TEST_COMPANIES:
        print(f"\nCompany: {company_name}")

        for domain in TEST_DOMAINS:
            source = get_domain_company_source(company_name, domain)

            print(
                f"  domain={domain:<10} "
                f"source={source:<8} "
                f"is_odoo={is_company_odoo_source(company_name, domain)} "
                f"is_wansoft={is_company_wansoft_source(company_name, domain)}"
            )

    print("\n==== DONE ✅ ====")