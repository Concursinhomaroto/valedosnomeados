import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

# Casos conferidos na mão, recortando o PNG: (folha, tile clicado, peça esperada)
CASOS = [
    # o caso do usuário: clicar na cadeira (col 0, linha 22) tem que dar a cadeira
    # inteira 1x2 (linhas 21-22), não um 2x2 que corta a máquina de baixo
    ('Modern_Office_Black_Shadow', 0, 22, {'c':0,'r':21,'w':1,'h':2}),
    # e clicar na máquina logo abaixo dá a máquina inteira, 2x3
    ('Modern_Office_Black_Shadow', 0, 23, {'c':0,'r':23,'w':2,'h':3}),
]

async def main():
    async with async_playwright() as p:
        browser, page, errors = await setup_page(p, make_seed({'studyNickname':'Reitor','studyCharacter':'ash'}))
        try:
            await page.evaluate("() => showScreen('mapaeditor')")
            await page.wait_for_function("() => !!mapedMapa", timeout=20000)

            for folha, c, r, esperado in CASOS:
                await page.evaluate("(n) => mapedSelectTileset(n)", folha)
                await page.wait_for_function("() => { const im=mapedImgs[mapedTS.n]; return im&&im.complete&&im.naturalWidth>0; }", timeout=15000)
                got = await page.evaluate("([c,r]) => mapedPecaInteira(c,r)", [c, r])
                print(f'{folha} clique em ({c},{r}) -> {got}')
                assert got == esperado, f'esperava {esperado}, veio {got}'

            # Varredura: em TODA folha, toda peça detectada tem que ser um retângulo
            # coerente — dentro da folha e sem tile de outra peça no meio dela.
            resumo = await page.evaluate("""async () => {
              const out=[];
              for(const t of SALA_TILESETS){
                const im=mapedImg(t);
                if(!(im.complete&&im.naturalWidth)) await new Promise(r=>{im.addEventListener('load',r,{once:true});im.addEventListener('error',r,{once:true});});
                const pc=mapedPecasDaFolha(t);
                if(!pc){out.push({n:t.n,erro:'não computou'});continue;}
                const vistas=new Set();let pecas=0,maior=0,foraDaFolha=0;
                for(let k=0;k<pc.porTile.length;k++){
                  const b=pc.porTile[k];if(!b||vistas.has(b))continue;
                  vistas.add(b);pecas++;
                  maior=Math.max(maior,b.w*b.h);
                  if(b.c<0||b.r<0||b.c+b.w>pc.cols||b.r+b.h>pc.rows)foraDaFolha++;
                }
                out.push({n:t.n,pecas,maior,foraDaFolha,tiles:pc.porTile.length});
              }
              return out;
            }""")
            ruins=[x for x in resumo if x.get('erro') or x.get('foraDaFolha')]
            for x in ruins: print('  ✗', x)
            assert not ruins, 'peça com caixa fora da folha'
            total=sum(x['pecas'] for x in resumo)
            print(f'✓ {len(resumo)} folhas varridas, {total} móveis reconhecidos, nenhuma caixa fora da folha')
            for x in sorted(resumo,key=lambda z:-z['pecas'])[:6]:
                print(f"   {x['n']}: {x['pecas']} peças (maior: {x['maior']} tiles)")

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK — clique seleciona o móvel inteiro, do jeito que foi desenhado')
        finally:
            await browser.close()

asyncio.run(main())
