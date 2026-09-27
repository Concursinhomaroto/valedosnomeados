import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p, make_seed({'studyNickname':'R','studyCharacter':'ash'}))
        await page.set_viewport_size({'width':1500,'height':950})
        try:
            page.on('dialog', lambda d: asyncio.ensure_future(d.accept('30')))
            await page.evaluate("() => showScreen('mapaeditor')")
            await page.wait_for_function("() => !!mapedMapa", timeout=20000)
            await page.evaluate("() => mapedNovo()")
            await page.wait_for_function("() => mapedMapa.width===30", timeout=8000)

            # entrar no modo Parede já liga o "ver colisão"
            await page.evaluate("""() => { document.getElementById('maped-vercol').checked=false;
                mapedSetMode('parede'); }""")
            assert await page.evaluate("()=>document.getElementById('maped-vercol').checked") is True, \
                'modo Parede devia ligar o "ver colisão"'
            assert await page.evaluate("()=>document.getElementById('maped-collide').checked") is True
            print('✓ modo Parede entra já mostrando a colisão')

            cv=page.locator('#maped-canvas'); box=await cv.bounding_box()
            def pt(tx,ty): return (box['x']+tx*32+16, box['y']+ty*32+16)

            # arrasta um retângulo 6x4 de (4,4) a (9,7)
            await page.mouse.move(*pt(4,4)); await page.mouse.down()
            await page.mouse.move(*pt(7,6), steps=4)
            gh=await page.evaluate("""()=>{const g=document.getElementById('maped-ghost');
                return {d:g.style.display,w:g.style.width,h:g.style.height,cor:g.style.borderColor};}""")
            print('prévia durante o arrasto:', gh)
            assert gh['d']=='block' and gh['w']=='128px' and gh['h']=='96px', gh
            await page.mouse.move(*pt(9,7), steps=4); await page.mouse.up()

            r=await page.evaluate("""()=>{
              const sol=mapedSolid().data,W=mapedMapa.width;
              let dentro=0,fora=0;
              for(let i=0;i<sol.length;i++){ if(!sol[i])continue;
                const x=i%W,y=(i/W)|0;
                if(x>=4&&x<=9&&y>=4&&y<=7)dentro++; else fora++; }
              return {dentro,fora,total:sol.filter(v=>v).length};
            }""")
            print('depois de soltar:', r)
            assert r['dentro']==24 and r['fora']==0, r
            print('✓ retângulo 6x4 = 24 tiles, nada fora')

            # desmarcando, o mesmo arrasto vira borracha
            await page.evaluate("()=>{document.getElementById('maped-collide').checked=false;}")
            await page.mouse.move(*pt(6,5)); await page.mouse.down()
            await page.mouse.move(*pt(9,7), steps=4); await page.mouse.up()
            r2=await page.evaluate("()=>mapedSolid().data.filter(v=>v).length")
            print('depois da borracha:', r2, 'tiles ainda bloqueados')
            assert r2==24-12, f'esperava 12 liberados, sobrou {r2}'
            print('✓ arrasto com a caixinha desmarcada libera a área')

            # borracha também solta o móvel que estiver na área
            solto=await page.evaluate("""()=>{
              mapedSelectTileset('Kitchen'); mapedSel={c:0,r:1,w:2,h:2};
              mapedSetMode('objeto'); document.getElementById('maped-collide').checked=true;
              mapedAplicar(20,20);
              const antes=mapedGradeSolida()[20*mapedMapa.width+20];
              mapedSetMode('parede'); document.getElementById('maped-collide').checked=false;
              // simula o arrasto de um tile só
              const sol=mapedSolid(); sol.data[20*mapedMapa.width+20]=0; mapedLiberarTile(20,20);
              return {antes, depois:mapedGradeSolida()[20*mapedMapa.width+20]};
            }""")
            print('móvel na área liberada:', solto)
            assert solto['antes']==1 and solto['depois']==0, solto
            print('✓ a borracha libera o móvel junto')

            # limpar tudo
            await page.evaluate("()=>mapedLimparColisao()")
            await page.wait_for_timeout(300)
            assert await page.evaluate("()=>mapedSolid().data.filter(v=>v).length")==0
            print('✓ "Limpar paredes" zera o desenho')

            print('\nErros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK — parede desenhada com arrasto em retângulo, com borracha e limpeza')
        finally:
            await browser.close()
asyncio.run(main())
