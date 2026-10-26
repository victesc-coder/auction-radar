# Auction Radar

Radar de leilões de veículos. Primeira versão em Python 3.9+, sem dependências externas de execução.

## Executar

Na pasta do projeto:

```sh
python3 -m auction_radar examples/lots.json --now 2026-10-26T08:00:00-03:00
python3 -m unittest discover -s tests -v
```

O exemplo contém **dados fictícios**, não uma oportunidade real. Sem `--now`, usa o horário atual de São Paulo. O comando retorna JSON e cria `radar.sqlite3` com o histórico local. `--database`, `--days` e `--margin` permitem configurar banco, horizonte e margem.

## Regras implementadas

- Considera retirada no estado de SP e leilão com data definida no intervalo de agora (inclusive) até sete dias depois (exclusive).
- Usa valores decimais para dinheiro. A comissão é explícita por lote: `0.05` significa 5%; não há taxa presumida do leiloeiro.
- Custo total = lance × (1 + comissão) + custos adicionais.
- Margem = (revenda estimada − custo total) / revenda estimada.
- Lance máximo = (revenda estimada × (1 − margem desejada) − custos adicionais) / (1 + comissão), arredondado para baixo em centavos e limitado a zero.
- Sem estimativa de revenda positiva, não classifica o lote como oportunidade.
- Guarda observações de todos os lotes importados, inclusive os que não passam no filtro. Repetições idênticas com o mesmo horário não duplicam o histórico; novas observações preservam mudanças de lance.

Os custos adicionais devem incluir reparos, transporte, documentação, taxas fixas, tributos aplicáveis e demais despesas estimadas. A qualidade do resultado depende dessas entradas. Lance observado não é preço final confirmado de arrematação.

## Formato de entrada

Veja `examples/lots.json`. Cada lote exige fonte, identificador na fonte, título, link, UF e cidade de retirada, lance, custos adicionais e comissão. `auction_at` pode ser nulo; quando informado, precisa incluir fuso horário. `resale_estimate` pode ser nulo. Valores monetários devem ser números não negativos, preferencialmente strings decimais.

## Próximas entregas

1. Validar o acesso aos calendários e lotes de Copart, Freitas e Sodré Santoro e implementar um coletor por vez.
2. Priorizar municípios da Grande São Paulo.
3. Registrar resultado e preço final confirmado separadamente do lance observado.
4. Acrescentar procedência, avarias e evidências da estimativa de revenda.
5. Executar automaticamente na nuvem e apresentar oportunidades em um painel.

Esta versão importa arquivos locais: ainda não consulta leiloeiros, estima preços de mercado nem envia alertas automaticamente.
