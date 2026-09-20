# Vale dos Nomeados — Análise da arquitetura atual e plano de refatoração

> Documento vivo. Atualizar ao final de cada fase com o que foi feito e o que mudou de escopo.

## 0. Status atual

- ✅ **Fase 0** — sincronização das correções + bug de `EIXOS_DEFAULT` (travava o loading quando o Firebase/CDN falha) corrigido.
- ✅ **Fase 1** — design tokens, responsivo mobile real (bottom nav, corrigido bug de texto vazando dos botões de navegação), modo claro/escuro persistido, skeleton loading + animações de entrada. Testado em 375px/1440px, claro/escuro, nas 7 telas principais.
- 🔶 **Fase 2** — parcial (2a feita). Tratamento de erros amigável — toasts para perda de conexão com o Firebase após o carregamento inicial, falha ao salvar (`saveDB`) e erros JS não tratados, com debounce contra spam. **Decisão de escopo**: a modularização ES6 completa prevista originalmente na Fase 2 foi adiada — é uma mudança de alto risco (165 funções globais entrelaçadas, 137 `onclick` inline) sem rede de testes automatizados, então não compensa arriscar sem necessidade concreta. Valor entregue prioriza o que reduz risco real ao usuário (perda silenciosa de dados) sobre reorganização interna do código.
- ✅ **Fase 3** — completa. Streak de dias consecutivos (🔥), meta diária com anel de progresso, 6 conquistas, notificações locais de revisões atrasadas (Web Notifications API, com botão de opt-in e limite de 1 aviso/dia), exportar CSV do histórico de estudos, e busca global (assuntos, flashcards, temas de repertório, redações) com debounce, acessível pela sidebar.
- ✅ **Fase 4** — completa. Ícones em 5 resoluções (192/512/512-maskable/180-apple/32-favicon), `manifest.json`, `sw.js` (service worker cache-first pro shell estático, nunca intercepta o Firebase — que usa WebSocket, fora do alcance do `fetch` de qualquer forma). Testado: registro do SW, cache do shell, e recarregamento 100% offline funcionando.
- ✅ **Fase 5** — completa. Exportar/importar decks de flashcards em JSON (por chefão); modo foco Pomodoro integrado ao cronômetro flutuante (ciclos 25/5min, pausa longa a cada 4, registra tempo de estudo real igual ao cronômetro livre); analytics avançado no Painel do Herói (taxa de acerto de flashcards ao longo do tempo + tempo médio por assunto por reino); exportar PDF do histórico via janela de impressão isolada (sem lib externa, mantendo o app livre de dependências extras).
- ⬜ Fase 6 — não iniciada (SaaS multiusuário — maior risco, precisa de decisão explícita antes de começar, ver seção da Fase 6 abaixo).

## 6. Nota técnica: bug real encontrado e corrigido na Fase 5
Ao implementar o export de PDF, um `</script>` literal dentro de uma string JS (usado pra montar o HTML da janela de impressão) quebrou o parser de HTML da página inteira — o navegador encerra a tag `<script>` no primeiro `</script>` que encontra no código-fonte, mesmo dentro de uma string, então isso derrubava a aplicação inteira ao carregar. Corrigido escapando pra `<\/script>`. Fica registrado aqui como lição: qualquer HTML gerado dinamicamente que inclua a palavra "script" precisa desse cuidado.

## 5. Novos arquivos desta fase
- `manifest.json` — metadados de instalação (nome, ícones, cores, display standalone)
- `sw.js` — service worker
- `icons/icon-192.png`, `icons/icon-512.png`, `icons/icon-512-maskable.png`, `icons/apple-touch-icon.png`, `icons/favicon-32.png`
- Ao subir manualmente pelo GitHub: arraste a **pasta** `icons` inteira (não os arquivos soltos) pro upload, senão os caminhos relativos (`icons/icon-192.png` etc.) quebram.

## 1. Mapeamento do estado atual

Arquivo único `index.html`, 4.493 linhas / ~240KB, sem build step.

**Cabeça do arquivo**
- `<style>` único, linhas 8–731 (724 linhas de CSS). Um segundo `<style>` residual de 2 linhas (só a keyframe `dot` do loading) na linha 1064 — resquício de edição, deveria estar no bloco principal.
- Só **18 custom properties** em `:root` (cores, sombras). Não há tokens de espaçamento, radius, tipografia ou breakpoints — cada componente define esses valores manualmente inline.
- **486 atributos `style="..."` inline** e **137 `onclick="..."` inline** espalhados pelo HTML/JS (template strings). Não há delegação de eventos centralizada além de `bindStaticEvents` (linha 4380), que cobre só uma fração dos casos.
- Apenas **5 media queries** no arquivo inteiro, quase todas específicas de um componente (`#kingdoms-container`, etc.) — não existe um sistema de breakpoints. O layout principal é `#sidebar` (220px fixo) + `#main-content`, sem colapso para mobile.

**Dados e backend**
- Firebase SDK **compat** 10.12.0 (app + database), carregado via CDN, sem Auth.
- Config do Firebase (incluindo `apiKey`) está hardcoded no cliente — isso é normal para apps Firebase (a chave não é secreta), mas o preocupante é que **toda a base é um único documento** `DB_REF = firebaseDB.ref('vdn_v1')` sem nenhum usuário/UID — ou seja, hoje é single-tenant "de fato": todo mundo que abre a página lê/escreve o mesmo nó, protegido só pelas regras do Realtime Database (que precisamos inspecionar no console do Firebase, não estão neste arquivo). Isso é o bloqueio nº1 para multiusuário/SaaS.
- Fallback para `localStorage` (`vdn_local_v1`) se o Firebase falhar — bom para resiliência offline, mas hoje é só leitura/escrita local sem sincronização quando a conexão volta.
- Estado global: um objeto `db` (linha 1188) com `kingdoms, topics, times, revisions, xp, examDate, sessions, editais, weeklyPlan, flashcards, redacoes, repertorio, ...` — mutado diretamente por ~150 funções soltas no escopo global (nenhum módulo, nenhum encapsulamento).
- `saveDB()` faz debounce de 800ms e grava o objeto inteiro (`.set()`) a cada mudança — funciona, mas não escala bem (qualquer edição reescreve toda a árvore) e não há resolução de conflito entre abas/dispositivos.

**Telas (`.screen`)**: `screen-map`, `screen-kingdom`, `screen-revisions`, `screen-dashboard`, `screen-editais`, `screen-flashcards`, `screen-redacoes`, `screen-repertorio` — trocadas via `showScreen()` (display none/flex), sem router, sem URL/histórico (não dá pra linkar direto pra uma tela).

**JavaScript**: ~165 funções `function nome(...)` no escopo global, um único `<script>` de ~3.370 linhas (1118–4489). Nomeação por prefixo indica módulos "mentais" já existentes (não formalizados): `fc*` (flashcards), `rd*` (redações), `rep*` (repertório), `ft*` (float timer) — isso ajuda bastante na hora de separar em módulos ES6 reais.

**Achado à parte — divergência de versão**: o arquivo que você anexou tem correções que o `index.html` do repositório (branch atual) **não tem** — principalmente uma limpeza de revisões inválidas em `applyDefaults()` e a geração correta das 4 revisões (7/14/30/45 dias) em vez de só 1, além de pequenos ajustes de `white-space`/`word-break` em flashcards. Isso indica que o arquivo enviado é mais novo que o que está commitado.

## 2. Riscos e dívidas técnicas priorizados

| # | Achado | Risco | Prioridade |
|---|---|---|---|
| 1 | Sem Auth + 1 nó de dados compartilhado no Realtime DB | Qualquer pessoa com a URL lê/escreve os dados de todo mundo | Crítico, bloqueia Fase 6 (SaaS) |
| 2 | Zero sistema de responsividade real | App provavelmente quebra/é inutilizável abaixo de 768px | Alto, é o pedido nº1 do usuário |
| 3 | CSS sem tokens, 486 inline styles | Qualquer mudança visual exige caçar estilos espalhados | Alto, bloqueia design system |
| 4 | Tudo em escopo global, 1 arquivo de 240KB | Risco alto de regressão a cada mudança, sem isolamento de módulos | Médio-alto |
| 5 | `saveDB()` reescreve a árvore inteira a cada save | Não escala, risco de perda de dados em edição concorrente (2 abas) | Médio |
| 6 | Sem testes automatizados, só manuais | Toda mudança precisa de checklist manual disciplinado | Médio (mitigável com checklist) |
| 7 | Divergência entre arquivo enviado e repo | Se eu partir do repo, perco correções já feitas manualmente | Precisa decisão antes de codar |

## 3. Plano de execução por fases

Ordem conforme priorização pedida: **mobile responsivo → design system → novas features → PWA → SaaS**. Cada fase é entregável e testável isoladamente; nenhuma reescreve o arquivo inteiro de uma vez.

### Fase 0 — Baseline e sincronização (housekeeping)
- Sincronizar `index.html` do repo com as correções do arquivo enviado (revisões 7/14/30/45, limpeza de dados inválidos, `word-break`).
- Montar checklist de teste manual por módulo (o que verificar em cada tela após uma mudança).
- Servidor estático local para testar (não dá pra abrir `file://` por causa do Firebase/CORS em alguns navegadores).
- **Impacto:** baixo/invisível ao usuário, mas remove um bug ativo de corrupção de dados e cria a rede de segurança para todo o resto.
- **Esforço:** XS (< 1h). **Risco:** baixo.

### Fase 1 — Mobile responsivo + Design System (tokens)
- Expandir `:root` com tokens reais: escala de espaçamento (grid de 8px), escala tipográfica fluida (`clamp()`), radius, elevação/shadow, breakpoints nomeados.
- Sidebar fixa de 220px → colapsa para navegação inferior (bottom nav) ou drawer em ≤768px; grids de reinos/flashcards/dashboard viram 1 coluna em mobile.
- Extrair os `style=""` inline mais repetidos (cards, badges, pills) para classes utilitárias/componentes, sem alterar a lógica JS que os gera.
- Dark/light mode com toggle + persistência em `localStorage` (a paleta já é HSL/hex organizada o suficiente pra inverter com uma segunda tabela de tokens).
- Skeleton screens no lugar do spinner do `#loading-overlay`.
- Animações leves de entrada (fade/slide) via classes CSS, sem JS extra.
- **Impacto:** altíssimo — é visual, é o que o usuário vê primeiro, e é pré-requisito de usabilidade para vender o produto.
- **Esforço:** M/L. **Risco:** médio (toca CSS global; testar as 8 telas em 375px e 1440px depois de cada mudança).

### Fase 2 — Qualidade de código (sem quebrar comportamento)
- Formalizar os módulos que já existem "de fato" (`fc*`, `rd*`, `rep*`, `ft*`, core) em `<script type="module">` com import maps — mantém GitHub Pages estático, sem bundler.
- Introduzir um store fino sobre `db` (get/set com notificação de listeners), mantendo o mesmo formato de dados gravado no Firebase — migração invisível para o usuário.
- Padronizar tratamento de erros (toast amigável em vez de `console.warn` silencioso nos `catch`).
- Ampliar `bindStaticEvents` para cobrir os 137 `onclick` inline restantes.
- **Impacto:** baixo/invisível para o usuário final, mas reduz drasticamente o custo das fases seguintes.
- **Esforço:** L. **Risco:** médio-alto — exige rodar o checklist completo da Fase 0 após cada módulo migrado.

### Fase 3 — Features novas de maior valor percebido
- Meta diária de horas com anel de progresso (reaproveita dados que já existem em `times`/`lifetimeSeconds`).
- Streak de dias consecutivos com 🔥 e marcos.
- Conquistas/badges (primeiro estudo, 7 dias seguidos, 100 flashcards revisados etc.).
- Busca global client-side (os dados já estão todos em memória em `db`).
- Notificações locais (Web Notifications API) para revisões atrasadas.
- Exportar CSV do histórico (mais simples e sem dependência nova; PDF fica pra Fase 5).
- **Impacto:** alto (engajamento/retenção), cada item é independente e paralelizável.
- **Esforço:** M por item.

### Fase 4 — PWA básico
- `manifest.json` + ícones em múltiplas resoluções + splash.
- Service Worker cache-first só para o shell estático (HTML/CSS/JS/ícones), **nunca** interceptando chamadas ao Firebase.
- **Impacto:** médio-alto para instalação/retenção mobile e percepção de produto "pronto pra vender".
- **Esforço:** M. **Risco:** baixo se o SW não tocar em dados dinâmicos.

### Fase 5 — Features "Pro"
- Dashboard de analytics avançado (taxa de acerto de flashcards ao longo do tempo, tempo médio por assunto).
- Exportar PDF.
- Modo foco (Pomodoro) integrado ao cronômetro flutuante existente.
- Exportar/importar decks de flashcards por chefão em JSON.
- **Impacto:** médio, mas é o que diferencia o plano Pro.
- **Esforço:** M/L.

### Fase 6 — SaaS multiusuário (maior risco e esforço)
- Firebase Auth (email/senha + Google).
- Migrar de `ref('vdn_v1')` único para `ref('users/{uid}')`, com regras de segurança do Realtime DB por usuário — **isso exige atenção especial**: é mudança de infraestrutura em produção, com dados reais existentes.
- Script de migração one-time: copiar o nó `vdn_v1` atual para o UID do usuário admin, sem perda de dados.
- Planos Free/Pro (gates de limite), onboarding guiado, landing page, painel admin de métricas.
- **Impacto:** altíssimo para o modelo de negócio, mas é a fase mais arriscada tecnicamente — não deve começar sem confirmação explícita, dado que envolve regras de segurança e dados reais de produção.
- **Esforço:** XL (dias, não horas).

## 4. Como cada fase será validada
Checklist manual por tela (mapa, chefão, revisões, dashboard, editais, flashcards em 3 modos, redações com cálculo NPD, repertório) em 375px e 1440px, em Chrome e Firefox, antes e depois de cada fase — documentado neste arquivo conforme evolui.
