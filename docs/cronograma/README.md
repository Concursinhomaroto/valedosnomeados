# Cronograma Ebserh / HU Brasil

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

## Ritmo, início e prazo (v2, 03/11/2026)

O prompt original assumia 5h por dia a partir de 09/11. O calendário agora é **gerado** a partir de três coisas
suas, em ⚙️ na Agenda:

- **Início** (padrão: amanhã, ao ativar) e **horas por dia** (padrão 4h; 1 a 12, de 0,5 em 0,5). Mudar as horas vale a partir
  de hoje (`db.cronograma.fases`): o que já passou continua no ritmo antigo, então não vira atraso falso.
- **Prazo de 3 meses** a partir do início. A semana final (7 dias) fica antes dele. A faixa mostra "No prazo" ou
  "N dias além do prazo · fecha com ~Xh/dia".
- **Trilha complementar fora por padrão**: Dir. Administrativo, História de Campina Grande e Informática não estavam no último edital (Ebserh/FGV 03/2024). O edital novo ainda não saiu; quando sair, confira.
- **Edital ainda não publicado**: o plano segue o último edital. A faixa avisa isso até você tocar em "O edital saiu" (`db.cronograma.editalSaiu`).

Capacidade do dia = horas × 0,66 (do prompt: ~3h18 de assunto novo num dia de 5h; o resto é revisão D+1/D+7/D+30, erros e
flashcards). Um assunto entra no dia se pelo menos metade dele couber. Com 4h são ~7 assuntos novos por dia.

Simulação (começando em 03/11, 534 assuntos do edital, 598 com a complementar; fim = último assunto novo):

| Por dia | Só o edital | Com a complementar |
|---|---|---|
| 4h | 01/02 (passa do prazo) | 10/02 |
| 4h30 | 22/01 (cabe) | 29/01 |
| 5h | 14/01 | 20/01 |

O dia a dia deixa de coincidir com a tabela do prompt (a ordem dos assuntos e dos blocos é a mesma).

## Grade por hora e rodízio (v3, 04/11/2026)

**Grade por hora** (botão "🕐 Grade por hora" na Agenda): a semana como uma grade de horários, dias nas colunas e
horas nas linhas. Cada dia de estudo vira blocos em sequência a partir da hora em que você começa (⚙️, padrão 08:00),
com uma pausa de 15 min a cada ~80 min seguidos, e os blocos somam as horas do dia:

| Dia | Blocos |
|---|---|
| Estudo | Revisões e flashcards (40% do que sobra) → assunto novo de cada matéria (o mais pesado primeiro) → questões do dia (45%) → erros (15%) |
| Domingo | Revisão da semana 25% · refazer os erros 20% · simulado de 30 45% · flashcards 10% |
| Feriado | 1h de revisão leve |
| Semana final | O tema do dia (seção 7 do prompt); o sábado é o simulado completo de 60 |

Clicar num bloco abre o dia; o do simulado abre o simulado. O que você digitou na Agenda sem horário aparece no topo do dia.
Embaixo, **"Tempo por matéria"** soma a semana por matéria (Específicos, Políticas Públicas, Português, Legislação Ebserh),
revisões, questões e erros, e avisa quando uma matéria não tem assunto novo naquela semana.

**Rodízio** (ligado por padrão; ⚙️ desliga): na ordem do prompt o Português só aparece de meados de dezembro a meados de
janeiro e a Legislação Ebserh some depois da 2ª semana. Com o rodízio, sempre entra o assunto do bloco que está mais atrás
*em proporção ao próprio tamanho*, então Específicos, Políticas Públicas e Português avançam juntos e terminam juntos; a
Legislação Ebserh (7 assuntos) termina antes e sobra tempo para revisá-la. A ordem *dentro* de cada bloco não muda.

**Atraso** passa a ter um "marco zero": ao mudar a estrutura do plano (rodízio, trilha complementar) o app guarda o atraso
daquele instante e só conta a diferença a partir dali (`db.cronograma.zero`). Sem isso, trocar a ordem inventaria ou apagaria atraso.

## Agenda: grade 06h–23h e lista dos 7 dias
- A grade por hora mostra o dia inteiro (06:00–23:00; estende só se o estudo passar das 23h) e já abre rolada para a hora de início.
- A lista "Próximos 7 dias" fica oculta com o cronograma ativo; volta em ⚙️ → "Mostrar também a lista dos 7 dias" (`cronograma.listaDias`).
- O "＋" no cabeçalho de cada dia adiciona compromissos; itens novos levam `criadoEm` e aparecem no cabeçalho do dia. Itens antigos (sem `criadoEm`) seguem escondidos/contáveis/apagáveis como antes.
