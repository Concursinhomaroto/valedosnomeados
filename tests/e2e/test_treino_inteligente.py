# -*- coding: utf-8 -*-
# Máquina de vencer: o "Treino inteligente" monta a rodada que mais rende ponto com o que
# o acervo já sabe — erros a consertar, chutes/difíceis, novas dos assuntos fracos (edital
# em foco primeiro) e acertos antigos — sem repetir o que foi respondido hoje. Meta diária
# de questões no cartão; "Mais uma rodada" no fim da sessão.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

def seed():
    subs=[{'id':'s%d'%i,'name':'Assunto %d'%i,'priority':70,'studied':True,'studiedAt':'2026-01-01'} for i in range(4)]
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],
      'topics':{'k1':[{'id':'t1','name':'Urgência','icon':'⚔️','subtopics':subs}]}})

# 10 erradas (2 delas hoje), 6 chutes, 4 difíceis, 30 novas (s0..s3), 8 acertadas há 40 dias, 5 acertadas ontem
ACERVO="""()=>{db.acervo=[];let n=0;
  const add=(sid,extra)=>{const q={questao:'Q'+(n++)+' '+sid+': julgue o item.',correta:'C',formato:'certoerrado',
    alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],explicacao:'.',subId:sid,subName:'Assunto '+sid.slice(1),
    topicName:'Urgência',kingdomId:'k1',kingdomName:'Enfermagem',kingdomIcon:'💉'};
    db.acervo.push({...q,_chaveForte:acervoChave2(q),...acervoCamposNovos('ia'),...extra});};
  const dias=d=>new Date(Date.now()-d*86400000).toISOString();
  for(let i=0;i<10;i++)add('s'+(i%4),{vezesRespondida:1,erros:1,ultimoResultado:'X',ultimaVezEm:i<2?new Date().toISOString():dias(3),tag:'ferida'});
  for(let i=0;i<6;i++)add('s1',{vezesRespondida:1,acertos:1,ultimoResultado:'C',chuteAcertos:1,ultimaVezEm:dias(5),tag:'chute'});
  for(let i=0;i<4;i++)add('s2',{vezesRespondida:4,acertos:1,erros:3,ultimoResultado:'C',dificuldadeAferida:'dificil',ultimaVezEm:dias(2),tag:'dificil'});
  for(let i=0;i<30;i++)add('s'+(i%4),{tag:'nova'});
  for(let i=0;i<8;i++)add('s3',{vezesRespondida:1,acertos:1,ultimoResultado:'C',ultimaVezEm:dias(40),tag:'antiga'});
  for(let i=0;i<5;i++)add('s3',{vezesRespondida:1,acertos:1,ultimoResultado:'C',ultimaVezEm:dias(1),tag:'recente'});
  return db.acervo.length;}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(ACERVO)

        print('=== A) rodada de 20: 8 erros, 4 chutes/difíceis, 5 novas, 3 antigas — nada de hoje ===')
        r=await page.evaluate("""()=>{const m=tiMontar(20);const tags={};m.itens.forEach(q=>tags[q.tag]=(tags[q.tag]||0)+1);
          const hoje=todayStr();
          return {total:m.total,partes:m.partes,tags,deHoje:m.itens.filter(q=>missaoHojeStr(q.ultimaVezEm)===hoje).length,
            unicas:new Set(m.itens.map(q=>q._chaveForte)).size};}""")
        print('   %s'%r)
        assert r['total']==20 and r['unicas']==20 and r['deHoje']==0
        assert r['partes']=={'feridas':8,'chutes':4,'novas':5,'relembrar':3}, r['partes']
        assert r['tags'].get('recente',0)==0, 'acerto de ontem não é "pra relembrar"'
        print('   OK\n')

        print('=== B) parte sem questão: o resto completa (rodada de 30 com só 8 erros disponíveis) ===')
        r=await page.evaluate("""()=>{const m=tiMontar(30);return {total:m.total,partes:m.partes};}""")
        print('   %s'%r)
        assert r['total']==30 and r['partes']['feridas']==8 and sum(r['partes'].values())==30
        print('   OK\n')

        print('=== C) edital em foco: novas do edital vêm primeiro ===')
        r=await page.evaluate("""()=>{const real=window.edFocoIndice;
          window.edFocoIndice=()=>({edital:{nome:'X',icon:'🎯'},idx:{s2:{peso:1,prev:1}}});
          const m=tiMontar(20);window.edFocoIndice=real;
          return m.itens.filter(q=>q.tag==='nova').map(q=>q.subId);}""")
        print('   novas: %s'%r)
        assert r and all(x=='s2' for x in r[:3])
        print('   OK\n')

        print('=== D) cartão: composição, tamanho lembrado, meta do dia; Treinar inicia a sessão ===')
        r=await page.evaluate("""()=>{showScreen('simgeral');
          const card=document.querySelector('.treino-destaque');
          const out={titulo:card.querySelector('.treino-destaque-titulo').textContent,comp:card.querySelectorAll('.ti-comp span').length,
            meta:card.querySelector('.ti-meta span').textContent,btn:card.querySelector('.treino-destaque-btn').textContent.trim()};
          tiEscolherTamanho(10);
          out.btn10=document.querySelector('.treino-destaque .treino-destaque-btn').textContent.trim();
          let salvo=null;try{salvo=localStorage.getItem('vdn_ti_n');}catch(e){}out.salvo=salvo;
          tiComecar();out.sessao=treinoSessao?{n:treinoSessao.itens.length,titulo:treinoSessao.titulo}:null;
          return out;}""")
        print('   %s'%r)
        assert r['titulo']=='Treino inteligente' and r['comp']==4 and r['meta']=='0/30 hoje'
        assert r['btn']=='Treinar 20 agora' and r['btn10']=='Treinar 10 agora' and r['salvo']=='10'
        assert r['sessao']=={'n':10,'titulo':'⚡ Treino inteligente'}
        print('   OK\n')

        print('=== E) responder conta nas questões de hoje e o fim oferece "mais uma rodada" ===')
        r=await page.evaluate("""()=>{const s=treinoSessao;
          const esperado=s.itens.filter(q=>questoesDiaDeveContar(q,todayStr())).length;
          for(let k=0;k<s.itens.length;k++){treinoSelecionar('C');treinoConfirmarResposta();if(k<s.itens.length-1)treinoProxima();}
          treinoEncerrar&&treinoEncerrar();
          const res=document.getElementById('simgeral-content').innerText;
          return {hoje:questoesDiaResumo().n,esperado,mais:res.indexOf('Mais uma rodada inteligente')>=0};}""")
        print('   %s'%r)
        # refazer o que você respondeu há menos de 7 dias não soma (regra das questões de hoje)
        assert r['hoje']==r['esperado'] and 0<r['esperado']<10 and r['mais']
        r=await page.evaluate("""()=>{const prox=tiMontar(20);const hoje=todayStr();
          return prox.itens.filter(q=>missaoHojeStr(q.ultimaVezEm)===hoje).length;}""")
        assert r==0, 'a rodada seguinte não repete o que acabou de responder'
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
