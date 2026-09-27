# Pedindo "o nome mais especifico possivel", a IA devolveu 120 assuntos diferentes, um
# por questao — 120 seletores pra resolver a mao. A lista fechada conserta isso.
# colar prova e o banco mudaram de painel (aba Minhas Provas); o teste olha os dois
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

K1='k1'; K2='k2'

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':K1,'name':'Enfermagem','icon':'💉','color':'#e11d48'},
                  {'id':K2,'name':'Portugues','icon':'📖','color':'#3b82f6'}],
      'topics':{
        K1:[{'id':'t1','name':'Legislacao','icon':'⚔️','subtopics':[
              {'id':'lei','name':'Lei 7.498/1986','priority':70,'studied':True,'studiedAt':'2026-01-01'},
              {'id':'naoest','name':'Assunto nao estudado','priority':70,'studied':False}]}],
        K2:[{'id':'t2','name':'Gramatica','icon':'⚔️','subtopics':[
              {'id':'reg','name':'Regencia','priority':70,'studied':True,'studiedAt':'2026-01-01'},
              {'id':'crase','name':'Crase','priority':70,'studied':True,'studiedAt':'2026-01-01'},
              {'id':'pont','name':'Pontuacao','priority':70,'studied':True,'studiedAt':'2026-01-01'}]}]}})

def item(idx,nome,texto,g='C'):
    return {"assunto":idx,"assuntoNome":nome,"textoApoio":"",
            "afirmacao":texto,"gabarito":g,"explicacao":"..."}

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('simgeral');return true;}")

        print('=== A) o prompt leva a lista numerada, so dos estudados ===')
        r=await page.evaluate("""()=>{const t=simColarPromptTexto();
          return {lista:simColarLista.map(c=>c.sub.name),
            temLista:t.indexOf('ASSUNTOS — LISTA FECHADA')>=0,
            numerado:t.indexOf('1. Lei 7.498/1986 (Enfermagem / Legislacao)')>=0,
            naoEstudado:t.indexOf('Assunto nao estudado')>=0,
            proibeInventar:t.indexOf('NÃO invente assunto fora da lista')>=0,
            doisCampos:t.indexOf('"assuntoNome"')>=0};}""")
        print('   lista no prompt: %s'%r['lista'])
        for k,v in r.items():
            if k!='lista': print('   %-14s %s'%(k,v))
        assert r['temLista'] and r['numerado'] and r['proibeInventar'] and r['doisCampos']
        assert not r['naoEstudado'] and len(r['lista'])==4
        print('   OK\n')

        print('=== B) 120 questoes por NUMERO viram poucas linhas, nao 120 ===')
        lote=[]
        nomes={1:'Lei 7.498/1986',2:'Regencia',3:'Crase',4:'Pontuacao'}
        for i in range(120):
            idx=(i%4)+1
            lote.append(item(idx,nomes[idx],'Item %d sobre %s.'%(i+1,nomes[idx]),'C' if i%2 else 'E'))
        r=await page.evaluate("""(txt)=>{document.getElementById('sg-colar-txt').value=txt;
          simColarAdicionar();
          const m=simColarMapa();
          return {lote:simColarLote.length,linhas:m.grupos.length,
                  grupos:m.grupos.map(g=>[g.n,g.alvo?g.alvo.sub.name:null]),
                  pend:m.grupos.filter(g=>!g.alvo).length};}""",json.dumps(lote,ensure_ascii=False))
        print('   %s questoes -> %s linhas na tela'%(r['lote'],r['linhas']))
        for n,alvo in r['grupos']: print('     %3d× -> %s'%(n,alvo))
        assert r['lote']==120 and r['linhas']==4 and r['pend']==0
        print('   OK\n')

        print('=== C) numero fora da lista cai no nome copiado ===')
        r=await page.evaluate("""(txt)=>{window.confirm=()=>true;simColarLimpar();
          document.getElementById('sg-colar-txt').value=txt;
          simColarAdicionar();
          const m=simColarMapa();
          return m.grupos.map(g=>[g.n,g.alvo?g.alvo.sub.name:g.nome]);}""",
          json.dumps([item(99,'Crase','Item com numero errado.'),
                      item(98,'Regencia nominal','Outro com numero errado.'),
                      item(97,'Semantica do verbo haver','Assunto que nao existe.')],ensure_ascii=False))
        for n,alvo in r: print('     %d× -> %s'%(n,alvo))
        d=dict((x[1],x[0]) for x in r)
        assert 'Crase' in d and 'Regencia' in d and 'Semantica do verbo haver' in d
        print('   OK\n')

        print('=== D) a linha resolvida mostra os nomes que a IA usou ===')
        r=await page.evaluate("""()=>{const t=(document.getElementById('provas-content').innerText+document.getElementById('simgeral-content').innerText);
          return {reg:t.indexOf('Regencia nominal')>=0,
                  contador:(t.match(/\\d+ questões no lote[^\\n]*/)||[''])[0]};}""")
        print('   %s'%r['contador'])
        print('   mostra o nome original da IA: %s'%r['reg'])
        assert r['reg'] and 'sem assunto' in r['contador']
        print('   OK\n')

        print('=== E) "Começar sem elas" descarta so as pendentes ===')
        r=await page.evaluate("""()=>{simColarIniciar();
          const travou=!simGeralActive;
          simColarIniciar(true);
          const a=simGeralActive;
          return {travou,n:a?a.questoes.length:0,
                  assuntos:a?a.questoes.map(q=>q.subName):[]};}""")
        print('   travou sem descartar: %s'%r['travou'])
        print('   começou com %s de 3 · %s'%(r['n'],sorted(set(r['assuntos']))))
        assert r['travou'] and r['n']==2 and 'Semantica do verbo haver' not in r['assuntos']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
