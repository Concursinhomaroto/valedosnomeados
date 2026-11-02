# -*- coding: utf-8 -*-
# Modo Revisar das Dicas: recordacao ativa (so a "pergunta" aparece ate revelar) + repeticao
# espacada em caixas de Leitner (1, 3, 7, 16 e 35 dias) sobre o db.dicasEstado. Cobre a fila
# (vencidas antes das novas, lote de 20), o que a tela esconde e mostra, as tres notas e o
# agendamento de cada uma, o erro voltando uma vez no fim, o teclado, o resumo final, o
# "ja sei" legado entrando na caixa 3 e o painel por materia / seletor de grupo.
import asyncio, os, sys
sys.path.insert(0,'.')
from test_sala import async_playwright
from test_aba_dicas import abrir, seed, graves

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        ctx,page,errs=await abrir(browser,seed())

        print('=== A) botao Revisar na aba, com a contagem do que vence hoje ===')
        r=await page.evaluate("""()=>{
          db.dicas=[];
          for(let i=0;i<30;i++)db.dicas.push(dicaNormalizar({id:'d'+i,kingdomId:'kPt',titulo:'Titulo '+i,
            regra:'Regra secreta '+i,cuidado:'Cuidado '+i,grupo:'G'+(i%2)},'minha'));
          db.dicas.push(dicaNormalizar({id:'n1',kingdomId:'kPt',tipo:'numero',titulo:'Prazo',rotulo:'Prazo do recurso',valor:'10 dias'},'minha'));
          db.dicas.push(dicaNormalizar({id:'p1',kingdomId:'kPt',tipo:'par',titulo:'A x B',a:'Mal',b:'Mau',diferenca:'Mau e o oposto de bom'},'minha'));
          showScreen('dicas');renderDicasScreen();
          return {btn:(document.querySelector('.dicas-rev-ini')||{}).textContent,pend:dicasRevPendentes().length};}""")
        print('   %s'%r)
        assert r['pend']==32 and '32' in r['btn']
        print('   OK\n')

        print('=== B) a pergunta aparece, a resposta so depois de revelar ===')
        r=await page.evaluate("""()=>{dicasRevIniciar();
          const el=document.getElementById('dicas-content');
          const antes={txt:el.innerText,mostrar:!!el.querySelector('.dicas-rev-mostrar'),notas:el.querySelectorAll('.dicas-rev-notas .btn').length,total:dicasRev.total};
          dicasRevRevelar();
          const dep={txt:el.innerText,notas:[...el.querySelectorAll('.dicas-rev-notas .btn')].map(b=>b.innerText.replace(/\\s+/g,' '))};
          return {antes,dep};}""")
        a,d=r['antes'],r['dep']
        print('   lote de %s · notas depois: %s'%(a['total'],d['notas']))
        assert a['total']==20 and a['mostrar'] and a['notas']==0 and 'Regra secreta' not in a['txt']
        assert 'Regra secreta' in d['txt'] and len(d['notas'])==3
        assert 'hoje' in d['notas'][0] and 'em 3 dias' in d['notas'][2], d['notas']   # nova + lembrei -> caixa 2
        print('   OK\n')

        print('=== C) as tres notas agendam e o erro volta uma vez no fim ===')
        r=await page.evaluate("""()=>{
          const hoje=todayStr();const ids=dicasRev.fila.slice(0,3);
          dicasRevNota('facil');                       // 1a: lembrei
          dicasRevRevelar();dicasRevNota('erro');      // 2a: errei
          dicasRevRevelar();dicasRevNota('dificil');   // 3a: dificil
          const e=ids.map(id=>db.dicasEstado[id]);
          return {hoje,e,total:dicasRev.total,fimDaFila:dicasRev.fila[dicasRev.fila.length-1]===ids[1],
                  lembrou:dicasRev.lembrou,errou:dicasRev.errou,i:dicasRev.i,soma:dicasRevSomaDias(hoje,3),amanha:dicasRevSomaDias(hoje,1)};}""")
        e=r['e']
        print('   lembrei: caixa %s prox %s · errei: caixa %s prox %s · dificil: caixa %s prox %s'%(e[0]['caixa'],e[0]['proxima'],e[1]['caixa'],e[1]['proxima'],e[2]['caixa'],e[2]['proxima']))
        assert e[0]['caixa']==2 and e[0]['proxima']==r['soma'] and not e[0]['sei']
        assert e[1]['caixa']==0 and e[1]['proxima']==r['hoje'] and e[1]['erros']==1
        assert e[2]['caixa']==1 and e[2]['proxima']==r['amanha'] and not e[2]['sei']
        assert r['total']==21 and r['fimDaFila'] and r['lembrou']==2 and r['errou']==1 and r['i']==3
        print('   OK\n')

        print('=== D) teclado: espaco revela, 3 lembrei, Esc sai ===')
        await page.keyboard.press('Space')
        assert await page.evaluate("()=>dicasRev.revelada")
        await page.keyboard.press('3')
        assert await page.evaluate("()=>dicasRev.i")==4
        await page.keyboard.press('Escape')
        assert await page.evaluate("()=>dicasRev===null&&!!document.querySelector('#dicas-busca')")
        print('   OK\n')

        print('=== E) terminar a sessao mostra o resumo e some o pendente ===')
        r=await page.evaluate("""()=>{
          const antes=dicasRevPendentes().length;dicasRevIniciar();let n=0;
          while(!dicasRev.fim&&n++<100){dicasRevRevelar();dicasRevNota('facil');}
          const el=document.getElementById('dicas-content');
          const tela=el.innerText;
          dicasRevSair();
          return {tela,antes,pend:dicasRevPendentes().length};}""")
        print('   restam %s pendentes'%r['pend'])
        assert 'Sessão concluída' in r['tela'] and r['pend']==r['antes']-20, r
        print('   OK\n')

        print('=== F) "ja sei" antigo (sem caixa) entra na caixa 3 e nao vence logo ===')
        r=await page.evaluate("""()=>{
          const d=dicaNormalizar({id:'leg',kingdomId:'kPt',titulo:'Legado',regra:'x'},'minha');db.dicas.push(d);
          db.dicasEstado.leg={sei:true,vistaEm:new Date().toISOString()};
          const venceHoje=dicasRevPendentes().some(x=>x.id==='leg');
          db.dicasEstado.leg={sei:true,vistaEm:'2020-01-01T00:00:00Z'};
          const venceVelha=dicasRevPendentes().some(x=>x.id==='leg');
          dicaJaSei('d29','aba');const e=db.dicasEstado.d29;
          return {venceHoje,venceVelha,manual:{c:e.caixa,sei:e.sei,p:e.proxima}};}""")
        print('   %s'%r)
        assert not r['venceHoje'] and r['venceVelha'] and r['manual']['c']>=3 and r['manual']['sei']
        print('   OK\n')

        print('=== G) muitas dicas: painel por materia e seletor de grupo ===')
        r=await page.evaluate("""()=>{
          db.dicas=[];
          for(let i=0;i<200;i++)db.dicas.push(dicaNormalizar({kingdomId:i%2?'kEnf':'kPt',grupo:'G'+(i%7)+(i%2?'e':'p'),titulo:'T'+i,regra:'r'},'minha'));
          dicasFiltro={...DICAS_FILTRO_VAZIO};renderDicasScreen();
          const el=document.getElementById('dicas-content');
          const painel=el.querySelectorAll('.dicas-materia-card').length,chipsGrupo=!!document.getElementById('dicas-chips-grupo'),cards=el.querySelectorAll('.dica-card').length;
          el.querySelector('.dicas-materia-card').click();
          const sel=document.querySelector('#dicas-chips-grupo select');
          const opts=[...sel.options].map(o=>o.textContent);
          dicasEscolherGrupo('G1p');
          return {painel,chipsGrupo,cards,opts,filtrado:document.querySelectorAll('#dicas-corpo .dica-card').length,grupo:dicasFiltro.grupo};}""")
        print('   %s'%r)
        assert r['painel']==2 and not r['chipsGrupo'] and r['cards']==0
        assert len(r['opts'])==8 and all('e ·' not in o for o in r['opts'])
        assert r['grupo']=='G1p' and r['filtrado']>0
        print('   OK\n')

        print('=== H) layout 375 px: sessao sem rolagem lateral ===')
        await page.set_viewport_size({'width':375,'height':800})
        r=await page.evaluate("""()=>{dicasFiltro={...DICAS_FILTRO_VAZIO};dicasFiltrarMateria('kPt');dicasRevIniciar();dicasRevRevelar();
          return {w:document.documentElement.scrollWidth,iw:innerWidth};}""")
        print('   %s'%r)
        assert r['w']<=r['iw']+1
        print('   OK\n')

        assert not graves(errs),graves(errs)
        print('erros de JS: nenhum\nOK')
        await browser.close()
asyncio.run(main())
