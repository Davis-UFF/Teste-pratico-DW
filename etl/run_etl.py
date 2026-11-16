import argparse
import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd

DB_PATH = "olist_dw.db"
DATA_DIR = Path("data")
DDL_PATH = Path("sql/ddl_dw.sql")

ESTADOS_INFO = {
    'AC': ('Acre', 'Norte'), 'AL': ('Alagoas', 'Nordeste'), 'AP': ('Amapá', 'Norte'),
    'AM': ('Amazonas', 'Norte'), 'BA': ('Bahia', 'Nordeste'), 'CE': ('Ceará', 'Nordeste'),
    'DF': ('Distrito Federal', 'Centro-Oeste'), 'ES': ('Espírito Santo', 'Sudeste'),
    'GO': ('Goiás', 'Centro-Oeste'), 'MA': ('Maranhão', 'Nordeste'), 'MT': ('Mato Grosso', 'Centro-Oeste'),
    'MS': ('Mato Grosso do Sul', 'Centro-Oeste'), 'MG': ('Minas Gerais', 'Sudeste'),
    'PA': ('Pará', 'Norte'), 'PB': ('Paraíba', 'Nordeste'), 'PR': ('Paraná', 'Sul'),
    'PE': ('Pernambuco', 'Nordeste'), 'PI': ('Piauí', 'Nordeste'), 'RJ': ('Rio de Janeiro', 'Sudeste'),
    'RN': ('Rio Grande do Norte', 'Nordeste'), 'RS': ('Rio Grande do Sul', 'Sul'),
    'RO': ('Rondônia', 'Norte'), 'RR': ('Roraima', 'Norte'), 'SC': ('Santa Catarina', 'Sul'),
    'SP': ('São Paulo', 'Sudeste'), 'SE': ('Sergipe', 'Nordeste'), 'TO': ('Tocantins', 'Norte')
}

FERIADOS_FIXOS = {
    '01-01': 'Confraternização Universal',
    '04-21': 'Tiradentes',
    '05-01': 'Dia do Trabalho',
    '09-07': 'Independência do Brasil',
    '10-12': 'Nossa Senhora Aparecida',
    '11-02': 'Finados',
    '11-15': 'Proclamação da República',
    '12-25': 'Natal',
}

FERIADOS_MOVEIS = {
    '2016-02-09': 'Carnaval', '2016-03-25': 'Sexta-Feira Santa', '2016-05-26': 'Corpus Christi', '2016-11-25': 'Black Friday',
    '2017-02-28': 'Carnaval', '2017-04-14': 'Sexta-Feira Santa', '2017-06-15': 'Corpus Christi', '2017-11-24': 'Black Friday',
    '2018-02-13': 'Carnaval', '2018-03-30': 'Sexta-Feira Santa', '2018-05-31': 'Corpus Christi', '2018-11-23': 'Black Friday',
}

MESES_PT = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}

DIAS_SEMANA_PT = {
    0: 'Segunda-feira', 1: 'Terça-feira', 2: 'Quarta-feira',
    3: 'Quinta-feira', 4: 'Sexta-feira', 5: 'Sábado', 6: 'Domingo'
}


def carregar_staging(conn):
    arquivos = {
        'stg_customers': 'olist_customers_dataset.csv',
        'stg_geolocation': 'olist_geolocation_dataset.csv',
        'stg_sellers': 'olist_sellers_dataset.csv',
        'stg_products': 'olist_products_dataset.csv',
        'stg_category_translation': 'product_category_name_translation.csv',
        'stg_orders': 'olist_orders_dataset.csv',
        'stg_order_items': 'olist_order_items_dataset.csv',
        'stg_order_payments': 'olist_order_payments_dataset.csv',
        'stg_order_reviews': 'olist_order_reviews_dataset.csv',
    }
    base_dir = DATA_DIR if DATA_DIR.exists() else Path(".")
    for tabela, nome_csv in arquivos.items():
        df = pd.read_csv(base_dir / nome_csv)
        if tabela == 'stg_order_reviews':
            df = df.drop_duplicates(subset=['review_id', 'order_id'])
        conn.execute(f"DELETE FROM {tabela};")
        df.to_sql(tabela, conn, if_exists='append', index=False)


def popular_dim_tempo(conn):
    datas = pd.date_range(start='2016-01-01', end='2018-12-31', freq='D')
    registros = []
    for dt in datas:
        data_str = dt.strftime('%Y-%m-%d')
        mm_dd = dt.strftime('%m-%d')
        nome_feriado = FERIADOS_MOVEIS.get(data_str) or FERIADOS_FIXOS.get(mm_dd) or 'Dia Normal'
        eh_feriado = 'Sim' if nome_feriado != 'Dia Normal' else 'Não'
        fim_de_semana = 'Sim' if dt.weekday() >= 5 else 'Não'
        semestre = 1 if dt.month <= 6 else 2
        trimestre = (dt.month - 1) // 3 + 1
        registros.append((
            data_str, dt.year, semestre, trimestre, dt.month, MESES_PT[dt.month],
            dt.day, dt.weekday(), DIAS_SEMANA_PT[dt.weekday()], fim_de_semana,
            eh_feriado, nome_feriado
        ))
    conn.executemany("""
        INSERT OR IGNORE INTO dim_tempo (
            data_completa, ano, semestre, trimestre, mes, nome_mes,
            dia, dia_semana, nome_dia_semana, fim_de_semana, eh_feriado, nome_feriado
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, registros)


def popular_dim_cliente_e_vendedor(conn):
    df_geo = pd.read_sql(
        "SELECT geolocation_zip_code_prefix, geolocation_lat, geolocation_lng FROM stg_geolocation",
        conn
    )
    geo_agg = df_geo.groupby('geolocation_zip_code_prefix', as_index=False).agg(
        latitude=('geolocation_lat', 'mean'),
        longitude=('geolocation_lng', 'mean')
    )

    df_cli = pd.read_sql("SELECT * FROM stg_customers", conn)
    df_cli = df_cli.merge(geo_agg, left_on='customer_zip_code_prefix', right_on='geolocation_zip_code_prefix', how='left')
    df_cli['cidade'] = df_cli['customer_city'].fillna('Não Informada').str.strip().str.title()
    df_cli['estado_uf'] = df_cli['customer_state'].fillna('NI').str.strip().str.upper()
    df_cli['nome_estado'] = df_cli['estado_uf'].map(lambda uf: ESTADOS_INFO.get(uf, ('Não Informado', 'Não Informada'))[0])
    df_cli['regiao'] = df_cli['estado_uf'].map(lambda uf: ESTADOS_INFO.get(uf, ('Não Informado', 'Não Informada'))[1])

    cli_rows = list(zip(
        df_cli['customer_id'], df_cli['customer_unique_id'], df_cli['customer_zip_code_prefix'],
        df_cli['cidade'], df_cli['estado_uf'], df_cli['nome_estado'], df_cli['regiao'],
        df_cli['latitude'].where(pd.notnull(df_cli['latitude']), None),
        df_cli['longitude'].where(pd.notnull(df_cli['longitude']), None)
    ))
    conn.executemany("""
        INSERT OR IGNORE INTO dim_cliente (
            id_cliente_pedido, id_cliente_unico, cep_prefixo, cidade,
            estado_uf, nome_estado, regiao, latitude, longitude
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, cli_rows)

    df_ven = pd.read_sql("SELECT * FROM stg_sellers", conn)
    df_ven = df_ven.merge(geo_agg, left_on='seller_zip_code_prefix', right_on='geolocation_zip_code_prefix', how='left')
    df_ven['cidade'] = df_ven['seller_city'].fillna('Não Informada').str.strip().str.title()
    df_ven['estado_uf'] = df_ven['seller_state'].fillna('NI').str.strip().str.upper()
    df_ven['nome_estado'] = df_ven['estado_uf'].map(lambda uf: ESTADOS_INFO.get(uf, ('Não Informado', 'Não Informada'))[0])
    df_ven['regiao'] = df_ven['estado_uf'].map(lambda uf: ESTADOS_INFO.get(uf, ('Não Informado', 'Não Informada'))[1])

    ven_rows = list(zip(
        df_ven['seller_id'], df_ven['seller_zip_code_prefix'],
        df_ven['cidade'], df_ven['estado_uf'], df_ven['nome_estado'], df_ven['regiao'],
        df_ven['latitude'].where(pd.notnull(df_ven['latitude']), None),
        df_ven['longitude'].where(pd.notnull(df_ven['longitude']), None)
    ))
    conn.executemany("""
        INSERT OR IGNORE INTO dim_vendedor (
            id_vendedor, cep_prefixo, cidade, estado_uf, nome_estado, regiao, latitude, longitude
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, ven_rows)


def popular_dim_produto(conn):
    df_prod = pd.read_sql("SELECT * FROM stg_products", conn)
    df_trad = pd.read_sql("SELECT * FROM stg_category_translation", conn)
    df_prod = df_prod.merge(df_trad, on='product_category_name', how='left')

    df_prod['categoria_pt'] = (
        df_prod['product_category_name']
        .fillna('sem_categoria')
        .str.replace('_', ' ', regex=False)
        .str.strip()
        .str.title()
    )
    df_prod['categoria_en'] = (
        df_prod['product_category_name_english']
        .fillna('Uncategorized')
        .str.replace('_', ' ', regex=False)
        .str.strip()
        .str.title()
    )

    prod_rows = list(zip(
        df_prod['product_id'], df_prod['categoria_pt'], df_prod['categoria_en'],
        df_prod['product_weight_g'].where(pd.notnull(df_prod['product_weight_g']), None),
        df_prod['product_length_cm'].where(pd.notnull(df_prod['product_length_cm']), None),
        df_prod['product_height_cm'].where(pd.notnull(df_prod['product_height_cm']), None),
        df_prod['product_width_cm'].where(pd.notnull(df_prod['product_width_cm']), None),
        df_prod['product_photos_qty'].fillna(0).astype(int)
    ))
    conn.executemany("""
        INSERT OR IGNORE INTO dim_produto (
            id_produto, categoria_pt, categoria_en, peso_g,
            comprimento_cm, altura_cm, largura_cm, qtd_fotos
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, prod_rows)


def popular_dim_pagamento(conn):
    mapa_tipos = {
        'credit_card': 'Cartão de Crédito',
        'boleto': 'Boleto',
        'voucher': 'Voucher',
        'debit_card': 'Cartão de Débito',
        'not_defined': 'Não Definido'
    }
    df_pag = pd.read_sql("SELECT DISTINCT payment_type, payment_installments FROM stg_order_payments", conn)
    df_pag['tipo_pagamento'] = df_pag['payment_type'].map(lambda x: mapa_tipos.get(x, 'Não Definido'))
    df_pag['qtd_parcelas'] = df_pag['payment_installments'].fillna(1).clip(lower=1).astype(int)

    def faixa(p):
        if p == 1:
            return 'À Vista (1x)'
        elif p <= 3:
            return '2x a 3x'
        elif p <= 6:
            return '4x a 6x'
        else:
            return '7x ou mais'

    df_pag['faixa_parcelamento'] = df_pag['qtd_parcelas'].apply(faixa)
    df_pag = df_pag[['tipo_pagamento', 'qtd_parcelas', 'faixa_parcelamento']].drop_duplicates()

    conn.executemany("""
        INSERT OR IGNORE INTO dim_pagamento (tipo_pagamento, qtd_parcelas, faixa_parcelamento)
        VALUES (?, ?, ?);
    """, list(df_pag.itertuples(index=False, name=None)))


def popular_fatos(conn, tipo_carga):
    df_orders = pd.read_sql("SELECT * FROM stg_orders", conn)
    df_orders['dt_compra'] = pd.to_datetime(df_orders['order_purchase_timestamp'])

    if tipo_carga == 'inicial':
        df_orders = df_orders[df_orders['dt_compra'] <= '2017-12-31 23:59:59'].copy()
    elif tipo_carga == 'incremental':
        df_orders = df_orders[df_orders['dt_compra'] >= '2018-01-01 00:00:00'].copy()
    else:
        raise ValueError("tipo_carga deve ser 'inicial' ou 'incremental'")

    map_tempo = dict(conn.execute("SELECT data_completa, sk_tempo FROM dim_tempo").fetchall())
    map_cliente = dict(conn.execute("SELECT id_cliente_pedido, sk_cliente FROM dim_cliente").fetchall())
    map_produto = dict(conn.execute("SELECT id_produto, sk_produto FROM dim_produto").fetchall())
    map_vendedor = dict(conn.execute("SELECT id_vendedor, sk_vendedor FROM dim_vendedor").fetchall())
    map_pagamento = dict(conn.execute("SELECT tipo_pagamento || '|' || qtd_parcelas, sk_pagamento FROM dim_pagamento").fetchall())

    # 1. fato_pedidos
    df_rev = pd.read_sql("SELECT order_id, AVG(review_score) AS nota_avaliacao FROM stg_order_reviews GROUP BY order_id", conn)
    df_ped = df_orders.merge(df_rev, on='order_id', how='left')

    df_ped['dt_aprov'] = pd.to_datetime(df_ped['order_approved_at'])
    df_ped['dt_transp'] = pd.to_datetime(df_ped['order_delivered_carrier_date'])
    df_ped['dt_entrega'] = pd.to_datetime(df_ped['order_delivered_customer_date'])
    df_ped['dt_estimada'] = pd.to_datetime(df_ped['order_estimated_delivery_date'])

    df_ped['sk_tempo_compra'] = df_ped['dt_compra'].dt.strftime('%Y-%m-%d').map(map_tempo)
    df_ped['sk_tempo_entrega'] = df_ped['dt_entrega'].dt.strftime('%Y-%m-%d').map(map_tempo)
    df_ped['sk_cliente'] = df_ped['customer_id'].map(map_cliente)

    df_ped['dias_aprovacao'] = (df_ped['dt_aprov'] - df_ped['dt_compra']).dt.total_seconds() / 86400.0
    df_ped['dias_transporte'] = (df_ped['dt_entrega'] - df_ped['dt_transp']).dt.total_seconds() / 86400.0
    df_ped['dias_entrega_total'] = (df_ped['dt_entrega'] - df_ped['dt_compra']).dt.total_seconds() / 86400.0
    df_ped['dias_diferenca_prazo'] = (df_ped['dt_entrega'] - df_ped['dt_estimada']).dt.total_seconds() / 86400.0
    df_ped['flag_atraso'] = np.where(
        df_ped['dt_entrega'].notnull() & df_ped['dt_estimada'].notnull(),
        (df_ped['dt_entrega'] > df_ped['dt_estimada']).astype(int),
        np.nan
    )

    ped_rows = [
        (
            r.order_id, r.order_status, int(r.sk_tempo_compra),
            int(r.sk_tempo_entrega) if pd.notnull(r.sk_tempo_entrega) else None,
            int(r.sk_cliente), 1,
            round(r.dias_aprovacao, 2) if pd.notnull(r.dias_aprovacao) else None,
            round(r.dias_transporte, 2) if pd.notnull(r.dias_transporte) else None,
            round(r.dias_entrega_total, 2) if pd.notnull(r.dias_entrega_total) else None,
            round(r.dias_diferenca_prazo, 2) if pd.notnull(r.dias_diferenca_prazo) else None,
            int(r.flag_atraso) if pd.notnull(r.flag_atraso) else None,
            round(r.nota_avaliacao, 2) if pd.notnull(r.nota_avaliacao) else None
        )
        for r in df_ped.itertuples()
    ]
    conn.executemany("""
        INSERT OR IGNORE INTO fato_pedidos (
            id_pedido_natural, status_pedido, sk_tempo_compra, sk_tempo_entrega,
            sk_cliente, qtd_pedidos, dias_aprovacao, dias_transporte,
            dias_entrega_total, dias_diferenca_prazo, flag_atraso, nota_avaliacao
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, ped_rows)

    # 2. fato_itens_venda
    df_items = pd.read_sql("SELECT * FROM stg_order_items", conn)
    df_items = df_items.merge(df_ped[['order_id', 'sk_tempo_compra', 'sk_cliente']], on='order_id', how='inner')
    df_items['sk_produto'] = df_items['product_id'].map(map_produto)
    df_items['sk_vendedor'] = df_items['seller_id'].map(map_vendedor)
    df_items['price'] = df_items['price'].clip(lower=0)
    df_items['freight_value'] = df_items['freight_value'].clip(lower=0)
    df_items['valor_total_item'] = (df_items['price'] + df_items['freight_value']).round(2)

    item_rows = [
        (r.order_id, int(r.order_item_id), int(r.sk_tempo_compra), int(r.sk_cliente),
         int(r.sk_produto), int(r.sk_vendedor), 1, float(r.price), float(r.freight_value), float(r.valor_total_item))
        for r in df_items.itertuples()
    ]
    conn.executemany("""
        INSERT OR IGNORE INTO fato_itens_venda (
            id_pedido_natural, numero_item, sk_tempo_compra, sk_cliente,
            sk_produto, sk_vendedor, quantidade_item, valor_produto, valor_frete, valor_total_item
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, item_rows)

    # 3. fato_pagamentos
    mapa_tipos = {
        'credit_card': 'Cartão de Crédito',
        'boleto': 'Boleto',
        'voucher': 'Voucher',
        'debit_card': 'Cartão de Débito',
        'not_defined': 'Não Definido'
    }
    df_pays = pd.read_sql("SELECT * FROM stg_order_payments", conn)
    df_pays = df_pays.merge(df_ped[['order_id', 'sk_tempo_compra', 'sk_cliente']], on='order_id', how='inner')
    df_pays['tipo_pt'] = df_pays['payment_type'].map(lambda x: mapa_tipos.get(x, 'Não Definido'))
    df_pays['parcelas_limpo'] = df_pays['payment_installments'].fillna(1).clip(lower=1).astype(int)
    df_pays['chave_pag'] = df_pays['tipo_pt'] + '|' + df_pays['parcelas_limpo'].astype(str)
    df_pays['sk_pagamento'] = df_pays['chave_pag'].map(map_pagamento)
    df_pays['payment_value'] = df_pays['payment_value'].clip(lower=0)
    df_pays['valor_medio_parcela'] = (df_pays['payment_value'] / df_pays['parcelas_limpo']).round(2)

    pay_rows = [
        (r.order_id, int(r.payment_sequential), int(r.sk_tempo_compra), int(r.sk_cliente),
         int(r.sk_pagamento), float(r.payment_value), int(r.parcelas_limpo), float(r.valor_medio_parcela))
        for r in df_pays.itertuples()
    ]
    conn.executemany("""
        INSERT OR IGNORE INTO fato_pagamentos (
            id_pedido_natural, sequencia_pagamento, sk_tempo_compra, sk_cliente,
            sk_pagamento, valor_pagamento, qtd_parcelas, valor_medio_parcela
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, pay_rows)


def main():
    parser = argparse.ArgumentParser(description="Pipeline ETL Olist -> SQLite DW")
    parser.add_argument("--carga", choices=["inicial", "incremental"], required=True, help="Tipo de carga: inicial (até 2017) ou incremental (2018+)")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(DDL_PATH.read_text(encoding="utf-8"))

    carregar_staging(conn)
    popular_dim_tempo(conn)
    popular_dim_cliente_e_vendedor(conn)
    popular_dim_produto(conn)
    popular_dim_pagamento(conn)
    popular_fatos(conn, args.carga)
    conn.commit()

    print(f"=== Carga '{args.carga}' concluída com sucesso! ===")
    for tabela in ['dim_tempo', 'dim_cliente', 'dim_produto', 'dim_vendedor', 'dim_pagamento', 'fato_itens_venda', 'fato_pedidos', 'fato_pagamentos']:
        qtd = conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
        print(f"  {tabela:<20}: {qtd:>8} registros")
    conn.close()


if __name__ == "__main__":
    main()
