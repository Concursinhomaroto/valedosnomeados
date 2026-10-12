# Pacotes de dicas

Arquivos JSON prontos para a aba **Treinar → Dicas → Importar em lote** (cole o conteúdo
ou use "Escolher arquivo .json").

| Arquivo | Conteúdo |
|---|---|
| `portugues-25-pontos.json` | 25 dicas de Português em 5 grupos: Classes e pronomes (6), Regência e preposições (6), Verbos e concordância (6), Colocação pronominal (3), Ortografia e sentido (4). Texto e exemplos originais; `origem: "ia"`, porque foram escritos por IA e merecem revisão. |

## Formato

Um array JSON. Cada item:

| Campo | Para quê |
|---|---|
| `tipo` | `"dica"` (padrão), `"numero"` ou `"par"` |
| `materia` | nome do reino; casa pelo nome (sem acento/caixa). Obrigatório |
| `assunto` | nome do miniboss; casa por `simCasarAssunto` dentro da matéria. Se não casar, a dica entra só com a matéria e aparece em "sem assunto" |
| `grupo` | texto livre; as dicas são agrupadas por ele na tela |
| `titulo` | curto. Matéria + título normalizado é o que identifica duplicata |
| `regra`, `aplicar`, `cuidado` | as três linhas do cartão (tipo `dica`) |
| `exemplos` | `[{ "txt": "...", "ok": true }]` — `ok: false` marca o exemplo errado |
| `valor`, `rotulo` | tipo `numero` (ex.: `"+2 a +8 °C"`, `"Rede de frio, instância local"`) |
| `a`, `b`, `diferenca` | tipo `par` (ex.: mau × mal) |
| `bancas` | lista de etiquetas, ex.: `["IGEDUC"]` |
| `origem` | `"minha"`, `"material"` (padrão na importação), `"erro"` ou `"ia"` |
| `fonte` | norma ou material de onde saiu |

Nada é descartado em silêncio: o relatório da importação diz quantas entraram (com e sem
assunto), quantas foram recusadas e por quê, quais foram ligadas por nome parecido (não
igual) e quais esperam você escolher a matéria.

## Pacotes publicados (dentro do app)

Em **Dicas → Pacotes**, o admin publica as dicas do filtro em uso (busca, matéria, grupo,
banca, assunto; rascunhos ficam de fora) para todos os assinantes. O pacote vai para o nó
`dicas_pacotes` do Firebase — lê quem está logado, grava só o admin, a mesma regra do
`sala_mapa` — no mesmo formato acima (matéria e assunto por nome).

Quem adiciona recebe as dicas pelo mesmo caminho da importação em lote. Numa versão nova
do pacote ("Atualizar para a vN"): a dica que a pessoa não mexeu é trocada; a que ela
editou fica como ela deixou; a que ela apagou não volta; o "já sei" e o assunto que ela
ligou continuam. O relatório conta cada caso.

Requer a regra `dicas_pacotes` do `firebase.rules.json` **publicada** no Firebase (console
→ Realtime Database → Regras, ou `firebase deploy --only database`). Sem ela, o painel
avisa que falta publicar as regras.
