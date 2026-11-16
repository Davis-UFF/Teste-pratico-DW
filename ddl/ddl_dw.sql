PRAGMA foreign_keys = ON;

-- 1. CAMADA STAGING (stg_*) - Espelho tipado dos CSVs brutos

CREATE TABLE IF NOT EXISTS stg_customers (
    customer_id TEXT PRIMARY KEY,
    customer_unique_id TEXT,
    customer_zip_code_prefix INTEGER,
    customer_city TEXT,
    customer_state TEXT
);

CREATE TABLE IF NOT EXISTS stg_geolocation (
    geolocation_zip_code_prefix INTEGER,
    geolocation_lat REAL,
    geolocation_lng REAL,
    geolocation_city TEXT,
    geolocation_state TEXT
);

CREATE TABLE IF NOT EXISTS stg_sellers (
    seller_id TEXT PRIMARY KEY,
    seller_zip_code_prefix INTEGER,
    seller_city TEXT,
    seller_state TEXT
);

CREATE TABLE IF NOT EXISTS stg_products (
    product_id TEXT PRIMARY KEY,
    product_category_name TEXT,
    product_name_lenght REAL,
    product_description_lenght REAL,
    product_photos_qty REAL,
    product_weight_g REAL,
    product_length_cm REAL,
    product_height_cm REAL,
    product_width_cm REAL
);

CREATE TABLE IF NOT EXISTS stg_category_translation (
    product_category_name TEXT PRIMARY KEY,
    product_category_name_english TEXT
);

CREATE TABLE IF NOT EXISTS stg_orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT,
    order_status TEXT,
    order_purchase_timestamp TEXT,
    order_approved_at TEXT,
    order_delivered_carrier_date TEXT,
    order_delivered_customer_date TEXT,
    order_estimated_delivery_date TEXT
);

CREATE TABLE IF NOT EXISTS stg_order_items (
    order_id TEXT,
    order_item_id INTEGER,
    product_id TEXT,
    seller_id TEXT,
    shipping_limit_date TEXT,
    price REAL,
    freight_value REAL,
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE IF NOT EXISTS stg_order_payments (
    order_id TEXT,
    payment_sequential INTEGER,
    payment_type TEXT,
    payment_installments INTEGER,
    payment_value REAL,
    PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE IF NOT EXISTS stg_order_reviews (
    review_id TEXT,
    order_id TEXT,
    review_score INTEGER,
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TEXT,
    review_answer_timestamp TEXT,
    PRIMARY KEY (review_id, order_id)
);

-- 2. CAMADA DATA WAREHOUSE (dim_* e fato_*) - Esquema Estrela

CREATE TABLE IF NOT EXISTS dim_tempo (
    sk_tempo INTEGER PRIMARY KEY AUTOINCREMENT,
    data_completa TEXT NOT NULL UNIQUE,
    ano INTEGER NOT NULL,
    semestre INTEGER NOT NULL,
    trimestre INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    nome_mes TEXT NOT NULL,
    dia INTEGER NOT NULL,
    dia_semana INTEGER NOT NULL,
    nome_dia_semana TEXT NOT NULL,
    fim_de_semana TEXT NOT NULL,
    eh_feriado TEXT NOT NULL,
    nome_feriado TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_cliente (
    sk_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente_pedido TEXT NOT NULL UNIQUE,
    id_cliente_unico TEXT NOT NULL,
    cep_prefixo INTEGER,
    cidade TEXT NOT NULL,
    estado_uf TEXT NOT NULL,
    nome_estado TEXT NOT NULL,
    regiao TEXT NOT NULL,
    latitude REAL,
    longitude REAL
);

CREATE TABLE IF NOT EXISTS dim_produto (
    sk_produto INTEGER PRIMARY KEY AUTOINCREMENT,
    id_produto TEXT NOT NULL UNIQUE,
    categoria_pt TEXT NOT NULL,
    categoria_en TEXT NOT NULL,
    peso_g REAL,
    comprimento_cm REAL,
    altura_cm REAL,
    largura_cm REAL,
    qtd_fotos INTEGER
);

CREATE TABLE IF NOT EXISTS dim_vendedor (
    sk_vendedor INTEGER PRIMARY KEY AUTOINCREMENT,
    id_vendedor TEXT NOT NULL UNIQUE,
    cep_prefixo INTEGER,
    cidade TEXT NOT NULL,
    estado_uf TEXT NOT NULL,
    nome_estado TEXT NOT NULL,
    regiao TEXT NOT NULL,
    latitude REAL,
    longitude REAL
);

CREATE TABLE IF NOT EXISTS dim_pagamento (
    sk_pagamento INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_pagamento TEXT NOT NULL,
    qtd_parcelas INTEGER NOT NULL,
    faixa_parcelamento TEXT NOT NULL,
    UNIQUE (tipo_pagamento, qtd_parcelas)
);

CREATE TABLE IF NOT EXISTS fato_itens_venda (
    sk_fato_item INTEGER PRIMARY KEY AUTOINCREMENT,
    id_pedido_natural TEXT NOT NULL,
    numero_item INTEGER NOT NULL,
    sk_tempo_compra INTEGER NOT NULL,
    sk_cliente INTEGER NOT NULL,
    sk_produto INTEGER NOT NULL,
    sk_vendedor INTEGER NOT NULL,
    quantidade_item INTEGER NOT NULL DEFAULT 1,
    valor_produto REAL NOT NULL CHECK (valor_produto >= 0),
    valor_frete REAL NOT NULL CHECK (valor_frete >= 0),
    valor_total_item REAL NOT NULL CHECK (valor_total_item >= 0),
    UNIQUE (id_pedido_natural, numero_item),
    FOREIGN KEY (sk_tempo_compra) REFERENCES dim_tempo (sk_tempo),
    FOREIGN KEY (sk_cliente) REFERENCES dim_cliente (sk_cliente),
    FOREIGN KEY (sk_produto) REFERENCES dim_produto (sk_produto),
    FOREIGN KEY (sk_vendedor) REFERENCES dim_vendedor (sk_vendedor)
);

CREATE TABLE IF NOT EXISTS fato_pedidos (
    sk_fato_pedido INTEGER PRIMARY KEY AUTOINCREMENT,
    id_pedido_natural TEXT NOT NULL UNIQUE,
    status_pedido TEXT NOT NULL,
    sk_tempo_compra INTEGER NOT NULL,
    sk_tempo_entrega INTEGER,
    sk_cliente INTEGER NOT NULL,
    qtd_pedidos INTEGER NOT NULL DEFAULT 1,
    dias_aprovacao REAL,
    dias_transporte REAL,
    dias_entrega_total REAL,
    dias_diferenca_prazo REAL,
    flag_atraso INTEGER,
    nota_avaliacao REAL,
    FOREIGN KEY (sk_tempo_compra) REFERENCES dim_tempo (sk_tempo),
    FOREIGN KEY (sk_tempo_entrega) REFERENCES dim_tempo (sk_tempo),
    FOREIGN KEY (sk_cliente) REFERENCES dim_cliente (sk_cliente)
);

CREATE TABLE IF NOT EXISTS fato_pagamentos (
    sk_fato_pagamento INTEGER PRIMARY KEY AUTOINCREMENT,
    id_pedido_natural TEXT NOT NULL,
    sequencia_pagamento INTEGER NOT NULL,
    sk_tempo_compra INTEGER NOT NULL,
    sk_cliente INTEGER NOT NULL,
    sk_pagamento INTEGER NOT NULL,
    valor_pagamento REAL NOT NULL CHECK (valor_pagamento >= 0),
    qtd_parcelas INTEGER NOT NULL CHECK (qtd_parcelas >= 0),
    valor_medio_parcela REAL NOT NULL CHECK (valor_medio_parcela >= 0),
    UNIQUE (id_pedido_natural, sequencia_pagamento),
    FOREIGN KEY (sk_tempo_compra) REFERENCES dim_tempo (sk_tempo),
    FOREIGN KEY (sk_cliente) REFERENCES dim_cliente (sk_cliente),
    FOREIGN KEY (sk_pagamento) REFERENCES dim_pagamento (sk_pagamento)
);

-- 3. ÍNDICES PARA DESEMPENHO DAS CONSULTAS ANALÍTICAS

CREATE INDEX IF NOT EXISTS idx_fato_itens_tempo ON fato_itens_venda (sk_tempo_compra);
CREATE INDEX IF NOT EXISTS idx_fato_itens_cliente ON fato_itens_venda (sk_cliente);
CREATE INDEX IF NOT EXISTS idx_fato_itens_produto ON fato_itens_venda (sk_produto);
CREATE INDEX IF NOT EXISTS idx_fato_itens_vendedor ON fato_itens_venda (sk_vendedor);

CREATE INDEX IF NOT EXISTS idx_fato_pedidos_tempo_compra ON fato_pedidos (sk_tempo_compra);
CREATE INDEX IF NOT EXISTS idx_fato_pedidos_tempo_entrega ON fato_pedidos (sk_tempo_entrega);
CREATE INDEX IF NOT EXISTS idx_fato_pedidos_cliente ON fato_pedidos (sk_cliente);
CREATE INDEX IF NOT EXISTS idx_fato_pedidos_status ON fato_pedidos (status_pedido);

CREATE INDEX IF NOT EXISTS idx_fato_pagamentos_tempo ON fato_pagamentos (sk_tempo_compra);
CREATE INDEX IF NOT EXISTS idx_fato_pagamentos_cliente ON fato_pagamentos (sk_cliente);
CREATE INDEX IF NOT EXISTS idx_fato_pagamentos_tipo ON fato_pagamentos (sk_pagamento);

CREATE INDEX IF NOT EXISTS idx_dim_tempo_ano_mes ON dim_tempo (ano, mes);
CREATE INDEX IF NOT EXISTS idx_dim_cliente_regiao_uf ON dim_cliente (regiao, estado_uf);
CREATE INDEX IF NOT EXISTS idx_dim_produto_categoria ON dim_produto (categoria_pt);