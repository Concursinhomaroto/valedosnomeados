# -*- coding: utf-8 -*-
# Redesign, fase A3: Painel em faixas. A faixa de hoje usa a mesma conta do selo do menu;
# o cartao "Hoje" tem UM botao primario (mesmo handler de antes); o Diagnostico troca de
# aba so mostrando/escondendo os mesmos conteineres; "Mais numeros" lembra se ficou aberto.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

def seed():
    subs=[{'id':'s%d'%i,'name':'Assunto %d'%i,'priority':70,'studied':True,'studiedAt':'2026-01-01'} for i in range(4)]
    return make_seed({'studyNickname':'Leo','examDate':'2026-12-25',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],
      'topics':{'k1':[{'id':'t1','name':'Urgência','icon':'⚔️','subtopics':subs}]},
      'revisions':{'s0':[{'date':'2026-01-10','completed':False}],'s1':[{'date':'2026-01-12','completed':False}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('dashboard');return true;}")
        await page.wait_for_timeout(300)

        print('=== A) faixa de hoje: dias pra prova e atrasadas com a mesma conta do menu ===')
        r=await page.evaluate("""()=>({dias:document.getElementById('dash-prova-dias').textContent,
          esperado:String(daysDiff(todayStr(),db.examDate)),
          atrasadas:document.getElementById('dash-atrasadas-val').textContent,
          menu:document.getElementById('rev-badge').textContent})""")
        print('   %s'%r)
        assert r['dias']==r['esperado'] and r['atrasadas']=='2' and r['menu']=='2'
        print('   OK\n')

        print('=== B) cartao de atrasadas e o botao grande abrem a fila de hoje ===')
        r=await page.evaluate("""()=>{document.getElementById('dash-atrasadas-card').click();
          const a=document.getElementById('screen-revisions').classList.contains('active');
          showScreen('dashboard');
          const btn=document.querySelector('#divida-resumo .div-btn');
          const h=btn?btn.getAttribute('onclick'):'';
          if(btn)btn.click();
          const b=document.getElementById('screen-revisions').classList.contains('active');
          showScreen('dashboard');return {cartao:a,botao:b,handler:h};}""")
        print('   %s'%r)
        assert r['cartao'] and r['botao'] and r['handler']=='abrirRevisoesAtrasadas()'
        print('   OK\n')

        print('=== C) abas do Diagnostico mostram so o painel escolhido ===')
        vis="""()=>({sim:getComputedStyle(document.querySelector('.dd-p-sim')).display!=='none',
          reinos:getComputedStyle(document.querySelector('.dd-p-reinos')).display!=='none',
          erros:getComputedStyle(document.querySelector('.dd-p-erros')).display!=='none'})"""
        r0=await page.evaluate(vis)
        await page.click('label[for=dd-erros]')
        r1=await page.evaluate(vis)
        await page.click('label[for=dd-reinos]')
        r2=await page.evaluate(vis)
        print('   inicio %s | erros %s | reinos %s'%(r0,r1,r2))
        assert r0=={'sim':True,'reinos':False,'erros':False}
        assert r1=={'sim':False,'reinos':False,'erros':True}
        assert r2=={'sim':False,'reinos':True,'erros':False}
        r=await page.evaluate("()=>document.getElementById('controle-erros').innerText")
        assert 'Nenhum erro classificado' in r, r
        print('   OK\n')

        print('=== D) "Mais numeros" comeca aberto e lembra quando fecha ===')
        r=await page.evaluate("""async()=>{const d=document.getElementById('dash-mais');const ini=d.open;
          d.querySelector('summary').click();await new Promise(r=>setTimeout(r,50));
          let salvo=null;try{salvo=localStorage.getItem('vdn_dash_mais');}catch(e){}
          d.querySelector('summary').click();await new Promise(r=>setTimeout(r,50));
          return {ini,salvo,depois:d.open};}""")
        print('   %s'%r)
        assert r['ini'] and r['salvo']=='0' and r['depois']
        print('   OK\n')

        print('=== E) nada rola por dentro no cartao Hoje e no Diagnostico ===')
        r=await page.evaluate("""()=>[...document.querySelectorAll('.dash-hoje *, .dash-diag *, .dash-agenda *')]
          .filter(e=>{const s=getComputedStyle(e);return /(auto|scroll)/.test(s.overflowY)&&e.scrollHeight>e.clientHeight+2;})
          .map(e=>e.id||e.className)""")
        print('   com rolagem interna: %s'%r)
        assert not r
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
