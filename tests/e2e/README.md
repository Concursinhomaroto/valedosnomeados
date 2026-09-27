# Suíte de testes end-to-end

Testes de comportamento contra `app/index.html` de verdade, rodando num Chromium
headless via Playwright. Não é unitário — cada teste sobe o app inteiro numa página,
com o SDK do Firebase substituído por um mock em memória (`test_sala.py`), e confere o
resultado lendo `db`, o DOM renderizado e as chamadas gravadas ao "Firebase" mockado.
Nenhum teste toca rede real, Firebase real ou uma chave de API real.

## Por que não é só manual

Cada mudança em `app/index.html` — um arquivo único de ~26 mil linhas, sem build step —
é testada rodando (ou escrevendo, quando o comportamento é novo) um destes scripts contra
uma cópia local do arquivo, antes de qualquer commit. Até agora essa suíte vivia só no
scratchpad de sessões do Claude Code, nunca commitada — o que a tornava real, mas não
reproduzível por ninguém além daquela sessão. Isso mudou: a partir de agora ela mora aqui,
e cresce por PR normal, junto com o código que testa.

## Pré-requisitos

- Python 3 com `playwright` instalado (`pip install playwright`) — os binários do
  Chromium não precisam ser baixados de novo se já existir uma instalação em
  `/opt/pw-browsers/chromium` (é o caminho que os testes usam); senão, rode
  `playwright install chromium`.
- Nenhuma dependência de rede: `phaser.min.js` (usado pela Sala de Estudo) está
  vendorizado em `fixtures/`, e os testes interceptam o pedido ao cdnjs pra servir essa
  cópia local em vez de baixar.

## Como rodar

```bash
# na raiz do repo, um servidor HTTP simples servindo o app
python3 -m http.server 8934 &

# cada teste é um script standalone
cd tests/e2e
python3 test_dedup_forte.py
python3 test_acervo.py
# ...e assim por diante — não há um único runner, cada arquivo roda com asyncio.run(main())
# e termina com "OK" (e código de saída 0) ou um AssertionError explicando o que falhou.
```

Rodar todos de uma vez:

```bash
cd tests/e2e
for f in test_*.py; do echo "=== $f ==="; python3 "$f" || echo "FALHOU: $f"; done
```

## Estrutura

- `test_sala.py` — o harness compartilhado: `setup_page()` sobe o Chromium, injeta o mock
  do Firebase (`window.__root` como "banco de dados", com `on`/`set`/`update`/`once`
  compatíveis com a API do SDK) e carrega `app/index.html` do servidor local.
  `make_seed()` monta um `db` inicial mínimo (reino, tópico, miniboss) que cada teste
  estende conforme precisa.
- `test_<algo>.py` — um cenário de comportamento por arquivo. Muitos importam `seed()` e
  fábricas de fixture de outros arquivos de teste já existentes (ex.: `test_acervo.py`
  exporta `seed`/`QS` reaproveitados por vários testes do Banco de Questões) em vez de
  duplicar setup.
- `fixtures/` — arquivos binários/grandes que os testes precisam (hoje, só o Phaser
  vendorizado).
- `*.json` na raiz — fixtures de dados pequenas (ex.: `fixture_caderno.json`, o texto de
  um caderno real da banca usado por `test_caderno.py`).
- `_out/` (gerada, ignorada pelo git) — screenshots que alguns testes tiram pra conferência
  visual manual; não fazem parte da asserção.

## Um teste conhecido, instável

`test_painel.py` falha esporadicamente numa contagem de revisões atrasadas — ela depende
do relógio do container bater com `todayStr()`, e o container às vezes fica um dia
atrasado. Confirmado várias vezes como falha pré-existente, não ligada a nenhuma mudança
de funcionalidade. Se ele falhar sozinho, rode de novo antes de investigar.
