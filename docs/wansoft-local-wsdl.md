# Wansoft Local WSDL

## Purpose

This document describes the technical setup for using a local Wansoft WSDL file in the ETL project.

The goal is to centralise Wansoft SOAP client initialisation and avoid relying on dynamic WSDL download during every execution.

This document applies to:

```text
Wansoft SOAP integrations
Wansoft inventory endpoints
Wansoft product endpoints
Wansoft purchase-like inventory inputs
future Wansoft ETL modules
```

---

## Design Principle

The project should not instantiate Wansoft SOAP clients directly inside ETL scripts.

Instead, all Wansoft SOAP access should go through:

```text
core/clients/wansoft_client.py
```

Expected import pattern:

```python
from core.clients.wansoft_client import get_wansoft_client

client = get_wansoft_client()
```

This centralises WSDL handling, environment configuration, service URL configuration, and client creation.

---

## Why Use a Local WSDL

Using a local Wansoft WSDL file provides several benefits:

```text
more stable ETL execution
less dependency on remote WSDL availability
faster client initialisation
consistent service definition across test runs
controlled versioning in Git
simpler debugging when Wansoft service metadata changes
```

The SOAP service endpoint can still point to the live Wansoft API service, while the WSDL definition is read locally.

---

## WSDL Location

The local WSDL file should be stored at:

```text
resources/wsdl/wansoft.wsdl
```

Expected repository location:

```text
resources/
└── wsdl/
    └── wansoft.wsdl
```

The WSDL file should be versioned in Git unless a security policy requires otherwise.

---

## Environment Variables

The Wansoft SOAP configuration is controlled through `.env`.

Recommended variables:

```env
# =========================
# WANSOFT SOAP / WSDL
# =========================

WANSOFT_USE_LOCAL_WSDL=true
WANSOFT_WSDL_PATH=resources/wsdl/wansoft.wsdl
WANSOFT_SERVICE_URL=https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx
```

---

## Variable Meaning

### WANSOFT_USE_LOCAL_WSDL

Controls whether the ETL should use the local WSDL file or a remote WSDL URL.

Expected values:

```text
true
false
```

Recommended value:

```text
true
```

---

### WANSOFT_WSDL_PATH

Defines the local path to the WSDL file.

Recommended value:

```text
resources/wsdl/wansoft.wsdl
```

This path should be resolved from the project root.

---

### WANSOFT_SERVICE_URL

Defines the Wansoft SOAP service endpoint.

Recommended value:

```text
https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx
```

This is the service endpoint used by the SOAP client after loading the WSDL definition.

---

## Centralised Client

The centralised Wansoft client should live in:

```text
core/clients/wansoft_client.py
```

Expected responsibility:

```text
load environment variables
resolve WSDL path
support local WSDL mode
support remote WSDL mode if needed
configure service endpoint
return a reusable Zeep client or service proxy
```

---

## Expected Client Usage

ETL scripts should use this pattern:

```python
from core.clients.wansoft_client import get_wansoft_client

client = get_wansoft_client()
```

Then call the required Wansoft operation through the returned client object.

---

## Avoid This Pattern

Avoid instantiating Zeep directly in ETL scripts:

```python
from zeep import Client

client = Client("https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx?wsdl")
```

Reason:

```text
duplicates client setup
depends on remote WSDL download
makes ETL scripts harder to maintain
prevents centralised service configuration
makes debugging inconsistent
```

---

## Validation Script

The WSDL client should be validated through:

```text
scripts/test_wansoft_wsdl_client.py
```

Run:

```bash
python -m scripts.test_wansoft_wsdl_client
```

Expected output should include information similar to:

```text
WSDL resolved path: file:///...
SERVICES
PORTS / OPERATIONS
DONE
```

The exact list of operations depends on the WSDL content.

---

## Expected Test Goals

The WSDL validation script should confirm:

```text
.env loads correctly
local WSDL path resolves correctly
WSDL file exists
Zeep can parse the WSDL
service and ports are discoverable
operations are visible
client initialisation succeeds
```

The test does not need to execute every API operation.

---

## Wansoft Endpoint Context

Wansoft exposes SOAP operations used by the project across product, inventory, purchase-like, and operational domains.

Previously documented endpoint examples include:

```text
GetProducts_Xml
GetProduct_Xml
GetDepartments_Xml
GetUnitOfMeasures_Xml
GetWarehouses_Xml
GetInventory_Xml
GetStockInventory_Xml
GetInventoryByWarehouse_Xml
GetInputInventory_Xml
GetOutgoingInventory_Xml
```

These endpoints were described in the Wansoft API analysis material, including `GetInputInventory_Xml` as an Inventory/Purchases endpoint that returns product, quantity, cost, invoice, provider, and input-date fields. 【1-3f2baa】

---

## Important Endpoint for Purchases

The Purchases canonical layer uses Wansoft purchase-like data from:

```text
getinputinventory_entrada
```

This table corresponds conceptually to Wansoft input inventory data.

The source filter used by the canonical purchases load is:

```sql
WHERE TipoEntrada = 'Factura'
```

Relevant Wansoft fields include:

```text
IdEntrada
ClaveAlmacen
Almacen
Departamento
CodigoProducto
NombreProducto
UnidadDeMedida
TipoEntrada
Cantidad
CostoUnitario
FechaEntrada
Factura
RFCProveedor
NombreProveedor
```

These fields were also described as part of `GetInputInventory_Xml` in the Wansoft API analysis material. 【1-3f2baa】

---

## Relationship With Purchases Domain

The Wansoft local WSDL setup supports the broader Purchases domain by standardising access to Wansoft SOAP operations.

However, the current canonical Wansoft purchases load reads from MySQL table:

```text
getinputinventory_entrada
```

rather than calling SOAP directly during canonical load.

This allows the canonical purchase layer to operate from a persisted Wansoft extraction table while preserving the ability to refresh Wansoft data through controlled SOAP extraction processes.

Related documentation:

```text
docs/purchases-canonical-layer.md
docs/purchases-runbook.md
docs/purchases-company-migration-policy.md
docs/purchases-product-mapping-policy.md
```

---

## Relationship With Inventory Domain

Wansoft product and inventory endpoints support Inventory governance by providing native Wansoft product identifiers and operational inventory references.

Relevant endpoints may include:

```text
GetProducts_Xml
GetProduct_Xml
GetInventory_Xml
GetStockInventory_Xml
GetInventoryByWarehouse_Xml
GetInputInventory_Xml
GetOutgoingInventory_Xml
```

Inventory mapping governance remains stored in MySQL:

```text
inventory_mapping_dictionary
inventory_product_lifecycle
odoo_inventory_snapshot
odoo_inventory_backlog
```

The SOAP client should only support data access. It should not directly update governance tables without explicit ETL logic.

---

## Relationship With Sales Domain

Sales remain Wansoft.

The Wansoft SOAP/local WSDL setup may support future or existing sales-related extraction flows, but the main source governance rule remains:

```text
Sales -> always Wansoft
```

Sales does not switch to Odoo through `COMPANY_SOURCE`.

---

## Security and Configuration Notes

The WSDL file itself usually describes service methods and schemas.

Sensitive information should not be hardcoded in:

```text
resources/wsdl/wansoft.wsdl
core/clients/wansoft_client.py
ETL scripts
```

Credentials should remain in:

```text
.env
```

Examples of sensitive values:

```text
Wansoft passwords
API credentials
database credentials
Odoo credentials
```

---

## Wansoft Credentials

Wansoft subsidiary credentials are configured in `.env` and referenced by:

```text
core/config/companies.py
```

The project uses:

```text
CUENTAS_SUCURSALES
```

to keep Wansoft subsidiary ids, company names, and environment-provided credentials together.

Example shape:

```python
CUENTAS_SUCURSALES = [
    ("4960", "Antenas", os.getenv("WANSOFT_PWD_4960")),
    ("6175", "Cancun", os.getenv("WANSOFT_PWD_6175")),
]
```

The Wansoft subsidiary mapping used by canonical purchases is derived from this same structure:

```python
WANSOFT_SUBSIDIARY_SOURCE_KEY = {
    str(subsidiary_id): company_name
    for subsidiary_id, company_name, _password in CUENTAS_SUCURSALES
}
```

This avoids maintaining duplicate manual mapping dictionaries.

---

## Local WSDL Resolution

The client should resolve the local WSDL path relative to the project root.

Expected behaviour:

```text
read WANSOFT_WSDL_PATH
resolve absolute path
convert to file URI if needed
pass local WSDL path to Zeep
override service address with WANSOFT_SERVICE_URL if required
```

Example resolved path shape:

```text
file:///.../resources/wsdl/wansoft.wsdl
```

---

## Remote WSDL Fallback

Remote WSDL fallback can exist for development or troubleshooting.

Example remote WSDL shape:

```text
https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx?wsdl
```

However, the recommended production-style configuration is:

```text
WANSOFT_USE_LOCAL_WSDL=true
```

Remote WSDL usage should be considered a fallback, not the default.

---

## Common Issues

### 1. Local WSDL file not found

Symptoms:

```text
file not found
WSDL path error
Zeep cannot open resource
```

Check:

```text
resources/wsdl/wansoft.wsdl exists
WANSOFT_WSDL_PATH is correct
script is executed from project root
path resolution in wansoft_client.py
```

---

### 2. Zeep cannot parse WSDL

Symptoms:

```text
XML parse error
invalid WSDL
missing service definition
missing binding
```

Check:

```text
WSDL file was downloaded completely
WSDL file is not an HTML error page
WSDL file has not been truncated
WSDL file is valid XML
```

---

### 3. Operations are missing

Symptoms:

```text
test prints services but expected operation is missing
operation call fails because method does not exist
```

Check:

```text
local WSDL is the correct version
WSDL was refreshed after API changes
operation name matches WSDL exactly
```

---

### 4. Service endpoint points to the wrong address

Symptoms:

```text
client parses WSDL but request fails
SOAP call goes to unexpected endpoint
connection error
```

Check:

```text
WANSOFT_SERVICE_URL
service binding address override
network access
Wansoft service availability
```

---

### 5. Authentication or password failure

Symptoms:

```text
operation returns authentication error
operation returns empty data unexpectedly
```

Check:

```text
subsidiary id
subsidiary password
.env variable name
CUENTAS_SUCURSALES entry
Wansoft credentials
```

---

### 6. Endpoint returns empty data

Possible causes:

```text
wrong subsidiary id
wrong operation date
wrong password
endpoint-specific date limitation
no operational data for that date
source table not refreshed
```

For Purchases, remember that the canonical Wansoft purchase load currently reads persisted data from:

```text
getinputinventory_entrada
```

not directly from SOAP at canonical-load time.

---

## Known Design Decisions

### 1. Wansoft client is centralised

All SOAP logic should go through:

```text
core/clients/wansoft_client.py
```

### 2. Local WSDL is preferred

The project prefers:

```text
resources/wsdl/wansoft.wsdl
```

over remote WSDL download.

### 3. Credentials remain in `.env`

No passwords should be hardcoded in source code or documentation.

### 4. WSDL setup is infrastructure, not governance

The WSDL client enables extraction, but it does not decide mappings, company source, or canonical inclusion.

Those decisions are governed by:

```text
core/config/companies.py
inventory_mapping_dictionary
odoo_company_migration_policy
canonical ETL logic
```

### 5. SOAP extraction and canonical loading are separated

Extracted Wansoft data can be persisted first, then canonical layers can be refreshed from MySQL source tables.

This keeps canonical refreshes more stable and auditable.

---

## Validation Checklist

Use this checklist when validating Wansoft SOAP setup.

```text
[ ] .env is loaded
[ ] WANSOFT_USE_LOCAL_WSDL=true
[ ] WANSOFT_WSDL_PATH points to resources/wsdl/wansoft.wsdl
[ ] WANSOFT_SERVICE_URL is configured
[ ] resources/wsdl/wansoft.wsdl exists
[ ] python -m scripts.test_wansoft_wsdl_client runs successfully
[ ] services are listed
[ ] ports are listed
[ ] operations are listed
[ ] credentials are available through CUENTAS_SUCURSALES
[ ] no ETL scripts instantiate Zeep directly with remote WSDL
```

---

## Related Files

```text
core/clients/wansoft_client.py
core/config/companies.py
core/config/env_loader.py
resources/wsdl/wansoft.wsdl
scripts/test_wansoft_wsdl_client.py
docs/wansoft-local-wsdl.md
```

---

## Related Documentation

```text
docs/project-technical-guide.md
docs/inventory-domain-closeout.md
docs/inventory-runbook.md
docs/purchases-company-migration-policy.md
docs/purchases-product-mapping-policy.md
docs/purchases-canonical-layer.md
docs/purchases-runbook.md
```

---

## Recommended Commit

This document should be committed together with the rest of the documentation refresh.

Recommended final commit after all documentation updates:

```bash
git add README.md docs/

git commit -m "docs(project): add technical guide and domain documentation"

git push
```