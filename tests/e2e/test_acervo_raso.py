# -*- coding: utf-8 -*-
# Rodada 2, item 5: o mosaico "Mapa do Acervo" sai da frente (vai pra "Cobertura do
# banco", recolhido) e no lugar entra "Onde o banco está raso" — os assuntos com menos de
# 15 questões, do menor pro maior, com chefão, nº e acerto. A linha chama o mesmo
# bancoMapaAbrirAssunto() do quadrado. A lista de questões ganha "carregar mais".
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

def seed():
    subs=[{'id':'s%d'%i,'name':'Assunto %02d'%i,'priority':70,'studied':True,'studiedAt':'2026-01-01'} for i in range(14)]
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],
      'topics':{'k1':[{'id':'t1','name':'Urgência','icon':'⚔️','subtopics':subs[:7]},
                      {'id':'t2','name':'Saúde da Mulher','icon':'⚔️','subtopics':subs[7:]}]}})

# s0 tem 20 questões (não é raso); s1..s13 têm 1..13 (rasos). Total = 20+91 = 111.
ACERVO = """()=>{
  const subs=[];db.kingdoms.forEach(k=>(db.topics[k.id]||[]).forEach(t=>(t.subtopics||[]).forEach(s=>subs.push({k,t,s}))));
  db.acervo=[];
  subs.forEach(({k,t,s},i)=>{const n=i===0?20:i;for(let j=0;j<n;j++){
    const q={questao:`Questão ${j} de ${s.name}: julgue o item.`,correta:'C',formato:'certoerrado',
      alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],explicacao:'.',
      subId:s.id,subName:s.name,topicName:t.name,kingdomId:k.id,kingdomName:k.name,kingdomIcon:k.icon};
    db.acervo.push({...q,_chaveForte:acervoChave2(q),...acervoCamposNovos('ia'),
      vezesRespondida:j%2,acertos:j%4===1?1:0,ultimoResultado:j%2?'C':null});}});
  return db.acervo.length;}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        n=await page.evaluate(ACERVO)
        await page.evaluate("()=>{window.__saves=0;const o=window.saveDB;window.saveDB=function(){window.__saves++;return o.apply(this,arguments)};}")
        await page.evaluate("()=>showScreen('banco')")
        await page.wait_for_timeout(400)

        print('=== A) "Onde o banco está raso": do menor pro maior, com chefão, 10 e "ver todos" ===')
        r=await page.evaluate("""()=>{const ls=[...document.querySelectorAll('#banco-raso .banco-raso-linha:not(.banco-raso-th)')];
          return {nomes:ls.map(l=>l.querySelector('.banco-raso-nome').textContent),
            ns:ls.map(l=>+l.querySelector('.banco-raso-n').textContent),
            chefoes:ls.map(l=>l.querySelector('.banco-raso-chefao').textContent),
            todos:(document.querySelector('.banco-raso-todos')||{}).textContent,
            gerar:!!document.querySelector('#banco-raso [onclick="bancoMapaGerarOndeRaso()"]')};}""")
        print('   %s'%r)
        assert n==111 and len(r['ns'])==10 and r['ns']==sorted(r['ns']) and r['ns'][0]==1
        assert 'Assunto 00' not in r['nomes'], 'assunto com 20 questões não é raso'
        assert r['chefoes'][0]=='Urgência' and 'Saúde da Mulher' in r['chefoes']
        assert r['todos']=='ver todos (13)' and r['gerar']
        await page.click('.banco-raso-todos')
        r=await page.evaluate("()=>document.querySelectorAll('#banco-raso .banco-raso-linha:not(.banco-raso-th)').length")
        assert r==13, r
        print('   OK\n')

        print('=== B) clicar na linha abre a lista filtrada naquele assunto (mesmo handler do mapa) ===')
        r=await page.evaluate("""()=>{const l=[...document.querySelectorAll('#banco-raso .banco-raso-linha')]
            .find(x=>(x.getAttribute('onclick')||'').includes("'s5'"));
          const h=l.getAttribute('onclick');l.click();
          const itens=[...document.querySelectorAll('#banco-filtro-lista .banco-item')];
          return {h,itens:itens.length,modo:document.getElementById('montar-modo').value};}""")
        print('   %s'%r)
        assert r['h']=="bancoMapaAbrirAssunto('s5')" and r['modo']=='assunto' and r['itens']==5
        print('   OK\n')

        print('=== C) "Cobertura do banco" começa recolhida e guarda o mosaico inteiro ===')
        await page.evaluate("()=>{montarSel=new Set();document.getElementById('montar-modo').value='todas';montarTrocarModo();}")
        await page.wait_for_timeout(200)
        r=await page.evaluate("""()=>{const d=document.querySelector('.banco-cobertura');
          return {existe:!!d,aberta:d&&d.open,celulas:d?d.querySelectorAll('.banco-mapa-cel').length:0,
            visivel:d?d.querySelector('.banco-mapa-grid').checkVisibility():null};}""")
        print('   %s'%r)
        assert r['existe'] and not r['aberta'] and r['celulas']==14 and not r['visivel']
        await page.click('.banco-cobertura > summary')
        await page.wait_for_timeout(250)   # o <details> abre no quadro seguinte ao clique
        r=await page.evaluate("()=>document.querySelector('.banco-cobertura .banco-mapa-grid').checkVisibility()")
        assert r
        # re-render da tela mantém o que a pessoa abriu
        await page.evaluate("()=>renderBancoScreen()")
        r=await page.evaluate("()=>document.querySelector('.banco-cobertura').open")
        assert r
        print('   OK\n')

        print('=== D) lista de questões: 30 por vez e "carregar mais" ===')
        r=await page.evaluate("""()=>{if(!bancoListaAberta)bancoListaToggle();
          const conta=()=>document.querySelectorAll('#banco-filtro-lista .banco-item').length;
          const a=conta();const btn=document.querySelector('.banco-lista-mais');const t1=btn&&btn.textContent.replace(/\\s+/g,' ').trim();
          btn.click();const b=conta();
          for(let i=0;i<5&&document.querySelector('.banco-lista-mais');i++)document.querySelector('.banco-lista-mais').click();
          return {a,t1,b,fim:conta(),botao:!!document.querySelector('.banco-lista-mais')};}""")
        print('   %s'%r)
        assert r['a']==30 and r['t1']=='carregar mais 30 (faltam 81)' and r['b']==60 and r['fim']==111 and not r['botao']
        print('   OK\n')

        print('=== E) importar em lote abre e fecha; ids da importação intactos ===')
        r=await page.evaluate("""()=>{bancoImportarAbrir();
          const ids=['banco-importar-txt','banco-importar-assunto-chefao','banco-importar-assunto','banco-card-importar'];
          const tem=ids.map(i=>!!document.getElementById(i));
          return {tem,fn:typeof bancoImportarProcessar};}""")
        print('   %s'%r)
        assert all(r['tem']) and r['fn']=='function'
        await page.evaluate("()=>{bancoImportando=false;renderBancoScreen();}")
        r=await page.evaluate("()=>!!document.getElementById('banco-importar-txt')")
        assert not r
        print('   OK\n')

        saves=await page.evaluate("()=>window.__saves")
        print('saveDB chamado: %s'%saves)
        assert saves==0, 'abrir e navegar o Acervo não pode gravar'
        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
