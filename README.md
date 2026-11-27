# what_oil_for_my_car

Aplicação web que responde "qual óleo usar no meu carro?". Ela cruza tabelas de especificação de
fabricantes de lubrificantes com modelos de veículos e devolve, para cada variante, os óleos
recomendados, viscosidade, tipo, capacidade e a PDF de origem. Interface em português, backend
FastAPI e banco Postgres.

Release atual: `v0.2.0`.

## Dados atualmente carregados

| Métrica | Valor |
| :--- | ---: |
| Recomendações | 6.471 |
| Fabricantes de veículos | 45 |
| Combinações marca/modelo | 1.535 |
| Variantes (motor/ano) | 3.422 |
| Produtos de óleo | 103 |
| Fabricantes de óleo | 7 |
| Tabelas de origem | 6 |

Exemplos reais do banco:

- Volkswagen FOX `1.6 L4 MSI 16V (F)` 2015-2021 → Valvoline Premium Protection 5W-40 Sintético, 4 L.
- BYD KING `1.5 L4 MPFI 16V(G)` 2024-2026 → YPF Elaion Auro D1 020 0W-20, 3,3 L (tabela YPF 2026).
- Chevrolet Equinox `1.5 L4 DFI TB 16V` 2021-2022 → F1 Master Sintético 0W20 SP, 4 L (tabela Ipiranga 2025).

## Estrutura do repositório

```
images/                     PDFs de origem (6 tabelas, 2014-2026)
data/raw/                   textos extraídos e fragmentos curados (seed_*.json)
data/seed.json              base única versionada, gerada pelos fragmentos
data/corrections.json       correções revisadas aplicadas na mesclagem
sql/schema.sql              DDL de reconstrução do Postgres
sql/migrations/             migrações idempotentes aplicadas no boot
app/config.py               URL do banco e variáveis de ambiente
app/db.py                   queries e carga/atualização do seed
app/migrations.py           aplicação versionada das migrações
app/log_config.py           logs estruturados (JSON por padrão)
app/rate_limit.py           limite de requisições por IP
app/main.py                 FastAPI: página estática + API JSON
scripts/dump_pdf_text.py    pdftotext nos modos -layout e -raw
scripts/merge_seeds.py      normaliza/valida/mescla os fragmentos
scripts/build_db.py         migra/carrega o seed; --rebuild recria tudo (destrutivo)
scripts/entrypoint.py       espera o DB, aplica migrações, atualiza o seed, inicia o uvicorn
scripts/extract_tables.py   extração opcional via AWS Textract
deploy/Caddyfile            proxy reverso HTTP (padrão)
deploy/Caddyfile.auth       proxy reverso com autenticação básica
deploy/backup.sh            dump periódico do Postgres com retenção
static/                     index.html, style.css, app.js (sem frameworks)
test/                       testes unitários (seed, DB, API, serviço, tema, limites)
docker-compose.yml          serviços db + app + caddy + backup
Dockerfile / .dockerignore  imagem da aplicação (usuário não-root)
verify.sh                   lint, formatação, ortografia, segredos e testes
```

## Modelo de dados

- `oil_brands(id, name)` — fabricantes de óleo (Supra, Petronas, Valvoline, Ipiranga, Total, Elf, YPF).
- `oils(id, brand_id, name, sae_viscosity, oil_type)` — 103 produtos.
- `vehicles(id, make, model, engine, year_from, year_to)` — 3.422 variantes; `NULL` em ano significa
  "sem limite informado na tabela".
- `recommendations(id, vehicle_id, oil_id, capacity_liters, source_pdf, notes)` — 6.471 linhas.

Uma variante é identificada por `(make, model, engine, year_from, year_to)`, incluindo `NULL`s.
A API usa `exact=true` para casar a variante exatamente; sem esse parâmetro ela devolve todas as
recomendações do modelo.

## API

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/makes
curl 'http://localhost:8000/api/models?make=Volkswagen'
curl 'http://localhost:8000/api/variants?make=Volkswagen&model=FOX'
curl 'http://localhost:8000/api/recommendations?make=BYD&model=KING&engine=1.5%20L4%20MPFI%2016V(G)&year_from=2024&year_to=2026&exact=true'
```

`GET /api/recommendations` devolve objetos com `oil_brand`, `oil_name`, `sae_viscosity`,
`oil_type`, `capacity_liters`, `source_pdf` e `notes`. Documentação interativa: `/docs`.

## Executar localmente

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
docker compose up -d db
.venv/bin/python scripts/build_db.py --create-database
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

O Postgres local escuta apenas em `127.0.0.1:5433`. Use `docker-compose` no lugar de
`docker compose` se tiver a versão 1.x.

## Serviço no servidor

```bash
cp .env.example .env
docker compose up -d --build
```

O entrypoint espera o Postgres, aplica as migrações pendentes e atualiza as recomendações das
fontes presentes no seed, sem apagar tabelas nem dados de outras fontes. A aplicação escuta apenas
em `127.0.0.1:8000`; o acesso externo passa pelo Caddy. O banco fica no volume `what_oil_pgdata`.
Todos os serviços têm `restart: unless-stopped`; `db` e `app` têm healthchecks. Defina
`POSTGRES_PASSWORD` no `.env` **antes** do primeiro boot.

### Proxy, HTTPS e autenticação

Por padrão o Caddy publica HTTP na porta `80`, sem autenticação — use essa configuração apenas em
rede confiável. Para expor o serviço, configure HTTPS e autenticação antes. Para HTTPS automático, defina
`SITE_ADDRESS=seu.dominio.com` e libere `80`/`443`; o Caddy obtém e renova o certificado. Para
proteger o acesso, use `CADDYFILE=Caddyfile.auth` e gere o hash da senha:

```bash
docker run --rm --entrypoint caddy caddy:2-alpine hash-password --plaintext 'sua-senha'
```

Cole o hash em `BASIC_AUTH_HASH` e ajuste `BASIC_AUTH_USER` no `.env`. A autenticação fica no
proxy — a aplicação não tem login próprio.

### Backup

O serviço `backup` executa `pg_dump` no primeiro boot e depois a cada `BACKUP_INTERVAL` segundos
(padrão 86400). Os arquivos ficam em `./backups/` com retenção de `BACKUP_RETENTION_DAYS` dias
(padrão 7). Restaure com:

```bash
docker compose exec -T db pg_restore --clean --if-exists -U whatoil -d whatoil \
  /backups/what_oil-YYYYMMDD-HHMMSS.dump
```

### Logs e limites

- `LOG_LEVEL` (padrão `INFO`) e `LOG_JSON` (padrão `true`) controlam os logs da aplicação; cada
  requisição `/api/*` gera um registro com método, caminho, status e duração. Configure rotação
  de logs no Docker (por exemplo `log-driver=json-file` com `max-size=10m`).
- `RATE_LIMIT_PER_MINUTE` (padrão `120`, `0` desativa) limita requisições `/api/*` por IP e
  devolve `429` quando excedido. Atrás do Caddy, a chave vem do primeiro valor de
  `X-Forwarded-For`, não do IP do proxy.

### Comandos úteis

```bash
docker compose ps
docker compose logs -f app
curl http://localhost/api/health
docker compose down
docker compose up -d --build
```

## Atualizando os dados

1. Coloque o PDF em `images/` e rode `scripts/dump_pdf_text.py` para gerar os textos.
2. Curie uma linha por recomendação em `data/raw/seed_<origem>.json` (campos iguais aos de
   `data/seed.json`). Use o texto `-raw.txt` para tabelas de várias colunas.
3. Adicione o fragmento à lista `FRAGMENTS` em `scripts/merge_seeds.py`. Se uma tabela substitui
   uma anterior do mesmo fabricante, remova a antiga da lista (ela fica no repositório como histórico).
4. Registre correções pontuais em `data/corrections.json` e rode `scripts/merge_seeds.py`.
5. Rode `scripts/build_db.py` (atualização não destrutiva) ou `scripts/build_db.py --rebuild`
   (apenas em desenvolvimento: apaga e recria as tabelas), depois `bash verify.sh`.

## Testes e qualidade

```bash
bash verify.sh
```

Executa `compileall`, ruff (lint e formatação), codespell, detect-secrets e 50 testes unitários.
Os testes usam o banco `what_oil_test` e recriam o schema a cada execução. Há testes semânticos
contra os textos de origem (códigos de produto, anos e combinações modelo/motor impossíveis),
além de testes de API, migrações, serviço Docker, tema claro/escuro e limite de requisições.

## Fontes ativas

| Fabricante de óleo | PDF | Ano da tabela | Recomendações |
| :--- | :--- | ---: | ---: |
| Valvoline | `Valvoline-Tabela-de-Veiculos-Leves-2023.pdf` | 2023 | 1.671 |
| Total / Elf | `Tabela-TotalEnergies-Leves-2026.pdf` | 2026 | 1.473 |
| Petronas | `Tabela - Petronas.pdf` | 2014 | 1.328 |
| YPF | `Tabela-YPF-Leves-2026-06.pdf` | 2026 | 1.041 |
| Ipiranga | `Tabela-Ipiranga-F1-Master-2025.pdf` | 2025 | 489 |
| Supra | `Tabela-Lubrificacao-PDV.pdf` | 2015 | 469 |

## Limitações

As tabelas são diagramas complexos de múltiplas colunas. Linhas ambíguas, recomendações
"verificar manual" e produtos sem código identificável foram descartados; desalinhamentos
encontrados em revisão estão em `data/corrections.json`. Podem restar imprecisões: a aplicação é
orientativa e o manual do veículo prevalece. A extração via AWS Textract em
`scripts/extract_tables.py` é opcional e exige credenciais (`scripts/requirements.txt`).
