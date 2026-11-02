# Cronograma Ebserh / HU Brasil (09/11/2026 a 31/01/2027)

- `ebserh-2026-prompt.md` — o prompt original (fonte da verdade do conteúdo).
- `ebserh-2026.json` — o cronograma em dados: 73 capítulos (id, nome, nº de assuntos, bloco) e 84 dias
  (`est` = estudo, `rev` = revisão de domingo, `fer` = feriado, `fin` = semana final). O mesmo JSON está
  embutido em `app/index.html` (`CRON_DADOS`); ao mudar um, mude o outro.

## Como funciona

O cronograma **não grava uma tarefa por dia**. Ele é uma fila ordenada dos 598 assuntos e um calendário
de cargas por dia; o plano de cada dia é calculado na hora a partir do que já foi concluído
(`crPlano()` em `app/index.html`). Por isso:

| Pedido do prompt | Como é atendido |
|---|---|
| Remarcar se não cumprir | Automático: o que não foi concluído desliza para os próximos dias de estudo. Domingo e feriado nunca recebem assunto novo. |
| Adiantar | Concluir ou dar "já sei" libera tempo; a fila puxa os próximos assuntos para o mesmo dia até completar a carga. "Já sei" gasta ~2 min (não os ~22 do assunto) e não rende XP. |
| Folga / encurtar a data final | Dias de estudo que sobram viram "Folga". "Encurtar fim" move a semana final para logo depois do último assunto. |
| Revisões D+1, D+7, D+30 | Ao concluir, vão para `db.revisions[subId]` (a Revisão que já existia). Com o cronograma ligado, o primeiro estudo pelo cronômetro também gera as três. |
| `[CONFERIR]` | O resumo (`sub.resumo.texto`) com `[CONFERIR]` ou "de memória, conferir" mostra ⚠️ e exige confirmar a leitura antes de concluir. |
| Simulado de domingo | 30 questões dos assuntos da semana (seg–sáb), sorteadas na proporção da prova (30/15/10/5 de 60), FGV primeiro quando a questão traz banca. Há também "Erros da semana". |
| Painel | Dia X de 69, meta do dia (nº de assuntos e tempo), atraso, folga, data da prova (Editais) e % por bloco. |

## Decisões que o prompt não fecha

- **Concluído = `db.cronograma.feitos[subId]`**, não `sub.studied`. Assunto estudado antes do cronograma continua nele até você confirmar; nada é dado como estudado sozinho.
- **Tempo por assunto**: 22 min; 15 min para Português e Informática; 28 min para UTI, Procedimentos, Vacinação, Urgência e Farmacologia. A carga do dia é a soma dos assuntos que o prompt planejou para ele.
- **Capítulos** são achados pelo id do prompt e, se não existir, pelo nome. Os não achados aparecem num aviso.
- **Questões da banca**: o Acervo não tem campo de banca por questão garantido; a prioridade FGV olha `banca`, `fonte`, `origem` e `provaBanca` se existirem.
