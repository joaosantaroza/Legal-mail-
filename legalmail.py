#!/usr/bin/env python3
"""Cliente mínimo da API LegalMail.

A chave vem da variável de ambiente LEGALMAIL_API_KEY (segredo do ambiente).
Nunca é impressa: toda saída passa por _mask().
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE_URL = "https://app.legalmail.com.br"
ENV_VAR = "LEGALMAIL_API_KEY"
SEND_ENDPOINTS = ("/intermediate/send", "/complaint/send")


def _key():
    key = os.environ.get(ENV_VAR, "").strip()
    if not key:
        sys.exit(f"{ENV_VAR} não está definida. Cadastre-a como segredo do "
                 "ambiente e abra uma sessão nova.")
    return key


def _mask(text, key):
    return text.replace(key, "***") if key else text


def _multipart(fields, files):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; '
                     f'name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, path in files.items():
        with open(path, "rb") as fh:
            data = fh.read()
        filename = os.path.basename(path)
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; '
                     f'name="{name}"; filename="{filename}"\r\n'
                     f'Content-Type: application/pdf\r\n\r\n'.encode()
                     + data + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def call(method, path, params=None, body=None, file=None, form=None):
    key = _key()
    query = dict(params or {})
    query["api_key"] = key
    url = f"{BASE_URL}{path}?{urllib.parse.urlencode(query)}"
    headers = {"Accept": "application/json"}
    data = None
    if file:
        data, ctype = _multipart(form or {}, {"file": file})
        headers["Content-Type"] = ctype
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, _mask(raw, key)
    except urllib.error.HTTPError as err:
        raw = _mask(err.read().decode("utf-8", "replace"), key)
        if err.code == 429:
            retry = err.headers.get("Retry-After", "não informado")
            sys.exit(f"HTTP 429 — limite atingido. Retry-After: {retry}. "
                     "PARAR: não repetir a chamada.\n" + raw)
        sys.exit(f"HTTP {err.code} em {method} {path}\n{raw}")
    except urllib.error.URLError as err:
        sys.exit(_mask(f"Falha de rede em {method} {path}: {err.reason}", key))


def _pairs(items):
    out = {}
    for item in items:
        if "=" not in item:
            sys.exit(f"Parâmetro inválido (use nome=valor): {item}")
        name, value = item.split("=", 1)
        out[name] = value
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("method", help="GET, POST, PUT, DELETE ou 'check'")
    ap.add_argument("path", nargs="?", help="ex.: /api/v1/lawsuit/summary")
    ap.add_argument("params", nargs="*", help="query params nome=valor")
    ap.add_argument("--json", help="corpo JSON")
    ap.add_argument("--file", help="PDF para upload multipart (campo 'file')")
    ap.add_argument("--form", action="append", default=[],
                    help="campo extra do multipart nome=valor")
    ap.add_argument("--confirmo-protocolo", action="store_true",
                    help="obrigatório nos endpoints de envio ao tribunal")
    args = ap.parse_args()

    if args.method.lower() == "check":
        _key()
        print(f"{ENV_VAR} está definida.")
        return

    if not args.path:
        ap.error("informe o caminho do endpoint")
    if "api_key" in args.path or any(p.startswith("api_key=") for p in args.params):
        ap.error("não passe api_key: o cliente lê a chave do ambiente")
    if args.path.endswith(SEND_ENDPOINTS) and not args.confirmo_protocolo:
        sys.exit("Endpoint de protocolo: exige o OK expresso do João e "
                 "--confirmo-protocolo.")

    body = json.loads(args.json) if args.json else None
    status, text = call(args.method.upper(), args.path, _pairs(args.params),
                        body, args.file, _pairs(args.form))
    try:
        print(json.dumps(json.loads(text), ensure_ascii=False, indent=2))
    except ValueError:
        print(text)
    if status >= 400:
        sys.exit(1)


if __name__ == "__main__":
    main()
