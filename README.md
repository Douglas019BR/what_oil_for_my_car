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

1. `scripts/dump_pdf_text.py` converte cada PDF em texto (`data/raw/`, ignorado pelo git).
2. Cada tabela é revisada e curada em um fragmento `data/raw/seed_*.json` (um por PDF).
3. `scripts/merge_seeds.py` normaliza, valida, aplica `data/corrections.json` (correções revisadas
   de linhas desalinhadas), remove duplicatas e gera `data/seed.json` (versionado, com 5.016
   recomendações de 5 fabricantes de óleo).
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
