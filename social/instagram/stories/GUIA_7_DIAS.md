# Guia — 7 dias de Stories prontos

## Arquivos (nessa ordem, um por dia)
1. `dia1-hook-esquece-tudo.png` — gancho/dor, sem print do app
2. `dia2-feature-mapa.png` — Mapa de Reinos
3. `dia3-feature-revisao.png` — Revisão Espaçada (SM-2)
4. `dia4-diferencial-tudo-em-um.png` — "tudo num só lugar" (a frase da mensagem, mas sem afirmar "primeiro app" — ver nota abaixo)
5. `dia5-feature-flashcards-ia.png` — flashcards gerados por IA a partir de PDF
6. `dia6-feature-gamificacao.png` — streak/XP/conquistas
7. `dia7-cta-final.png` — chamada final pro cadastro

## Duas formas de postar — escolha uma por story

### Opção A — manual pelo app (mantém o link clicável)
O Instagram **não deixa** colocar link clicável na imagem em si — o "sticker de
link" só dá pra adicionar na hora que você posta, direto no app:

1. Abra o Instagram → Criar story → escolha a imagem (`dia1-...png`, etc.)
2. Toque no ícone de **sticker** (quadradinho de carinha) no topo
3. Procure **"Link"** → cole `https://valedosnomeados.com.br/quiz.html`
4. Arraste o sticker pra perto da seta "⬆️ Arrasta pra cima" que já tá desenhada
   na imagem, pra ficar visualmente alinhado
5. Publica

### Opção B — automático pela fila (`admin-stories.html`), sem link clicável
Agora existe uma fila separada de Stories no mesmo Worker (`vdn-instagram`),
publicada sozinha nos mesmos 3 horários do dia configurados no Cron Trigger.
Pra usar: abra `admin-stories.html`, adiciona a URL da imagem, clica em
**"Aprovar"** — no próximo horário do Cron, ela publica sozinha.

**Troca que você faz ao escolher essa opção**: publica sem precisar tocar em
nada, mas o Instagram **não permite** adicionar o sticker de link por API —
então esse story sai sem o "arrasta pra cima" clicável. Pra esses 7 primeiros
(feitos pra converter gente pro quiz), a Opção A vale mais a pena. Pra stories
futuros mais "de presença" (sem CTA direto), a automação é mais prática.

## Sugestão de sticker extra (opcional, mas ajuda MUITO a engajar)
Nos dias 1, 4 e 6, dá pra adicionar em cima da imagem um sticker de
**enquete** ou **caixinha de pergunta** nativo do Instagram, tipo:
- Dia 1: enquete "Você também esquece tudo depois de 1 semana? 😵 Sim / Não"
- Dia 4: enquete "Como você estuda hoje? 📓 Caderno / 📱 App"
- Dia 6: caixinha de pergunta "Qual sua maior dificuldade pra estudar?"

Isso não dá pra automatizar (só existe dentro do app), mas é o que mais gera
gente clicando em seguir depois — vale o minuto extra.

## Cadência sugerida
Poste 1 story novo por dia (dessa lista) e deixa ele salvo nos **Destaques**
depois das 24h, categoria "Como funciona" — assim quem chega no perfil depois
ainda vê tudo isso.

## Sobre a frase "primeiro aplicativo que tem tudo em um só lugar"
Ajustei pra não afirmar "primeiro" como fato (não temos como provar isso, e
concorrentes com features parecidas existem). O Dia 4 comunica o mesmo
benefício de um jeito que dá pra defender 100%: "tudo num só lugar" é
literalmente o que o app faz, sem prometer ineditismo.
