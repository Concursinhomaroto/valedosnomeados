# -*- coding: utf-8 -*-
# "Montar meu treino" em três níveis: Reino → Chefão → Miniboss. Escolher só o chefão
# treina o chefão inteiro (revisão por chefão). O chefão de cada questão sai da árvore do
# edital — se o miniboss mudou de chefão, a questão acompanha.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

def seed():
    sub=lambda i,n:{'id':i,'name':n,'priority':70,'studied':True,'studiedAt':'2026-01-01'}
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'},{'id':'k2','name':'Português','icon':'📖'}],
      'topics':{'k1':[{'id':'t1','name':'Saúde da Mulher','icon':'⚔️','subtopics':[sub('s1','Pré-natal'),sub('s2','Puerpério')]},
                      {'id':'t2','name':'Saúde da Criança','icon':'⚔️','subtopics':[sub('s3','Aleitamento')]}],
                'k2':[{'id':'t3','name':'Sintaxe','icon':'⚔️','subtopics':[sub('s4','Regência')]}]}})

# 3 questões por miniboss; s2 tem topicName velho ('Antigo') — a árvore manda
ACERVO="""()=>{db.acervo=[];const subs=[['s1','Pré-natal','Saúde da Mulher','k1','Enfermagem'],['s2','Puerpério','Antigo','k1','Enfermagem'],
  ['s3','Aleitamento','Saúde da Criança','k1','Enfermagem'],['s4','Regência','Sintaxe','k2','Português']];
  subs.forEach(([sid,sn,tn,kid,kn])=>{for(let j=0;j<3;j++){const q={questao:'Q'+j+' '+sid+': julgue.',correta:'C',formato:'certoerrado',
    alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],explicacao:'.',subId:sid,subName:sn,topicName:tn,kingdomId:kid,kingdomName:kn,kingdomIcon:'x'};
    db.acervo.push({...q,_chaveForte:acervoChave2(q),...acervoCamposNovos('ia')});}});return db.acervo.length;}"""

LER="""()=>{const sels=[...document.querySelectorAll('#treino-montar-bar select')];
  const ops=i=>[...sels[i].options].map(o=>o.textContent);
  return {rotulos:sels.slice(0,3).map(s=>s.options[0].textContent),reinos:ops(0),chefoes:ops(1),minis:ops(2),
    conta:document.querySelector('.treino-montar-count').textContent};}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(ACERVO)
        await page.evaluate("()=>{treinoFiltro={materia:'',chefao:'',assunto:'',formato:'',estado:'',nivel:''};showScreen('simgeral');renderSimGeralScreen();return true;}")

        print('=== A) três seletores: Reino, Chefão, Miniboss ===')
        r=await page.evaluate(LER)
        print('   %s'%r)
        assert r['rotulos']==['Reino','Chefão','Miniboss'] and r['conta']=='12 questões'
        assert r['chefoes'][1:]==['Saúde da Criança','Saúde da Mulher','Sintaxe'], 'chefão sai da árvore (Antigo não aparece)'
        print('   OK\n')

        print('=== B) reino limita chefões; chefão limita minibosses e a contagem ===')
        r=await page.evaluate("""()=>{treinoFiltroMudou('materia','Enfermagem');return true;}""")
        r=await page.evaluate(LER)
        assert r['chefoes'][1:]==['Saúde da Criança','Saúde da Mulher'] and r['conta']=='9 questões'
        await page.evaluate("()=>treinoFiltroMudou('chefao','t1')")
        r=await page.evaluate(LER)
        print('   %s'%r)
        assert r['minis'][1:]==['Pré-natal','Puerpério'] and r['conta']=='6 questões'
        print('   OK\n')

        print('=== C) Treinar com só o chefão: sessão com o chefão inteiro e título dele ===')
        r=await page.evaluate("""()=>{treinoFiltroTreinar();const s=treinoSessao;
          return {n:s.itens.length,subs:[...new Set(s.itens.map(q=>q.subId))].sort(),titulo:s.titulo};}""")
        print('   %s'%r)
        assert r=={'n':6,'subs':['s1','s2'],'titulo':'Chefão · Saúde da Mulher'}
        print('   OK\n')

        print('=== D) miniboss dentro do chefão; trocar o reino limpa chefão e miniboss ===')
        r=await page.evaluate("""()=>{treinoSessao=null;treinoResumo=null;renderSimGeralScreen();
          treinoFiltroMudou('assunto','s2');const n1=treinoFiltroAplicar().length;
          treinoFiltroMudou('materia','Português');
          return {n1,f:{...treinoFiltro},n2:treinoFiltroAplicar().length};}""")
        print('   %s'%r)
        assert r['n1']==3 and r['f']['chefao']=='' and r['f']['assunto']=='' and r['n2']==3
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
