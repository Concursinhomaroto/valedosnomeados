import asyncio, sys, base64, io, os
sys.path.insert(0, '.')
from PIL import Image, ImageChops
from test_sala import async_playwright, setup_page, make_seed, real_errors

REPO='/home/user/DerrubaFGV/icons/sala-mapa/'

async def main():
    async with async_playwright() as p:
        browser, page, errors = await setup_page(p, make_seed({'studyNickname':'Reitor','studyCharacter':'ash'}))
        try:
            await page.evaluate("() => showScreen('mapaeditor')")
            await page.wait_for_function("() => !!mapedMapa", timeout=20000)

            # helper: percorre o MESMO caminho do editor e do jogo (gid -> tileset
            # por faixa de firstgid -> quadro = gid-firstgid) e devolve o recorte.
            await page.evaluate("""() => {
              window.__provaPeca = (nome,k) => {
                const t=SALA_TS_BY_NAME[nome], gid=t.f+k;
                const t2=mapedTilesetPorGid(gid);
                if(!t2) return {erro:'gid '+gid+' não caiu em folha nenhuma'};
                const im=mapedImg(t2);
                if(!im.complete||!im.naturalWidth) return {erro:'imagem não carregou'};
                const k2=gid-t2.f, cv=document.createElement('canvas');
                cv.width=t2.w; cv.height=t2.h;
                const ctx=cv.getContext('2d'); ctx.imageSmoothingEnabled=false;
                ctx.drawImage(im,(k2%t2.c)*t2.w,Math.floor(k2/t2.c)*t2.h,t2.w,t2.h,0,0,t2.w,t2.h);
                return {ts:t2.n,k:k2,w:t2.w,h:t2.h,png:cv.toDataURL()};
              };
              window.__carrega = () => Promise.all(SALA_TILESETS.map(t=>new Promise(res=>{
                const im=mapedImg(t);
                if(im.complete&&im.naturalWidth)return res(t.n);
                im.addEventListener('load',()=>res(t.n),{once:true});
                im.addEventListener('error',()=>res(null),{once:true});
              })));
            }""")
            carregadas = await page.evaluate("() => window.__carrega()", )
            faltando = [t for t in carregadas if t is None]
            assert not faltando, f'{len(faltando)} folhas não carregaram'
            print(f'{len(carregadas)} folhas carregaram no editor')

            cat = await page.evaluate("() => SALA_TILESETS.map(t=>({n:t.n,i:t.i,c:t.c,t:t.t,w:t.w,h:t.h}))")
            ruins=[]
            for t in cat:
                src = Image.open(REPO + t['i']).convert('RGBA')
                # 3 amostras por folha: primeiro, meio e último tile
                for k in (0, t['t']//2, t['t']-1):
                    r = await page.evaluate("([n,k]) => window.__provaPeca(n,k)", [t['n'], k])
                    if r.get('erro'): ruins.append((t['n'],k,r['erro'])); continue
                    if r['ts'] != t['n']:
                        ruins.append((t['n'],k,f"gid caiu na folha errada: {r['ts']}")); continue
                    got = Image.open(io.BytesIO(base64.b64decode(r['png'].split(',',1)[1]))).convert('RGBA')
                    col,row = k % t['c'], k // t['c']
                    box = (col*t['w'], row*t['h'], col*t['w']+t['w'], row*t['h']+t['h'])
                    if box[2] > src.width or box[3] > src.height:
                        ruins.append((t['n'],k,f'tile {k} cai fora do PNG {src.size}')); continue
                    esperado = src.crop(box)
                    if ImageChops.difference(got, esperado).getbbox() is not None:
                        ruins.append((t['n'],k,'pixels diferentes do PNG de origem'))
            if ruins:
                print(f'\n{len(ruins)} PROBLEMAS:')
                for n,k,msg in ruins[:20]: print(f'  ✗ {n} tile {k}: {msg}')
            assert not ruins, f'{len(ruins)} amostras saíram desconfiguradas'
            print(f'✓ {len(cat)} folhas x 3 amostras = {len(cat)*3} peças, todas pixel-idênticas ao PNG')

            # --- lado do jogo: o Phaser tem que gerar o mesmo número de quadros ---
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_function("""() => {const g=salaMapaGame;
                return !!(g&&g.scene.keys['salaMapaScene']&&g.scene.keys['salaMapaScene'].player);}""", timeout=25000)
            quadros = await page.evaluate("""() => {
                const s=salaMapaGame.scene.keys['salaMapaScene'],out=[];
                SALA_TILESETS.forEach(t=>{
                  if(!s.textures.exists(t.key))return;         // folha não usada por este mapa
                  const tex=s.textures.get(t.key);
                  out.push({n:t.n, esperado:t.t, veio:tex.frameTotal-1});  // -1 = quadro __BASE
                });
                return out;
            }""")
            erradas=[q for q in quadros if q['veio']!=q['esperado']]
            print(f'folhas carregadas pelo jogo: {len(quadros)}')
            for q in erradas: print(f"  ✗ {q['n']}: o Phaser fatiou {q['veio']} quadros, o catálogo diz {q['esperado']}")
            assert not erradas, 'folha fatiada errada pelo Phaser (tamanho de tile no catálogo != PNG)'
            print('✓ todas as folhas usadas foram fatiadas pelo Phaser exatamente como o catálogo declara')

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK — nenhuma folha do módulo sai desconfigurada')
        finally:
            await browser.close()

asyncio.run(main())
