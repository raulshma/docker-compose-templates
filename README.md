# docker-compose-templates

A collection of self-hosted infrastructure templates: Docker Compose stacks, env
files, and client integration scripts. Each stack is self-contained and copy-paste
ready — clone the repo, pick a folder, run it.

## Layout

```
stacks/
└── <stack-name>/
    ├── README.md            # what it is, setup, usage
    ├── docker-compose.yml
    ├── .env.example         # copy to .env and fill in
    ├── scripts/             # optional stack-specific helpers
    └── mcp/                 # generated client snippets (gitignored — contains tokens)
```

## Stacks

| Stack                                              | What it is                                  | Ports |
|----------------------------------------------------|---------------------------------------------|-------|
| [crawl4ai](stacks/crawl4ai/)                       | Self-hosted crawler: REST API + MCP server  | 11235 |

## Usage

Every stack works the same way: `cd` into its folder, copy `.env.example` to
`.env`, fill in secrets, and bring it up.

```bash
cd stacks/crawl4ai
cp .env.example .env
# generate secrets as documented in the stack README, then:
docker compose up -d
```

## Adding a stack

1. Create `stacks/<name>/` following the layout above.
2. Read every secret from the environment (`${VAR:?required}`) — never hardcode
   tokens or keys in `docker-compose.yml`.
3. Ship a `.env.example` listing all variables (required ones empty, optional ones
   commented out).
4. Add a `README.md` with setup, usage, and endpoints, then add a row to the
   Stacks table above.

## Roadmap

- Website that showcases stacks with one-click copy-paste configs, generated
  from the `stacks/` directory (each folder's `README.md` + `docker-compose.yml`
  is the single source of truth).
