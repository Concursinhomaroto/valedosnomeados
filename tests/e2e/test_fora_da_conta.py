# -*- coding: utf-8 -*-
# Marcar "Item desatualizado" tirava o item das estatisticas do assunto, mas o placar
# DAQUELA tela continuava igual — e e esse numero que a pessoa olha. Voce tirava o item
# da conta e continuava vendo o erro contado contra voce.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
from test_banco_provas import LOTE

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
      'topics':{'k1':[{'id':'t1','name':'Urgencia','icon':'⚔️','subtopics':[
          {'id':'s1','name':'Choque septico','priority':70,'studied':True},
          {'id':'s2','name':'PCR','priority':70,'studied':True}]}]}})

def num(t,rx):
    import re
    m=re.search(rx,t)
    return m.group(1) if m else None

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('provas');return true;}")

        print('=== A) prova de 10: 6 acertos, 3 erros, 1 branco ===')
        r=await page.evaluate("""async(x)=>{
          (%s)(10);
          simColarIniciar(false);
          simGeralActive.questoes.forEach((q,i)=>{
            if(i<6)q.userAnswer=q.correta;
            else if(i<9)q.userAnswer=(q.correta==='C'?'E':'C');});
          simGeralActive.tempoGastoSec=600;
          simGeralCorrigir();
          await new Promise(r=>setTimeout(r,400));
          const t=document.getElementById('simgeral-content').innerText;
          return {banner:t.match(/(\\d+)\\/(\\d+) acertos \\((\\d+)%%\\)/).slice(1,4),
                  saldo:(t.match(/saldo Cebraspe: ([+-]?\\d+)/)||[])[1],
                  fora:/saiu da conta|saíram da conta/.test(t)};}"""%LOTE,0)
        print('   banner: %s/%s (%s%%) · saldo %s · aviso de item fora: %s'
              %(r['banner'][0],r['banner'][1],r['banner'][2],r['saldo'],r['fora']))
        assert r['banner']==['6','10','60'] and r['saldo']=='+3' and not r['fora']
        print('   OK\n')

        print('=== B) marcar um ERRO como desatualizado refaz o placar na hora ===')
        r=await page.evaluate("""()=>{
          simMotivoSalvar(6,'datado');          // item 7: um dos erros
          const t=document.getElementById('simgeral-content').innerText;
          return {banner:t.match(/(\\d+)\\/(\\d+) acertos \\((\\d+)%\\)/).slice(1,4),
                  saldo:(t.match(/saldo Cebraspe: ([+-]?\\d+)/)||[])[1],
                  aviso:/1 item saiu da conta/.test(t),
                  cartaoAceso:document.querySelectorAll('#simgeral-content .sim-q')[6]
                              .classList.contains('sim-q-flagged'),
                  bannerCartao:document.querySelectorAll('#simgeral-content .sim-q')[6]
                              .querySelector('.sim-flagged-banner').style.display!=='none'};}""")
        print('   banner: %s/%s (%s%%) · saldo %s'
              %(r['banner'][0],r['banner'][1],r['banner'][2],r['saldo']))
        print('   aviso "1 item saiu da conta": %s · cartão aceso: %s · faixa no cartão: %s'
              %(r['aviso'],r['cartaoAceso'],r['bannerCartao']))
        assert r['banner']==['6','9','67'], r['banner']
        assert r['saldo']=='+4', r['saldo']   # o erro sumiu: 6 acertos - 2 erros
        assert r['aviso'] and r['cartaoAceso'] and r['bannerCartao']
        print('   o erro deixou de pesar: 6/10 virou 6/9, e o saldo subiu de +3 pra +4')
        print('   OK\n')

        print('=== C) desmarcar devolve o item pro placar ===')
        r=await page.evaluate("""()=>{
          simMotivoSalvar(6,'datado');
          const t=document.getElementById('simgeral-content').innerText;
          return {banner:t.match(/(\\d+)\\/(\\d+) acertos/).slice(1,3),
                  saldo:(t.match(/saldo Cebraspe: ([+-]?\\d+)/)||[])[1],
                  aceso:document.querySelectorAll('#simgeral-content .sim-q')[6]
                        .classList.contains('sim-q-flagged')};}""")
        print('   %s/%s · saldo %s · cartão aceso: %s'
              %(r['banner'][0],r['banner'][1],r['saldo'],r['aceso']))
        assert r['banner']==['6','10'] and r['saldo']=='+3' and not r['aceso']
        print('   OK\n')

        print('=== D) marcar um ACERTO como desatualizado tira ele tambem ===')
        r=await page.evaluate("""()=>{
          simMotivoSalvar(0,'datado');          // item 1: um acerto
          const t=document.getElementById('simgeral-content').innerText;
          return {banner:t.match(/(\\d+)\\/(\\d+) acertos/).slice(1,3),
                  saldo:(t.match(/saldo Cebraspe: ([+-]?\\d+)/)||[])[1]};}""")
        print('   %s/%s · saldo %s'%(r['banner'][0],r['banner'][1],r['saldo']))
        assert r['banner']==['5','9'] and r['saldo']=='+2'
        print('   acerto contra norma revogada também não é conhecimento')
        print('   OK\n')

        print('=== E) a quebra por assunto acompanha ===')
        # A quebra deixou de ser uma linha por assunto: agora abre no bloco do edital,
        # e o assunto-a-assunto fica atras do botao. Os dois precisam somar o mesmo.
        r=await page.evaluate("""()=>{
          const pega=sel=>[...document.querySelectorAll('#simgeral-content '+sel)]
            .map(e=>e.innerText.replace(/\\n/g,' ').trim());
          const somar=ls=>ls.map(l=>l.match(/(\\d+)\\/(\\d+)/)).filter(Boolean)
                          .reduce((a,m)=>a+ +m[2],0);
          const blocos=pega('.sg-bloco');
          document.querySelector('#simgeral-content .sg-mais').click();
          const assuntos=pega('.sg-todos-linha');
          document.querySelector('#simgeral-content .sg-mais').click();
          return {blocos,assuntos,somaBloco:somar(blocos),somaAssunto:somar(assuntos)};}""")
        for l in r['blocos']: print('   bloco: %s'%l)
        for l in r['assuntos']: print('   assunto: %s'%l)
        print('   soma por bloco: %s · soma por assunto: %s'%(r['somaBloco'],r['somaAssunto']))
        assert r['somaBloco']==9 and r['somaAssunto']==9, (r['somaBloco'],r['somaAssunto'])
        print('   OK\n')

        print('=== F) o banco de provas mostra o mesmo numero ===')
        r=await page.evaluate("""()=>{
          const h=provasGuardadasHTML();
          const m=h.match(/1ª: <b[^>]*>(\\d+)\\/(\\d+)<\\/b>[^·]*· líq\\. ([+-]?\\d+)/);
          return {acertos:m&&m[1],total:m&&m[2],liq:m&&m[3],
                  selo:/1 fora da conta/.test(h)};}""")
        print('   no banco: %s/%s · líq. %s · selo "1 fora da conta": %s'
              %(r['acertos'],r['total'],r['liq'],r['selo']))
        assert r['acertos']=='5' and r['total']=='9' and r['liq']=='+2' and r['selo']
        print('   os dois lugares contam igual')
        print('   OK\n')

        print('=== G) a marcacao sobrevive e a revisao ja abre com a conta certa ===')
        r=await page.evaluate("""()=>{
          provaRevisar(db.provas[0].id);
          const t=document.getElementById('simgeral-content').innerText;
          return {banner:t.match(/(\\d+)\\/(\\d+) acertos/).slice(1,3),
                  aviso:/1 item saiu da conta/.test(t),
                  motivos:simGeralActive.questoes.filter(q=>q.motivo==='datado').length};}""")
        print('   na revisão: %s/%s · aviso: %s · itens marcados como datados: %s'
              %(r['banner'][0],r['banner'][1],r['aviso'],r['motivos']))
        assert r['banner']==['5','9'] and r['aviso'] and r['motivos']==1
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
