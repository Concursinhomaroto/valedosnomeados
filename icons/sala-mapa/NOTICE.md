# Origem dos assets desta pasta

Os tilesets, itens e os personagens originais (`character/adam.png`, `ash.png`,
`lucy.png`, `nancy.png`, e os retratos `portraits/Adam_login.png`, `Ash_login.png`,
`Lucy_login.png`, `Nancy_login.png`) vêm do repositório
[kevinshen56714/SkyOffice](https://github.com/kevinshen56714/SkyOffice), licença MIT
(ver `LICENSE` do repositório original — cobre código e assets, sem ressalva separada
pra imagens).

O `map.json` foi refeito a partir do mapa original do SkyOffice, transformando o
escritório numa biblioteca/sala de estudo (salão de leitura + sala silenciosa), mantendo
o lado esquerdo do mapa (copa, recepção, sala de reunião) como estava.

**Variações de tom de pele** (`character/*_media.png`, `*_morena.png`, `*_retinta.png` e
os retratos correspondentes) são derivadas dos 4 spritesheets originais acima por troca
de paleta (HSV, preservando sombreado — cabelo/roupa/silhueta idênticos, só a pele muda),
geradas pelo pacote que o usuário enviou (`ferramentas/recolor.py` do pacote
"sala-de-estudo-personagens"). Mesma licença herdada da arte-fonte (MIT, SkyOffice).

Usados no Vale dos Nomeados só pra renderizar o mapa da Sala de Estudo (Phaser 3,
client-side) — sem nenhum código do SkyOffice em si (servidor Colyseus, React, Redux
etc.), só os arquivos de imagem/mapa.
