# what_oil_for_my_car

Aplicação simples que responde à pergunta "qual óleo usar no meu carro?" a partir de tabelas de
especificação de fabricantes de lubrificantes. Os PDFs em `images/` são convertidos em registros
estruturados, carregados no Postgres e consultados por uma página web em português.

## Requisitos

- Python 3.12+
- Docker com `docker-compose` (para o Postgres)
- `pdftotext` (poppler-utils) para gerar os textos das tabelas

## Instalação

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
docker-compose up -d db
```

O Postgres fica disponível em `localhost:5433` (banco/usuário/senha `whatoil`). O banco de testes
`what_oil_test` é criado automaticamente pelo comando abaixo.

## Como os dados são gerados

1. `scripts/dump_pdf_text.py` converte cada PDF em texto nos modos `-layout` e `-raw`
   (`data/raw/*.txt`, ignorado pelo git). O modo `-raw` preserva a ordem dos blocos de colunas e
   foi usado na curadoria das tabelas mais recentes.
2. Cada tabela é revisada e curada em um fragmento `data/raw/seed_*.json` (um por PDF). Esses
   fragmentos são versionados e preservam a curadoria original; o `data/seed.json` é gerado deles.
3. `scripts/merge_seeds.py` normaliza, valida, aplica `data/corrections.json` (correções revisadas
   de linhas desalinhadas), remove duplicatas e gera `data/seed.json` (versionado, com 6.567
   recomendações de 7 fabricantes de óleo).

Fontes ativas (a mais recente substitui a anterior do mesmo fabricante):

| Fabricante de óleo | PDF de origem | Data |
| :--- | :--- | :--- |
| Supra | `Tabela-Lubrificacao-PDV.pdf` | 2015 |
| Petronas | `Tabela - Petronas.pdf` | 2014 |
| Valvoline | `Valvoline-Tabela-de-Veiculos-Leves-2023.pdf` | 2023 |
| Ipiranga | `Tabela-Ipiranga-F1-Master-2025.pdf` | 2025 |
| Total / Elf | `Tabela-TotalEnergies-Leves-2026.pdf` | 2026 |
| YPF | `Tabela-YPF-Leves-2026-06.pdf` | 2026 |

Os fragmentos das tabelas antigas de Ipiranga (`seed_ipiranga.json`) e Total
(`seed_total.json`) permanecem versionados como histórico, mas não entram mais no seed.
4. `scripts/build_db.py` aplica `sql/schema.sql` e carrega o seed no Postgres:

```bash
.venv/bin/python scripts/dump_pdf_text.py
.venv/bin/python scripts/merge_seeds.py
.venv/bin/python scripts/build_db.py --create-database
.venv/bin/python scripts/build_db.py --test --create-database
```

O banco é derivado do seed, então pode ser reconstruído a qualquer momento.

## Execução

```bash
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Acesse `http://localhost:8000`. Selecione **Marca → Modelo → Motor/ano** para ver os óleos
recomendados por cada fabricante, com viscosidade, tipo, capacidade, observações e PDF de origem.
Documentação da API: `http://localhost:8000/docs`.

Endpoints: `GET /api/makes`, `/api/models`, `/api/variants`, `/api/recommendations`, `/api/health`.

## Serviço no servidor (Docker Compose)

O mesmo arquivo `docker-compose.yml` sobe o banco e a aplicação. No primeiro boot, o entrypoint
aguarda o Postgres e carrega `data/seed.json` automaticamente; em boots seguintes ele preserva os
dados existentes.

```bash
cp .env.example .env
docker compose up -d --build
```

Acesse `http://<ip-do-servidor>:8000`. Para alterar a porta ou a senha do banco, defina `APP_PORT`
e `POSTGRES_PASSWORD` no `.env` **antes** do primeiro boot. O banco fica no volume
`what_oil_pgdata`, ambos os serviços têm `restart: unless-stopped` e healthchecks.

Comandos úteis:

```bash
docker compose ps
docker compose logs -f app
curl http://localhost:8000/api/health
docker compose down
```

Se usar a versão antiga do Docker Compose, substitua `docker compose` por `docker-compose`.

## Testes e qualidade

```bash
.venv/bin/python -m unittest discover -s test -v
bash verify.sh
```

`verify.sh` executa lint e formatação (ruff), checagem de ortografia (codespell), varredura de
segredos (detect-secrets) e os testes unitários. Os testes usam `what_oil_test` e recriam o schema
a cada execução, portanto são repetíveis.

## Limitações

As tabelas originais são diagramas de múltiplas colunas com códigos de produtos. A curadoria
priorizou exatidão: linhas ambíguas e recomendações do tipo "verificar manual" foram descartadas,
e os desalinhamentos identificados na revisão foram corrigidos em `data/corrections.json`.
Intervalos de capacidade e outras ressalvas aparecem na coluna "Observação". Ainda podem restar
imprecisões nessas tabelas complexas; as informações são orientativas e o manual do veículo
prevalece. A extração opcional via AWS Textract usa `scripts/requirements.txt`.
