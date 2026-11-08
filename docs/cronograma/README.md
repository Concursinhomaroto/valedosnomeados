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

## Plano por edital, importar/exportar e ajuste do dia

**Onde:** ⚙️ da Agenda → "Montar / ajustar plano", "Importar agenda", exportar JSON/CSV/.ics e "Copiar prompt para IA externa". O botão "⏱ Ajustar o dia" fica na aba Hoje.

**Modelo (aditivo).** Contas atuais seguem na trilha da Ebserh (`CRON_DADOS`) até aplicarem um plano. `db.agendaPlanos = {ativoId, planos:{id:plano}, versoes:[últimas 5]}`; o plano guarda `editalIds, pct, pesos (min/dia por disciplina), minPorAssunto, excluidos {id: motivo}, prioridade, reforco, config{inicio,horasDia,horaInicio,diasSemana,prazo}`. Em `db.cronograma` ficam o que vale nas duas trilhas: `pins {subId:{ds,travado}}`, `bloqueios [{data,inicio,min,titulo}]`, `indisp [datas]`, `ajusteHoje`. Progresso (`feitos`), revisões, XP, resumos e flashcards não são tocados.

**Regras do gerador.** Blocos = disciplinas do edital (mesmo nome em dois editais vira um bloco). Peso: minutos/dia definidos por você; senão fatia das questões declaradas; sem número nenhum aparece "peso não informado" (nunca estimado em silêncio). Duração padrão por assunto: **30 min** (a trilha da Ebserh continua em 22), ajustável por disciplina e por assunto. Assunto em dois editais entra uma vez (pelo `subId`) e concluir vale para todos. Assunto sem vínculo fica fora da fila, listado em "sem vínculo". Reconciliação por edital: total = na fila + sem vínculo + excluídos. Rodízio ponderado pelo peso; o último diagnóstico por disciplina e o 🎯 reforçam pontos fracos. `prev` (prevalência) nunca é preenchida pelo app.

**Ajustes.** Mover assunto de dia, trocar de matéria e adiantar são "pinos": o resto desliza em volta, pino em dia sem estudo volta à fila e vira aviso. Compromissos e dias indisponíveis reduzem as horas do dia e a grade se reorganiza em volta. "Hoje só X horas / não vou estudar" usam `fases` por data: o calendário-base usa as mesmas horas, então não há atraso falso; o término muda e é mostrado. Revisões D+1/D+7/D+30 e o simulado de domingo não são tocados.

**Importar.** Aceita JSON `vale-agenda-v1`, CSV/planilha colada e .ics (até 2 MB). Sempre mostra prévia com `lidas = aplicadas + ignoradas (motivo)`. Só entra o que vem **a partir de amanhã**. Modos: somar, substituir só o futuro, criar como novo plano. Casa assunto por `subId` e depois pelo nome (do Mapa ou do edital); nome com mais de um candidato pergunta. Sobreposição só com confirmação. Eventos .ics viram bloqueio; dia inteiro vira dia indisponível; recorrência lê só a primeira ocorrência (avisa).

**Limitações conhecidas.** O horário de um assunto dentro do dia não é fixável (só o dia); itens de revisão/questões/erros/simulado importados são ignorados porque o app os gera sozinho; domingo é sempre revisão + simulado; a IA externa é só por copiar/colar (não há chamada automática); `test_edital_peso` e `test_edital_pdf` já falhavam antes desta mudança.

## Agenda manual e "Apagar agendas geradas"
- Sem cronograma ativo a Agenda é **manual**: só a grade por hora com os seus blocos (nada da Ebserh aparece). "＋ Bloco" (ou o ＋ de cada dia) cria um bloco com título, dia, hora, duração e repetição semanal opcional; clicar no bloco edita ou exclui (um só ou a série).
- Blocos manuais são os mesmos `db.cronograma.bloqueios`: com plano ativo, o estudo se reorganiza em volta deles.
- ⚙️ → "🗑 Apagar agendas geradas" desliga a trilha da Ebserh e apaga os planos por edital (versões, assuntos movidos, ajustes do dia). Ficam: o que você concluiu, revisões, blocos manuais e o que você digitou na agenda. A Ebserh só volta se você ativar de novo.
- A lista antiga dos 7 dias só aparece se ligada em ⚙️.

## Filtros do Treino (Banca · Mundo · Chefe · Miniboss)
Painel novo em Treinar ("Montar meu treino"): seleção múltipla com busca, cascata Mundo → Chefe → Miniboss (o de baixo só abre com o de cima; trocar o de cima limpa o que deixou de valer), contagem por opção respeitando os outros filtros, chips com ✕ e "Limpar filtros", status pessoal (resolvidas, não resolvidas, acertei, errei) e, no filtro avançado, palavra-chave, formato, dificuldade e favoritas. "Treinar com estas" pergunta quantidade (10/20/30/todas/outra) e ordem (aleatória ou sequencial). Os filtros ficam na URL (`f_banca`, `f_mundo`, `f_chefe`, `f_mini`, `f_estado`, `f_q`, `f_formato`, `f_nivel`, `f_fav`, `f_av`) e no aparelho; no celular abrem numa gaveta. Banca = campo `banca` da questão (editável no Acervo); sem ele vale **"Cebraspe (estilo)"**. O filtro roda em memória (não há servidor próprio). Não existem, no seu acervo, anuladas/desatualizadas, ano, instituição, cargo, nível de escolaridade ou "com comentários" — esses filtros não foram criados. A barra antiga (`treinoMontarBarHTML`, `treinoFiltro*`) continua no código, sem uso na tela.

### Banca, ano e prova em cada questão
Campos opcionais da questão (`db.acervo`): `banca`, `ano` (número de 4 dígitos), `prova`, `orgao`, `cargo`. Questões antigas seguem sem eles. Aparecem numa linha pequena no Treinar (`banca · ano · prova`; vazio não mostra). O importador (colar JSON/prova) e o editor do Acervo aceitam e gravam esses campos; ao fundir uma questão repetida, o que estava vazio é preenchido (nunca sobrescreve). Filtros do Treino: **Banca** (as que existem + "Sem banca") e **Ano** (+ "Sem ano"). Migração (`acervoMigrarOrigem`, roda uma vez depois que o acervo carrega e pelo botão "Preencher pelo texto da fonte"): só preenche quando a `fonte` diz a banca (Cebraspe/Cespe, FGV, IDECAN, AOCP, IBFC, Vunesp, FCC, Quadrix, Consulplan, Instituto Access, IADES); "estilo Cebraspe" vira **"Cebraspe (estilo)"**; o ano só entra se aparecer junto da banca; nada é sobrescrito nem chutado. Grava com `acervoSalvar(true)`. O padrão "Cebraspe (estilo) para todas" da versão anterior foi **substituído** por "Sem banca".

### Questões inéditas (Treinar → 🧪 Questões inéditas)
Cartão dentro de Treinar: **1)** escolhe Mundo › Chefe › minibosses (ou todos do chefe), formato (Certo/Errado ou Múltipla) e quantidade (1–60); **2)** estilo/banca (Cebraspe, FGV, IDECAN, AOCP… ou outra), ano e prova (só para prova real); **3)** "Copiar prompt" gera o texto para a IA externa (lista fechada numerada dos minibosses, regras de nível/situação/fonte, o que você já tem em cada miniboss para não repetir, instruções de procedência e o formato JSON exato); **4)** cola a resposta e "Importar questões". O import liga cada item ao miniboss pelo nome (`assuntoNome`), cai no número do prompt quando não há nome e, se o nome não existe, deixa pendente para você escolher o assunto. Procedência: o que a IA preencher vale; senão entra `banca = "<Banca> (estilo)"` (ou a banca real, se marcado "prova real"), e ano/prova só se informados. Resposta cortada aproveita o que está inteiro; até 500 itens e 2 MB por importação; gabarito que não bate é descartado; repetida só preenche o que faltava. O relatório fecha a conta (lidas = novas + já existentes + aguardando assunto + descartadas) e há "Treinar com as novas". Grava com `acervoSalvar(true)`.
**Assunto digitado (Questões inéditas):** o campo "Ou digite o assunto" (um por linha) manda sobre as listas: o prompt usa o nome **exatamente como escrito** e pede à IA para não renomear nem escolher outro. O app diz, linha a linha, se o nome já existe como miniboss (e mostra qual) ou se vai ficar pendente. Ao importar, o nome digitado vale (o mapa do prompt); nome que não existe como miniboss fica pendente para você escolher o assunto.

### Peso do app: banco comprimido e carregamento adiado
- **Banco de questões comprimido.** `db.acervo` agora vai para a nuvem e para o aparelho comprimido (gzip em base64, em pedaços de até 600 mil caracteres) no nó **`vdn_acervoz`** (`{v,ts,n,chars,z,parts}`). A versão é um carimbo (`ts`): se a cópia local tem o mesmo carimbo, não baixa nada. O nó antigo **`vdn_acervo` não é tocado** (fica como cópia de segurança e para versões antigas do app). Se o navegador não suporta compressão, o pacote não abre, a contagem (`n`) não bate ou o pacote vem vazio, o app volta para o nó antigo. A primeira abertura migra sozinha — só se leu o banco de algum lugar (falha de rede não grava pacote vazio).
- **Gravação em fila e protegida.** As gravações passam por uma fila (uma de cada vez, sempre com o estado mais novo da memória) e **nada grava antes do banco carregar** (o pedido fica marcado e grava depois, com tudo junto). Ao esconder a aba, grava o que estava marcado.
- **Carregamento adiado.** O banco carrega quando o navegador está livre (no máximo 2,5 s depois da primeira tela) ou na hora, se você abrir Treinar, Provas, Acervo, Dicas, Flashcards, Revisões ou Editais antes disso (mostra "Carregando seu banco de questões…" e abre em seguida).
- Limitação: um aparelho com versão antiga do app que gravar no nó antigo depois da migração não é visto pelos aparelhos novos (a versão nova passa a ler só o pacote).

### Agenda desligada e Plano de assunto
- **Agenda desligada** (junto com Sala e Redação, em `RECURSOS_DESLIGADOS`): some do menu, `showScreen('agenda')` volta ao Painel, o card da agenda some do Painel e `renderWeeklyPlan` não monta mais nada (cronograma, grade e plano por edital não são calculados). **Nada foi apagado**: `db.cronograma`, `db.agendaPlanos`, `db.weeklyPlan`, blocos e pinos continuam guardados. Para religar: tirar `'agenda'` da lista ou abrir o app com `?ligar=agenda`.
- **Plano de assunto** (menu HOJE → ✅ Plano de assunto; no celular fica em "Mais"): lista Mundo › Chefe › assuntos (minibosses), cada um com uma caixinha "já estudei". Clicar marca (guarda a data, mostra dd/mm); clicar de novo desmarca. Por chefe: "Marcar todos" e "Limpar" (com confirmação). Resumo no topo (X de Y e %), por mundo, busca e "só os que faltam". É **só um registro**: não gera revisão, XP nem altera o Mapa. Guardado em `db.planoAssunto` (`{idDoAssunto: 'AAAA-MM-DD'}`); assuntos apagados do Mapa não contam.
