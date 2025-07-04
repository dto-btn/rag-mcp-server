# Business Request Server
Demo PoC MCP server to be used in other PoC

FIX ME @monarchwadia

## Devs

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
# then run it locally
mcp dev server.py
# or alternatively
python server.py
```

Navigate to the URL it showed to test your server.

And then you can test functions such as Templates, and then `search_business_requests`: 

Pass in this:

```json
{
  "query_filters": [
    {
      "name": "BR_SHORT_TITLE",
      "value": "Server",
      "operator": "="
    }
  ]
}
```

And then you can filter on the results via `filter_results`: 

```json
[
  {
    "column": "RPT_GC_ORG_NAME_EN",
    "operator": "contains",
    "value": "Correctional"
  }
]
```

## Running via Docker

```bash
docker build -t mcp-bits:local .
docker run -p 8080:8080 --env-file ./.env --name mcp-bits-container mcp-bits:local
```

## pymssql issues

### pymssql on Mac OSX

`pymssql` has dependency with **FreeTDS**, as such ensure you install it beforehand `brew install freetds`.

After which if you have issues with running the code please do the following: 

```bash
uv pip uninstall pymssql
uv pip install --pre --no-binary :all: pymssql --no-cache --no-build-isolation
```

Also you can add to `uv` `pyproject.toml`

```toml
[tool.uv]
no-binary-package = ["pymssql"]
```

After this all should be working.

NOTE: Known issue with `cython==3.1.0` [found here](https://github.com/pymssql/pymssql/issues/937)

Here is how to get around it for now (please remove this once this issue is fixed):

```bash
export CFLAGS="-I$(brew --prefix freetds)/include"
export LDFLAGS="-L$(brew --prefix freetds)/lib"
uv pip install "packaging>=24" "setuptools>=54.0" "setuptools_scm[toml]>=8.0" "wheel>=0.36.2" "Cython==3.0.10" "tomli"
uv pip install --pre --no-binary :all: pymssql --no-cache --no-build-isolation
```
## Deployment

### CI/CD

TODO

### Manual

This is how you can deploy manually in Azure via the CLI.

```bash
az webapp deployment source config-local-git \
  --name <WebAppName> \
  --resource-group <ResourceGroupName>
git remote add azure <GitURLFromPreviousStep>
git push azure main
```

## Documentation

* [Using this](https://github.com/modelcontextprotocol/python-sdk) as tutorial on how to build the demo.
* [FastMCP documentation](https://gofastmcp.com/servers/context)
* [MCP OAuth 2.0 Authentication](https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization)

