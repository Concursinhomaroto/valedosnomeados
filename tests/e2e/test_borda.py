import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p, make_seed({'studyNickname':'Reitor','studyCharacter':'ash'}))
        try:
            await page.evaluate("() => showScreen('mapaeditor')")
            await page.wait_for_function("() => !!mapedMapa", timeout=20000)
            await page.evaluate("(n)=>mapedSelectTileset(n)", 'Kitchen')
            await page.wait_for_function("() => { const im=mapedImgs[mapedTS.n]; return im&&im.complete&&im.naturalWidth>0; }", timeout=15000)

            # 1) peça larga (16 tiles) na borda direita: encaixa e nada some
            r = await page.evaluate("""() => {
              const peca=mapedPecaInteira(1,2);
              mapedSel=peca; mapedSetMode('objeto');
              const W=mapedMapa.width,H=mapedMapa.height,res=[];
              for(const tx of [40,80,85,91]){
                const l0=(mapedMapa.layers.find(l=>l.name==='Obj_Kitchen')||{objects:[]}).objects.length;
                mapedAplicar(tx,40);
                const l=mapedMapa.layers.find(l=>l.name==='Obj_Kitchen');
                const novos=l.objects.slice(l0);
                res.push({tx,criados:novos.length,
                          fora:novos.filter(o=>o.x/32>=W||o.y/32>H||o.x<0).length,
                          x0:novos[0].x/32, x1:novos[novos.length-1].x/32});
              }
              return {W,H,peca,res};
            }""")
            print('peça', r['peca'], '| mapa', r['W'],'x',r['H'])
            for x in r['res']:
                print(f"  clique tx={x['tx']:3d} -> {x['criados']} tiles de x={x['x0']} a x={x['x1']}, fora do mapa: {x['fora']}")
                assert x['fora'] == 0, 'ainda cria peça fora do mapa'
                assert x['criados'] == r['peca']['w']*r['peca']['h'], 'peça saiu incompleta'
                assert x['x1'] <= r['W']-1, x
            # encaixou: o clique em 91 vira 76 (92-16)
            assert r['res'][-1]['x0'] == r['W']-r['peca']['w'], r['res'][-1]

            # 2) borda de baixo também
            await page.evaluate("() => { mapedSetMode('objeto'); mapedAplicar(10, mapedMapa.height-1); }")
            baixo = await page.evaluate("""() => {
              const l=mapedMapa.layers.find(l=>l.name==='Obj_Kitchen'),H=mapedMapa.height;
              return l.objects.filter(o=>o.y/32>H).length;
            }""")
            assert baixo == 0, f'{baixo} peças passaram da borda de baixo'

            # 3) ambiente pronto grande na borda também encaixa
            await page.evaluate("""() => { mapedSetMode('ambiente'); mapedEscolheDesign('Museum_room_2'); mapedCarimbarAmbiente(88,68); }""")
            amb = await page.evaluate("""() => {
              const d=SALA_DESIGNS.find(x=>x.id==='Museum_room_2');
              const W=mapedMapa.width,H=mapedMapa.height;
              const nomes=d.camadas.filter(c=>c.papel!=='chao').map(c=>'Obj_'+c.ts);
              let fora=0,total=0;
              mapedMapa.layers.forEach(l=>{ if(!nomes.includes(l.name))return;
                total+=l.objects.length;
                fora+=l.objects.filter(o=>o.x/32>=W||o.y/32>H).length; });
              return {total,fora,d:[d.w,d.h]};
            }""")
            print('ambiente', amb)
            assert amb['fora'] == 0 and amb['total'] > 0, amb

            # 4) mapa antigo com fantasma é limpo ao abrir
            limpou = await page.evaluate("""() => {
              const l=mapedCamada('Obj_Kitchen');
              l.objects.push({gid:6226,height:32,id:999999,name:'',rotation:0,type:'',visible:true,
                              width:32,x:200*32,y:5*32+32,properties:[]});
              const antes=l.objects.length;
              const copia=JSON.parse(JSON.stringify(mapedMapa));
              mapedCarregar(copia);
              const l2=mapedMapa.layers.find(l=>l.name==='Obj_Kitchen');
              return {antes, depois:l2.objects.length};
            }""")
            print('limpeza de fantasma:', limpou)
            assert limpou['depois'] == limpou['antes']-1, limpou

            # 5) o contorno segue o cursor e mostra o tamanho encaixado
            await page.evaluate("""() => {
              mapedSelectTileset('Kitchen'); mapedSel=mapedPecaInteira(1,2); mapedSetMode('objeto');
              const cv=document.getElementById('maped-canvas'),r=cv.getBoundingClientRect();
              mapedCanvasHover({clientX:r.left+91*32+8, clientY:r.top+40*32+8});
            }""")
            gh = await page.evaluate("""() => { const g=document.getElementById('maped-ghost');
              return {display:g.style.display,left:g.style.left,width:g.style.width}; }""")
            print('contorno:', gh)
            assert gh['display'] == 'block', gh
            assert gh['left'] == f"{(r['W']-r['peca']['w'])*32}px", gh   # já mostra encaixado
            assert gh['width'] == f"{r['peca']['w']*32}px", gh

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK — peça encaixa na borda, nada vira fantasma, e o contorno avisa antes do clique')
        finally:
            await browser.close()
asyncio.run(main())
