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

⚠️ **Pendência real, não resolvida por este aviso**: os termos exatos de uso da
LimeZu para o pacote pago (Modern Interiors) — em particular se hospedar essas
imagens num site público conta como "redistribuir" o asset — não foram confirmados
com uma fonte primária (comprovante de compra/licença). Decisão registrada em
2026-09-02: manter os assets publicados por ora; revisitar se surgir confirmação
em qualquer direção.
