# -*- coding: utf-8 -*-
# Corrigir o gabarito durante o treino: botão ao lado da lixeira abre a escolha do gabarito
# certo e a explicação. Salva no próprio item do acervo. Se a questão já foi respondida, a
# resposta é recorrigida: placar da sessão, contadores da questão, estatística do assunto
# e as questões de hoje acompanham.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

def seed():
    subs=[{'id':'s0','name':'Assunto 0','priority':70,'studied':True,'studiedAt':'2026-01-01'}]
    return make_seed({'studyNickname':'Leo','kingdoms':[{'id':'k1','name':'Dir. Administrativo','icon':'⚖️'}],
      'topics':{'k1':[{'id':'t1','name':'Poder Legislativo','icon':'⚔️','subtopics':subs}]}})

ACERVO="""()=>{db.acervo=[];
  const q={questao:'Compete privativamente à Assembleia dispor sobre cargos.',correta:'E',formato:'certoerrado',
    alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],explicacao:'Explicação antiga.',subId:'s0',subName:'Assunto 0',
    topicName:'Poder Legislativo',kingdomId:'k1',kingdomName:'Dir. Administrativo',kingdomIcon:'⚖️'};
  db.acervo.push({...q,_chaveForte:acervoChave2(q),...acervoCamposNovos('ia')});
  const m={questao:'Assinale a correta.',correta:'A',formato:'multipla',
    alternativas:[{letra:'A',texto:'um'},{letra:'B',texto:'dois'},{letra:'C',texto:'três'},{letra:'D',texto:'quatro'},{letra:'E',texto:'cinco'}],
    explicacao:'x',subId:'s0',subName:'Assunto 0',topicName:'Poder Legislativo',kingdomId:'k1',kingdomName:'Dir. Administrativo',kingdomIcon:'⚖️'};
  db.acervo.push({...m,_chaveForte:acervoChave2(m),...acervoCamposNovos('ia')});
  return db.acervo.length;}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(ACERVO)
        await page.evaluate("()=>{showScreen('simgeral');treinoIniciar([db.acervo[0]],{titulo:'Gab',ordenado:true});renderSimGeralScreen();return true;}")

        print('=== A) botão ao lado da lixeira; responder C com gabarito E = errou ===')
        r=await page.evaluate("""()=>{const ac=document.querySelector('.treino-q-acoes');
          const bts=[...ac.querySelectorAll('button')].map(b=>b.getAttribute('onclick'));
          treinoSelecionar('C');treinoConfirmarResposta();
          return {bts,erradas:treinoSessao.erradas,dia:JSON.parse(JSON.stringify(db.questoesPorDia[todayStr()])),
            sub:JSON.parse(JSON.stringify(simFindSub('s0').simStats))};}""")
        print('   %s'%r)
        assert r['bts']==['treinoEditarGabaritoAbrir()','treinoExcluirQuestaoAtual()'] and r['erradas']==1
        assert r['dia']=={'n':1,'c':0,'x':1}
        print('   OK\n')

        print('=== B) corrigir pra C com "recorrigir": vira acerto em todo lugar ===')
        await page.click('.treino-q-acoes button:first-child')
        r=await page.evaluate("""()=>{const ops=[...document.querySelectorAll('.gab-ed-op')].map(b=>b.textContent.trim());
          return {ops,on:document.querySelector('.gab-ed-op.on').dataset.letra,rec:!!document.getElementById('gab-ed-recorrigir')};}""")
        print('   %s'%r)
        assert r['on']=='E' and r['rec'] and len(r['ops'])==2
        await page.click('.gab-ed-op[data-letra="C"]')
        await page.fill('#gab-ed-exp','Art. 80, VI, da Constituição de Alagoas: é da Assembleia.')
        await page.click('.gab-ed-acoes .btn-primary')
        r=await page.evaluate("""()=>{const q=db.acervo[0];const s=treinoSessao;
          return {correta:q.correta,exp:q.explicacao,editado:!!q.gabaritoEditadoEm,res:q.ultimoResultado,acertos:q.acertos,erros:q.erros,
            sessao:[s.certas,s.erradas],dia:db.questoesPorDia[todayStr()],contada:q.contadaResultado,
            sub:[simFindSub('s0').simStats.acertosTotal,simFindSub('s0').simStats.porFormato.certoerrado.acertos],
            banner:document.querySelector('.sim-score-banner').textContent.trim()};}""")
        print('   %s'%r)
        assert r['correta']=='C' and r['exp'].startswith('Art. 80') and r['editado'] and r['res']=='C'
        assert r['acertos']==1 and r['erros']==0 and r['sessao']==[1,0] and r['dia']=={'n':1,'c':1,'x':0} and r['contada']=='C'
        assert r['sub']==[1,1] and 'acertou' in r['banner']
        print('   OK\n')

        print('=== C) múltipla, sem responder: troca o gabarito sem mexer em contagem ===')
        r=await page.evaluate("""()=>{treinoIniciar([db.acervo[1]],{titulo:'M',ordenado:true});renderSimGeralScreen();
          treinoEditarGabaritoAbrir();const n=document.querySelectorAll('.gab-ed-op').length;const rec=!!document.getElementById('gab-ed-recorrigir');
          treinoGabaritoNovo='D';treinoEditarGabaritoSalvar();
          return {n,rec,correta:db.acervo[1].correta,vezes:db.acervo[1].vezesRespondida||0};}""")
        print('   %s'%r)
        assert r['n']==5 and not r['rec'] and r['correta']=='D' and r['vezes']==0
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
