# Origem dos assets desta pasta

**Correção em relação à versão anterior deste aviso:** a arte (personagens, móveis,
tilesets) não é "do SkyOffice" — o SkyOffice (código) é MIT, mas a arte em si é do
pacote **Modern Interiors**, da artista **LimeZu** (https://limezu.itch.io/), só
*incluída* no repositório do SkyOffice com crédito (`readme.md` do SkyOffice: "Big
thanks to pixel artist - LimeZu"). A licença MIT do SkyOffice cobre o código-fonte
dele; não necessariamente os arquivos de imagem de terceiros que ele empacota. Créditos
correntes: **LimeZu — https://limezu.itch.io/**.

Arquivos vindos por esse caminho: `tileset/FloorAndGround.png`,
`Modern_Office_Black_Shadow.png`, `Generic.png`, `Basement.png`,
`Classroom_and_library.png`, `Conference_Hall.png`, `Kitchen.png`, `LivingRoom.png`;
`items/chair.png`, `computer.png`, `whiteboard.png`, `vendingmachine.png`;
`character/adam.png`, `ash.png`, `lucy.png`, `nancy.png` e os retratos
`portraits/Adam_login.png`, `Ash_login.png`, `Lucy_login.png`, `Nancy_login.png`.

**Variações de tom de pele** (`character/*_media.png`, `*_morena.png`, `*_retinta.png`
e os retratos correspondentes) são derivadas dos 4 spritesheets originais acima por
troca de paleta (HSV, preservando sombreado — cabelo/roupa/silhueta idênticos, só a
pele muda). Mesma origem/crédito da arte-fonte (LimeZu).

O `map.json` (planta v2, 60x44) foi construído do zero por código
(`ferramentas/build_map_v2.py`, fora deste repositório) usando as peças dos tilesets
acima — não é o mapa original do escritório do SkyOffice.

Usados no Vale dos Nomeados só pra renderizar o mapa da Sala de Estudo (Phaser 3,
client-side) — sem nenhum código do SkyOffice em si (servidor Colyseus, React, Redux
etc.), só os arquivos de imagem/mapa.

⚠️ **Atualização de 2026-09-02**: o usuário enviou o pacote completo
"Modern_Interiors_RPG_Maker_Version", que inclui `LICENSE.txt` (fonte primária, não
mais suposição):

```
MODERN INTERIORS FULL VERSION LICENSE
YOU CAN: Edit and use the asset in any commercial or non commercial project
YOU CAN'T: Resell or distribute the asset to others / Edit and resell the asset to others
Credits required
```

Isso confirma que "distribuir o asset" é proibido — e servir esses PNGs crus em URLs
públicas (como este site faz) é um candidato bem direto a se encaixar nessa proibição,
mesmo a arte estando "dentro" de um jogo. Decisão explícita do usuário, registrada aqui:
**manter os assets publicados mesmo assim** ("Segue mesmo assim — uso o pacote à
vontade..."). Crédito visível adicionado na tela da Sala de Estudo (rodapé, link pra
https://limezu.itch.io/) pra cumprir a exigência de "Credits required" — a única parte
do texto que dava pra atender sem tirar nada do ar.
