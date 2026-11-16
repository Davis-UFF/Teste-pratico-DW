-- CONSULTAS ANALÍTICAS DO DATA WAREHOUSE OLIST (20 PERGUNTAS DE NEGÓCIO)

-- PROCESSO 1: VENDAS E RECEITA (fato_itens_venda)

-- P1.1: Qual o valor total dos produtos?
SELECT ROUND(SUM(valor_produto), 2) AS valor_total_produtos
FROM fato_itens_venda;

-- P1.2: Qual o valor total do frete?
SELECT ROUND(SUM(valor_frete), 2) AS valor_total_frete
FROM fato_itens_venda;

-- P1.3: Qual a quantidade de itens vendidos por trimestre?
SELECT t.ano, t.trimestre, COUNT(*) AS qtd_itens_vendidos
FROM fato_itens_venda f
JOIN dim_tempo t ON f.sk_tempo_compra = t.sk_tempo
GROUP BY t.ano, t.trimestre
ORDER BY t.ano, t.trimestre;

-- P1.4: Quais são as 10 categorias de produtos que mais geram faturamento?
SELECT p.categoria_pt, ROUND(SUM(f.valor_produto), 2) AS faturamento_produtos
FROM fato_itens_venda f
JOIN dim_produto p ON f.sk_produto = p.sk_produto
GROUP BY p.categoria_pt
ORDER BY faturamento_produtos DESC
LIMIT 10;

-- P1.5: Qual o ticket médio por item em cada uma das categorias top 10?
SELECT p.categoria_pt,
       ROUND(SUM(f.valor_produto), 2) AS faturamento_produtos,
       ROUND(AVG(f.valor_produto), 2) AS ticket_medio_item
FROM fato_itens_venda f
JOIN dim_produto p ON f.sk_produto = p.sk_produto
GROUP BY p.categoria_pt
ORDER BY faturamento_produtos DESC
LIMIT 10;

-- P1.6: Como o volume de vendas se distribui entre os estados (UF) dos clientes?
SELECT c.estado_uf, c.nome_estado, COUNT(*) AS qtd_itens_vendidos
FROM fato_itens_venda f
JOIN dim_cliente c ON f.sk_cliente = c.sk_cliente
GROUP BY c.estado_uf, c.nome_estado
ORDER BY qtd_itens_vendidos DESC;

-- P1.7: Como o faturamento se distribui entre as regiões dos clientes?
SELECT c.regiao,
       ROUND(SUM(f.valor_produto), 2) AS faturamento_produtos,
       ROUND(SUM(f.valor_total_item), 2) AS receita_com_frete
FROM fato_itens_venda f
JOIN dim_cliente c ON f.sk_cliente = c.sk_cliente
GROUP BY c.regiao
ORDER BY faturamento_produtos DESC;

-- P1.8: Quais são os 10 vendedores (sellers) com maior receita acumulada?
SELECT v.id_vendedor, ROUND(SUM(f.valor_produto), 2) AS receita_acumulada
FROM fato_itens_venda f
JOIN dim_vendedor v ON f.sk_vendedor = v.sk_vendedor
GROUP BY v.id_vendedor
ORDER BY receita_acumulada DESC
LIMIT 10;

-- P1.9: A quais estados pertencem os top 10 vendedores?
SELECT v.id_vendedor, v.estado_uf, v.cidade,
       ROUND(SUM(f.valor_produto), 2) AS receita_acumulada
FROM fato_itens_venda f
JOIN dim_vendedor v ON f.sk_vendedor = v.sk_vendedor
GROUP BY v.id_vendedor, v.estado_uf, v.cidade
ORDER BY receita_acumulada DESC
LIMIT 10;

-- PROCESSO 2: LOGÍSTICA DE ENTREGA E SATISFAÇÃO (fato_pedidos)

-- P2.1: Qual é o tempo médio real de entrega (em dias)?
SELECT ROUND(AVG(dias_entrega_total), 2) AS tempo_medio_entrega_dias
FROM fato_pedidos
WHERE dias_entrega_total IS NOT NULL;

-- P2.2: Qual a taxa de pedidos entregues com atraso por região do cliente?
SELECT c.regiao,
       COUNT(*) AS pedidos_entregues,
       SUM(f.flag_atraso) AS pedidos_atrasados,
       ROUND(AVG(f.flag_atraso) * 100, 2) AS taxa_atraso_pct
FROM fato_pedidos f
JOIN dim_cliente c ON f.sk_cliente = c.sk_cliente
WHERE f.flag_atraso IS NOT NULL
GROUP BY c.regiao
ORDER BY taxa_atraso_pct DESC;

-- P2.3: Qual a nota média de avaliação dos clientes?
SELECT ROUND(AVG(nota_avaliacao), 2) AS nota_media_geral
FROM fato_pedidos
WHERE nota_avaliacao IS NOT NULL;

-- P2.4: Qual a nota média quando entregue dentro do prazo?
SELECT ROUND(AVG(nota_avaliacao), 2) AS nota_media_no_prazo
FROM fato_pedidos
WHERE flag_atraso = 0 AND nota_avaliacao IS NOT NULL;

-- P2.5: Qual a nota média quando entregue fora do prazo?
SELECT ROUND(AVG(nota_avaliacao), 2) AS nota_media_atrasado
FROM fato_pedidos
WHERE flag_atraso = 1 AND nota_avaliacao IS NOT NULL;

-- P2.6: Como evoluiu a nota média de satisfação dos clientes e o volume de pedidos ao longo dos meses?
SELECT t.ano, t.mes, t.nome_mes,
       COUNT(*) AS total_pedidos,
       ROUND(AVG(f.nota_avaliacao), 2) AS nota_media
FROM fato_pedidos f
JOIN dim_tempo t ON f.sk_tempo_compra = t.sk_tempo
GROUP BY t.ano, t.mes, t.nome_mes
ORDER BY t.ano, t.mes;

-- PROCESSO 3: MEIOS DE PAGAMENTO (fato_pagamentos)

-- P3.1: Qual é o valor total transacionado?
SELECT ROUND(SUM(valor_pagamento), 2) AS valor_total_transacionado
FROM fato_pagamentos;

-- P3.2: Qual a participação percentual (%) por meio de pagamento?
SELECT p.tipo_pagamento,
       ROUND(SUM(f.valor_pagamento), 2) AS valor_total,
       ROUND(SUM(f.valor_pagamento) * 100.0 / (SELECT SUM(valor_pagamento) FROM fato_pagamentos), 2) AS participacao_pct
FROM fato_pagamentos f
JOIN dim_pagamento p ON f.sk_pagamento = p.sk_pagamento
GROUP BY p.tipo_pagamento
ORDER BY valor_total DESC;

-- P3.3: Qual o ticket médio por meio de pagamento?
SELECT p.tipo_pagamento,
       ROUND(AVG(f.valor_pagamento), 2) AS ticket_medio_pagamento
FROM fato_pagamentos f
JOIN dim_pagamento p ON f.sk_pagamento = p.sk_pagamento
GROUP BY p.tipo_pagamento
ORDER BY ticket_medio_pagamento DESC;

-- P3.4: Qual o meio de pagamento preferido (Cartão de Crédito vs. Boleto) entre as regiões do Brasil?
SELECT c.regiao, p.tipo_pagamento,
       COUNT(*) AS qtd_transacoes,
       ROUND(SUM(f.valor_pagamento), 2) AS valor_total
FROM fato_pagamentos f
JOIN dim_pagamento p ON f.sk_pagamento = p.sk_pagamento
JOIN dim_cliente c ON f.sk_cliente = c.sk_cliente
WHERE p.tipo_pagamento IN ('Cartão de Crédito', 'Boleto')
GROUP BY c.regiao, p.tipo_pagamento
ORDER BY c.regiao, valor_total DESC;

-- P3.5: Qual é o comportamento mensal do valor pago em compras realizadas em feriados nacionais vs. dias normais?
SELECT t.ano, t.mes, t.eh_feriado,
       COUNT(*) AS qtd_transacoes,
       ROUND(SUM(f.valor_pagamento), 2) AS valor_total_pago,
       ROUND(AVG(f.valor_pagamento), 2) AS ticket_medio
FROM fato_pagamentos f
JOIN dim_tempo t ON f.sk_tempo_compra = t.sk_tempo
GROUP BY t.ano, t.mes, t.eh_feriado
ORDER BY t.ano, t.mes, t.eh_feriado;