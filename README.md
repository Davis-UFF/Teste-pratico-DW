# Data Warehouse E-Commerce Olist (SQLite + Python ETL)

Projeto completo de modelagem dimensional, implementação de banco de dados analítico, pipeline de ETL (carga inicial e incremental) e consultas SQL analíticas utilizando o dataset público **Brazilian E-Commerce Public Dataset by Olist**.

---

## Estrutura do Repositório

```text
├── data/                        # Coloque aqui os 9 arquivos CSV originais da Olist
├── sql/
│   ├── ddl_dw.sql               # Criação das tabelas staging (stg_*) e DW (dim_*, fato_*) + índices
│   └── consultas_analiticas.sql # 20 consultas SQL respondendo às perguntas de negócio
├── etl/
│   └── run_etl.py               # Pipeline ETL em Python + SQLite (carga inicial e incremental)
├── requirements.txt             # Dependências Python (pandas, numpy)
└── README.md                    # Documentação completa das Partes 1, 2, 3 e 4
```

---

## Como Executar o Projeto

1. **Instalar dependências:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Colocar os CSVs da Olist na pasta `data/`** (os 9 arquivos originais do Kaggle).
3. **Executar a Carga Inicial (pedidos até 31/12/2017):**
   ```bash
   python etl/run_etl.py --carga inicial
   ```
4. **Executar a Carga Incremental (pedidos a partir de 01/01/2018):**
   ```bash
   python etl/run_etl.py --carga incremental
   ```
   *(Nota: Reexecutar o comando incremental não gera registros duplicados.)*

---

## Parte 1 — Modelagem Dimensional

### 1. Escolha da Arquitetura: Esquema Estrela (Star Schema)
Foi adotado o **Esquema Estrela** desnormalizando hierarquias geográficas (Cidade, Estado, Região e Latitude/Longitude médias por CEP) e categorias diretamente nas tabelas de dimensão. Isso elimina `JOIN`s encadeados e torna as consultas analíticas mais simples, legíveis e rápidas no SQLite.

### 2. Tabelas Fato
* **`fato_itens_venda` (Grão: 1 linha por item do pedido):** mede `quantidade_item` (aditiva), `valor_produto` (aditiva), `valor_frete` (aditiva) e `valor_total_item` (aditiva).
* **`fato_pedidos` (Grão: 1 linha por pedido):** mede `qtd_pedidos` (aditiva), `dias_aprovacao` (não aditiva), `dias_transporte` (não aditiva), `dias_entrega_total` (não aditiva), `dias_diferenca_prazo` (não aditiva), `flag_atraso` (semiaditiva/binária) e `nota_avaliacao` (não aditiva).
* **`fato_pagamentos` (Grão: 1 linha por transação de pagamento do pedido):** mede `valor_pagamento` (aditiva), `qtd_parcelas` (não aditiva) e `valor_medio_parcela` (não aditiva).

### 3. Tabelas Dimensão
* **`dim_tempo`:** calendário 2016–2018 com ano, semestre, trimestre, mês, dia da semana, fim de semana e indicador de feriados nacionais/datas especiais.
* **`dim_cliente`:** dados cadastrais, cidade, UF, nome do estado, região do Brasil e coordenadas médias do prefixo de CEP.
* **`dim_produto`:** categoria limpa em português (`categoria_pt`), tradução em inglês (`categoria_en`), dimensões físicas, peso e quantidade de fotos.
* **`dim_vendedor`:** localização completa (cidade, UF, região e coordenadas médias do CEP) dos sellers.
* **`dim_pagamento`:** meio de pagamento traduzido (`Cartão de Crédito`, `Boleto`, `Voucher`, `Cartão de Débito`), quantidade de parcelas e faixa de parcelamento.

---

## Parte 2 — Banco de Dados e Regras de Qualidade (`sql/ddl_dw.sql`)

* **Organização em SQLite (`olist_dw.db`):** camada `staging` (`stg_*`) espelhando os CSVs tipados e camada `dw` (`dim_*` e `fato_*`) com `PRAGMA foreign_keys = ON`, chaves substitutas `AUTOINCREMENT`, restrições `UNIQUE`/`CHECK` e índices nas FKs e colunas de filtro.
* **Principais Regras de Qualidade:**
  * Categorias nulas preenchidas com `'Sem Categoria'` e formatadas com `.title()`.
  * Nomes de cidades e UFs padronizados e enriquecidos com `nome_estado` e `regiao`.
  * Geolocalização agregada por média (`mean`) de latitude e longitude por prefixo de CEP.
  * Pedidos sem entrega mantêm datas e atraso como `NULL`; avaliações ausentes permanecem `NULL` para não distorcer médias.
  * Parcelas iguais a `0` ajustadas para `1` no cálculo de `valor_medio_parcela`.

---

## Parte 3 — Pipeline ETL (`etl/run_etl.py`)

| Tabela no DW | Carga Inicial (`<= 2017-12-31`) | Carga Incremental (`>= 2018-01-01`) | Reexecução Incremental |
| :--- | :---: | :---: | :---: |
| `dim_tempo` | 1.096 | 1.096 | 1.096 |
| `dim_cliente` | 99.441 | 99.441 | 99.441 |
| `dim_produto` | 32.951 | 32.951 | 32.951 |
| `dim_vendedor` | 3.095 | 3.095 | 3.095 |
| `dim_pagamento` | 27 | 27 | 27 |
| **`fato_itens_venda`** | **51.234** | **112.650** | **112.650** |
| **`fato_pedidos`** | **45.430** | **99.441** | **99.441** |
| **`fato_pagamentos`** | **47.871** | **103.886** | **103.886** |

---

## Parte 4 — Principais Resultados Analíticos (`sql/consultas_analiticas.sql`)

* **Receita Total:** R$ 13.591.643,70 em produtos e R$ 2.251.909,54 em frete (112.650 itens vendidos).
* **Categorias Líderes:** *Beleza Saúde* (R$ 1.258.681,34; ticket médio R$ 130,16), *Relógios Presentes* (R$ 1.205.005,68; ticket médio R$ 201,14) e *Cama Mesa Banho* (R$ 1.036.988,68; ticket médio R$ 93,30).
* **Concentração Regional:** Sudeste representa 65,4% do faturamento de produtos (R$ 8.887.393,06) e concentra 9 dos 10 maiores vendedores (todos em SP; o 2º maior está em Lauro de Freitas/BA).
* **Logística e Satisfação:** Tempo médio real de entrega de **12,56 dias**. Pedidos entregues no prazo têm nota média **4,29**, enquanto pedidos atrasados caem para **2,57** (taxa de atraso chega a 14,33% no Nordeste contra 7,05% no Sul).
* **Meios de Pagamento:** Total transacionado de **R$ 16.008.872,12**, liderado por **Cartão de Crédito** (78,34%; ticket médio R$ 163,32) e **Boleto** (17,92%; ticket médio R$ 145,03).
