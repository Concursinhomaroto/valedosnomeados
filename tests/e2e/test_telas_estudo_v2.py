# -*- coding: utf-8 -*-
# Redesign, fase A4: o formulario de chefao virou "Novo chefao" (mesmos campos/ids), a
# linha do miniboss destaca "Estudar" e guarda renomear/excluir no "⋯", e a fila de
# revisoes separa "Revisar" das outras tres — sem nenhum botao sair do DOM.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

def seed():
    subs=[{'id':'s%d'%i,'name':'Assunto %d'%i,'priority':70,'studied':True,'studiedAt':'2026-01-01'} for i in range(2)]
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#ec4899'}],
      'topics':{'k1':[{'id':'t1','name':'Urgência','icon':'⚔️','subtopics':subs}]},
      'revisions':{'s0':[{'date':'2026-01-10','completed':False}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{window.confirm=()=>true;openKingdom(db.kingdoms[0]);"
                            "const bd=document.getElementById('tb-t1');if(bd&&bd.style.display==='none')toggleTopic('t1');return true;}")
        await page.wait_for_timeout(300)

        print('=== A) "Novo chefão" abre o mesmo formulário e cria o chefão ===')
        r=await page.evaluate("()=>({fechado:!document.querySelector('.reino-novo-chefao').open,"
                              "visivel:document.getElementById('new-topic-name').checkVisibility()})")
        print('   antes de abrir: %s'%r)
        assert r['fechado'] and not r['visivel']
        await page.click('.reino-novo-chefao > summary')
        await page.fill('#new-topic-name','Saúde da Mulher')
        await page.click('.reino-novo-chefao .add-form .btn-primary')
        await page.wait_for_timeout(300)
        r=await page.evaluate("()=>(db.topics.k1||[]).map(t=>t.name)")
        print('   chefões: %s'%r)
        assert 'Saúde da Mulher' in r
        print('   OK\n')

        print('=== B) linha do miniboss: todos os botões no DOM, Estudar primeiro, ⋯ com renomear/excluir ===')
        await page.evaluate("()=>{const bd=document.getElementById('tb-t1');if(bd&&bd.style.display==='none')toggleTopic('t1');return true;}")
        await page.wait_for_timeout(200)
        r=await page.evaluate("""()=>{const it=document.getElementById('si-s0');
          const on=[...it.querySelectorAll('.sub-actions button')].map(b=>(b.getAttribute('onclick')||'').split('(')[0]);
          return {on,primeiro:on[0],menuFechado:!it.querySelector('.sub-acoes-mais').open};}""")
        print('   %s'%r)
        for f in ['toggleTimer','showSubRevisions','toggleNote','toggleResumo','toggleFlash','toggleSim','toggleFluxo','renameSubtopic','deleteSub']:
            assert f in r['on'], f
        assert r['primeiro']=='toggleTimer' and r['menuFechado']
        await page.click('#si-s0 .sub-acoes-mais > summary')
        r=await page.evaluate("()=>[...document.querySelectorAll('#si-s0 .sub-acoes-mais-menu button')].map(b=>b.checkVisibility())")
        assert r==[True]*5, r   # rodada 2: Revisões, Anotar, Fluxograma, Renomear, Excluir
        await page.click('#si-s0 .sub-acoes-mais-menu .btn-danger')
        await page.wait_for_timeout(300)
        r=await page.evaluate("()=>db.topics.k1[0].subtopics.map(s=>s.id)")
        print('   depois de excluir pelo ⋯: %s'%r)
        assert 's0' not in r
        print('   OK\n')

        print('=== C) fila de revisões: Revisar + três ações distintas, mesmos handlers ===')
        r=await page.evaluate("""()=>{db.topics.k1[0].subtopics.push({id:'s9',name:'Assunto 9',priority:70,studied:true,studiedAt:'2026-01-01'});
          db.revisions={s9:[{date:'2026-01-10',completed:false}]};showScreen('revisions');
          const it=document.querySelector('#revisions-list .rev-item');
          const bs=[...it.querySelectorAll('.rev-acoes button')];
          return bs.map(b=>({txt:b.textContent.trim(),on:(b.getAttribute('onclick')||'').split('(')[0],cor:getComputedStyle(b).backgroundColor}));}""")
        for x in r: print('   %s'%x)
        assert [x['on'] for x in r]==['revAbrirTela','revConcluirDaFila','revConcluirDaFila','revDominar']
        assert len({x['cor'] for x in r})==4, 'as quatro ações precisam ter cores diferentes'
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
