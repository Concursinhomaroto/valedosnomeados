import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p, make_seed({'studyNickname':'Reitor','studyCharacter':'ash'}))
        try:
            avisos=[]
            def dialogo(d):
                avisos.append(d.message)
                asyncio.ensure_future(d.accept('40'))
            page.on('dialog', dialogo)

            await page.evaluate("() => showScreen('mapaeditor')")
            await page.wait_for_function("() => !!mapedMapa", timeout=20000)

            # ---- 1) o diagnóstico do editor tem que bater com o do JOGO ----
            # (se divergir, o editor mente e o usuário publica no escuro)
            await page.evaluate("() => mapedNovo()")
            await page.wait_for_function("() => mapedMapa.width===40", timeout=8000)
            await page.evaluate("""() => {
                mapedSelectTileset('Kitchen');
                mapedSel={c:0,r:1,w:3,h:2}; mapedSetMode('objeto');
                document.getElementById('maped-collide').checked=true;
                mapedSnapshot(); mapedAplicar(5,5); mapedAplicar(20,20);
                mapedSel={c:0,r:1,w:2,h:1};
                document.getElementById('maped-collide').checked=false;
                mapedAplicar(10,10);                       // esse NÃO deve barrar
                mapedSetMode('parede');
                document.getElementById('maped-collide').checked=true;
                mapedAplicar(30,30); mapedAplicar(30,31);
                mapedSetMode('spawn'); mapedAplicar(2,2);
            }""")
            editor = await page.evaluate("""() => {
                const s=mapedGradeSolida(),W=mapedMapa.width;
                const lista=[];for(let i=0;i<s.length;i++)if(s[i])lista.push((i%W)+','+((i/W)|0));
                return lista.sort();
            }""")
            print(f'editor diz: {len(editor)} tiles sólidos')

            await page.evaluate("() => mapedSalvar()")
            await page.wait_for_function("() => window.__updateCalls.some(c=>c.path==='sala_mapa/atual')", timeout=8000)
            await page.evaluate("() => { salaMapaJSON=null; }")
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_function("""() => {const g=salaMapaGame;
                return !!(g&&g.scene.keys['salaMapaScene']&&g.scene.keys['salaMapaScene'].player);}""", timeout=25000)
            jogo = await page.evaluate("""() => {
                const s=salaMapaGame.scene.keys['salaMapaScene'],lista=[];
                (s.walls?s.walls.getChildren():[]).forEach(r=>lista.push(((r.x-16)/32)+','+((r.y-16)/32)));
                (s.solids?s.solids.getChildren():[]).forEach(sp=>{
                  const x0=Math.round((sp.x-sp.displayWidth/2)/32), y0=Math.round((sp.y-sp.displayHeight/2)/32);
                  const cols=Math.max(1,Math.round(sp.displayWidth/32)), lins=Math.max(1,Math.round(sp.displayHeight/32));
                  for(let dy=0;dy<lins;dy++)for(let dx=0;dx<cols;dx++)lista.push((x0+dx)+','+(y0+dy));
                });
                return [...new Set(lista)].sort();
            }""")
            print(f'jogo diz:   {len(jogo)} tiles sólidos')
            so_editor=sorted(set(editor)-set(jogo)); so_jogo=sorted(set(jogo)-set(editor))
            if so_editor: print('  só no editor:', so_editor[:10])
            if so_jogo:   print('  só no jogo:  ', so_jogo[:10])
            assert not so_editor and not so_jogo, 'o editor não mostra a mesma colisão do jogo'
            print('✓ editor e jogo concordam tile a tile')

            # ---- 2) entrada bloqueada é barrada antes de publicar ----
            await page.evaluate("() => showScreen('mapaeditor')")
            avisos.clear()
            await page.evaluate("""() => {
                mapedSetMode('parede'); document.getElementById('maped-collide').checked=true;
                mapedSnapshot(); mapedAplicar(2,2);      // fecha a própria entrada
            }""")
            d = await page.evaluate("() => { const x=mapedDiagnostico(); return {preso:x.preso,sx:x.sx,sy:x.sy,alcance:x.alcance}; }")
            print('diagnóstico com a entrada fechada:', d)
            assert d['preso'] is True and d['sx']==2 and d['sy']==2, d
            info = await page.evaluate("() => document.getElementById('maped-info').innerHTML")
            assert 'entrada está bloqueada' in info, info
            await page.evaluate("() => mapedSalvar()")
            await page.wait_for_timeout(400)
            assert any('EM CIMA de algo que bloqueia' in a for a in avisos), avisos
            print('✓ publicar avisa que a entrada está bloqueada')

            # ---- 3) área fechada é detectada ----
            avisos.clear()
            fechado = await page.evaluate("""() => {
                // abre a entrada de novo e fecha o mapa numa caixinha de 3x3
                const l=mapedMapa.layers.find(l=>l.name==='Solid'),W=mapedMapa.width,H=mapedMapa.height;
                l.data.fill(0);
                for(let x=0;x<W;x++)for(let y=0;y<H;y++){
                  const dentro = x>=1&&x<=3&&y>=1&&y<=3;
                  const parede = (x>=0&&x<=4&&y>=0&&y<=4)&&!dentro;
                  if(parede)l.data[y*W+x]=1;
                }
                mapedMapa.properties=[{name:'spawn',type:'string',value:'2,2'}];
                const d=mapedDiagnostico();
                return {alcance:d.alcance, livre:d.livre, preso:d.preso};
            }""")
            print('preso numa caixa 3x3:', fechado)
            assert fechado['preso'] is False and fechado['alcance']==9, fechado
            await page.evaluate("() => mapedSalvar()")
            await page.wait_for_timeout(400)
            assert any('dá pra alcançar só' in a for a in avisos), avisos
            print('✓ publicar avisa quando o mapa fica fechado')

            # ---- 4) o overlay "ver colisão" desenha ----
            pintou = await page.evaluate("""() => {
                const cv=document.getElementById('maped-canvas'),ctx=cv.getContext('2d');
                document.getElementById('maped-vercol').checked=false; mapedDraw();
                const a=ctx.getImageData(0,0,160,160).data.join(',');
                document.getElementById('maped-vercol').checked=true; mapedDraw();
                const b=ctx.getImageData(0,0,160,160).data.join(',');
                return a!==b;
            }""")
            assert pintou, 'o "ver colisão" não mudou nada na tela'
            print('✓ "ver colisão" pinta o que bloqueia')

            # ---- 5) o pincel Parede desmarcado libera passagem no móvel ----
            lib = await page.evaluate("""() => {
                mapedNovo && 0;
                mapedSelectTileset('Kitchen'); mapedSel={c:0,r:1,w:3,h:2};
                mapedSetMode('objeto'); document.getElementById('maped-collide').checked=true;
                mapedSnapshot(); mapedAplicar(12,12);
                const antes=mapedGradeSolida()[12*mapedMapa.width+12];
                mapedSetMode('parede'); document.getElementById('maped-collide').checked=false;
                mapedAplicar(12,12);
                const depois=mapedGradeSolida()[12*mapedMapa.width+12];
                const l=mapedMapa.layers.find(l=>l.name==='Obj_Kitchen');
                const o=l.objects.find(o=>o.x/32===12);
                return {antes,depois,flag:o.properties.find(p=>p.name==='collide').value};
            }""")
            print('liberar passagem no móvel:', lib)
            assert lib['antes']==1 and lib['depois']==0 and lib['flag'] is False, lib
            print('✓ Parede desmarcado destrava móvel já colocado')

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK — o editor mostra a colisão real e avisa antes de publicar mapa intransitável')
        finally:
            await browser.close()
asyncio.run(main())
