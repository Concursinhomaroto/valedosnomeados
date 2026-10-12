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
