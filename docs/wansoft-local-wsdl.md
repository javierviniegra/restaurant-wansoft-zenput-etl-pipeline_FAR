# Wansoft Local WSDL Configurat*on

## Purpose

The Wansoft SOAP i*tegration now uses a local WSDL fi*e instead of downloading the WSDL *ynamically from Wansoft on every e*ecution.

This change was required*because the dynamic documentation/*SDL access route may be restricted*for security and hardening reasons*

The local WSDL allows the SOAP c*ient to initialize without dependi*g on dynamic WSDL download availab*lity.

---

## Recommended WSDL Lo*ation

The local WSDL file should *e stored at:

```text
resources/ws*l/wansoft.wsdl
```

Expected repos*tory structure:

```text
.
├── cor*/
│   └── clients/
│       └── wan*oft_client.py
├── resources/
│   └*─ wsdl/
│       └── wansoft.wsdl
├*─ scripts/
│   └── test_wansoft_ws*l_client.py
└── docs/
    └── wans*ft-local-wsdl.md
```

---

## Envi*onment Variables

The following va*iables control the Wansoft SOAP cl*ent:

```env
WANSOFT_USE_LOCAL_WSD*=true
WANSOFT_WSDL_PATH=resources/*sdl/wansoft.wsdl
WANSOFT_SERVICE_U*L=https://www.wansoft.net/wansoft.*eb/API/IntegrationService.asmx
```*
### `WANSOFT_USE_LOCAL_WSDL`

Whe* set to:

```text
true
```

the SO*P client loads the local WSDL file*

When set to:

```text
false
```
*the SOAP client can fall back to t*e remote WSDL URL.

The recommende* production value is:

```text
tru*
```

---

## Centralized Client

*ll Wansoft SOAP clients should use*

```python
from core.clients.wans*ft_client import get_wansoft_clien*

client = get_wansoft_client()
``*

Do not instantiate Zeep directly*with the remote WSDL URL inside ET* scripts.

Avoid this pattern:

``*python
from zeep import Client

cl*ent = Client("https://www.wansoft.*et/wansoft.web/API/IntegrationServ*ce.asmx?wsdl")
```

Use this patte*n instead:

```python
from core.cl*ents.wansoft_client import get_wan*oft_client

client = get_wansoft_c*ient()
```

---

## Why This Matte*s

The ETL should not depend on dy*amic WSDL download during every ex*cution.

Using a local WSDL:

- av*ids failures caused by blocked WSD* documentation routes
- makes star*up more stable
- centralizes SOAP *lient configuration
- reduces dupl*cated hardcoded URLs
- allows all *ansoft integrations to change conn*ction behaviour from one place

--*

## Test

Run:

```bash
python -m scripts.test_wansoft_wsdl_client
```

Expected result:

```text
WSDL resolved path: file:///...
SERVICES
PORTS / OPERATIONS
DONE
```

The test validates that:

- the local WSDL file exists
- the SOAP client can initialize
- services and operations can be discovered from the WSDL

---

## Files Changed

```text
core/clients/wansoft_client.py
scripts/test_wansoft_wsdl_client.py
resources/wsdl/wansoft.wsdl
docs/wansoft-local-wsdl.md
.env.example
```

---

## Migration Checklist

1. Add the WSDL file at:

```text
resources/wsdl/wansoft.wsdl
```

2. Add environment variables to `.env` and `.env.example`.

3. Replace direct Zeep calls:

```python
Client("https://www.wansoft.net/wansoft.web/API/IntegrationService.asmx?wsdl")
```

with:

```python
get_wansoft_client()
```

4. Run the WSDL test:

```bash
python -m scripts.test_wansoft_wsdl_client
```

5. Run existing Wansoft-related ETL tests.

6. Commit the change.

---

## Git Notes

If the repository is private, the WSDL can be versioned in:

```text
resources/wsdl/wansoft.wsdl
```

If the repository is public or shared externally, do not commit the WSDL file. In that case, store the WSDL outside the repo and configure:

```env
WANSOFT_WSDL_PATH=/absolute/path/to/wansoft.wsdl
```

---

## Commit Message

Recommended commit:

```bash
git add .
git commit -m "fix(wansoft): use local WSDL for SOAP client initialization"
git push
```