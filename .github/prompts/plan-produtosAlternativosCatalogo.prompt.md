## Plano: Produtos Alternativos no Catálogo

Implementar a flag `outros` recebida em `TX_TEXTO`.

Quando `outros=true` e o cliente não possuir contrato:

- 1 produto principal com `status: "normal"`;
- até 3 produtos adicionais com `status: "alternativo"`;
- todos com a mesma quantidade solicitada;
- alternativas geradas por item do pedido.

Quando `outros=false`, ausente ou inválido, o fluxo permanece igual. Se existir qualquer produto no `contract_pool`, nenhuma alternativa será criada, independentemente da flag.

**Etapas**

1. Adicionar `outros` ao `AgentState`.
2. Ler e normalizar `outros` em [app/services/worker_service.py](app/services/worker_service.py), propagando-o para o grafo.
3. Ajustar [app/orcamento/agents/no_catalogo.py](app/orcamento/agents/no_catalogo.py) para preservar os candidatos ranqueados e retornar o principal mais três alternativas distintas.
4. Aplicar a expansão somente quando `outros is True` e `contract_pool` estiver vazio.
5. Manter histórico, contrato, `source` e `status_estoque` funcionando como atualmente.
6. Propagar o novo campo `status` para `produtos_mapeados`.
7. Atualizar a rota direta em [app/api/rotas/pedidos.py](app/api/rotas/pedidos.py), caso ela também receba essa flag.
8. Criar testes mockados para:
   - `outros=false`;
   - `outros=true` sem contrato;
   - `outros=true` com contrato;
   - flag ausente;
   - catálogo com menos de três alternativas;
   - ausência de duplicidade entre produtos.

**Persistência**

A API deve retornar `status` diretamente no JSON. Na persistência, como [app/repositories/repositorio_orcamento.py](app/repositories/repositorio_orcamento.py) já insere a origem do produto em `DS_MARCA` na tabela `TEMP_REL_ORCAMENTO`, utilizar esse mesmo atributo para identificar o status: manter o valor atual para o produto principal e gravar `alternativo` nos três produtos adicionais. O frontend poderá identificar as alternativas por esse valor em `DS_MARCA`, sem criar uma nova coluna na tabela.

**Verificação**

- Executar `python -m compileall app/orcamento app/services app/api app/repositories`.
- Executar os novos testes sem OpenAI ou banco real.
- Confirmar que contratos nunca recebem alternativas.
- Confirmar que cada item sem contrato gera um principal normal e até três alternativas.