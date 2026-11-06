# Optional Local SearXNG Provider

> **中文摘要**：SearXNG 是可选的本地搜索前端，通过 JSON 接口为网络证据通道提供结果。项目默认仍可使用 DuckDuckGo；配置 `SEARXNG_URL` 后，服务先查 SearXNG，结果为空或报错时自动回退 DuckDuckGo。SearXNG 只返回候选 URL，最终仍经过 allowlist、HTTPS 抓取、TTL 缓存和人工晋升草稿，不自动入库。

## 1. What it is for

The web-evidence plane (`src/scs_fkb/web_v2/`) can use two providers:

- `SearXNGProvider`: a local SearXNG instance with `formats: [json]`.
- `DuckDuckGoProvider`: the default fallback, using `ddgs`.

When `SEARXNG_URL` is set, `build_provider` returns a `FallbackProvider`:
it returns SearXNG results if non-empty, otherwise tries DuckDuckGo. If both
fail, the caller gets a `ProviderError` and the smoke report records it. The
provider still cannot bypass the allowlist or fetch a non-allowlisted host.

## 2. Local setup (macOS/Linux, no Docker)

SearXNG is kept outside this repository, in a separate checkout and virtual
environment:

```bash
git clone --depth 1 https://github.com/searxng/searxng.git ~/src/searxng
cd ~/src/searxng
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Use a small settings file. It keeps only the two Chinese engines that work in
this environment and enables JSON:

```yaml
use_default_settings:
  engines:
    keep_only:
      - 360search
      - sogou
general:
  instance_name: "SCS-FKB local SearXNG"
search:
  safe_search: 0
  default_lang: "zh-CN"
  formats:
    - html
    - json
server:
  port: 8888
  bind_address: "127.0.0.1"
  limiter: false
  public_instance: false
  secret_key: "replace-with-a-long-random-value"
  image_proxy: false
  method: "GET"
```

Start it:

```bash
export SEARXNG_SETTINGS_PATH="$HOME/src/searxng/settings.yml"
export SEARXNG_SECRET="replace-with-the-same-long-random-value"
cd "$HOME/src/searxng"
.venv/bin/python -m searx.webapp
```

Check JSON from another terminal:

```bash
curl --get 'http://127.0.0.1:8888/search' \
  --data-urlencode 'q=南海伏季休渔' \
  --data-urlencode 'format=json'
```

The `results` array must be present. If a long query returns no results, the
combined provider will try DuckDuckGo; this is expected and is recorded in the
smoke report.

## 3. Use from this repository

```bash
SEARXNG_URL=http://127.0.0.1:8888 \
SCS_FKB_DATA_ROOT=... \
SCS_FKB_RUN_ROOT=... \
PYTHONPATH=src python scripts/eval_web_v2.py \
  --report-dir P10-WEB-147 --delay 2
```

The provider label in the report should be `searxng+ddgs`. The local SearXNG
does not run in CI; CI keeps `SEARXNG_URL` unset and uses the default provider
or mocks.

## 4. Boundaries

- SearXNG is optional and local; it is not a public instance and not a
  production dependency.
- Results are candidates, not evidence. The allowlist, HTTPS-only fetch,
  content hash, TTL and promotion-draft rules still apply.
- SearXNG engines can rate-limit or CAPTCHA. The fallback prevents a single
  engine from turning into a total outage; failures remain visible.
- Do not commit the SearXNG settings file or its secret to this repository.
