# "Ocorreu medio, precisei colocar uns 25 miniboss." Resolver 25 nomes num seletor de
# 326 opcoes e caro — e na prova seguinte o mesmo trabalho se repetia inteiro.
# colar prova e o banco mudaram de painel (aba Minhas Provas); o teste olha os dois
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def subs(nomes,pref):
    return [{'id':pref+str(i),'name':n,'priority':70,'studied':True,'studiedAt':'2026-01-01'}
            for i,n in enumerate(nomes)]

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'},
                  {'id':'k2','name':'Portugues','icon':'📖'}],
      'topics':{
        'k1':[{'id':'t1','name':'Legislacao','icon':'⚔️','subtopics':subs(
                 ['Lei 7.498/1986','Codigo de Etica'],'e')}],
        'k2':[{'id':'t2','name':'Gramatica','icon':'⚔️','subtopics':subs(
                 ['Regencia','Crase','Pontuacao','Concordancia'],'p')}]}})

def item(nome,txt):
    return {"assunto":999,"assuntoNome":nome,"textoApoio":"","afirmacao":txt,
            "gabarito":"C","explicacao":"..."}

# nomes que a IA devolveu fora da lista — o caso real
LOTE=[item('Regencia nominal','Item 1.'),
      item('Regencia verbal do verbo preferir','Item 2.'),
      item('Concordancia verbal do verbo haver','Item 3.'),
      item('Prazos de recondução no servico publico','Item 4.')]

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('simgeral');return true;}")
        await page.evaluate("""()=>{simColarPromptTexto();return true;}""")

        print('=== A) nome fora da lista: o app sugere os 3 mais parecidos ===')
        r=await page.evaluate("""(txt)=>{document.getElementById('sg-colar-txt').value=txt;
          simColarAdicionar();
          const m=simColarMapa();
          return m.grupos.map(g=>[g.nome,g.alvo?g.alvo.sub.name:null,
            g.alvo?[]:simColarSugestoes(g.nome,m.ix,3).map(c=>c.sub.name)]);}""",
          json.dumps(LOTE,ensure_ascii=False))
        for nome,alvo,sug in r:
            print('   %-42s -> %s' % (nome, alvo or ('sugestões: '+', '.join(sug))))
        resolvidos=[x[1] for x in r if x[1]]
        # os nomes "inventados" da imagem real casam sozinhos, sem pendencia
        assert 'Regencia' in resolvidos and 'Concordancia' in resolvidos
        # o que sobra e assunto que de fato NAO existe no cadastro — sem palavra em comum
        # nao ha sugestao honesta a dar, e a linha cai no seletor
        pend=[x for x in r if not x[1]]
        assert len(pend)==1 and pend[0][0].startswith('Prazos de recondu')
        assert pend[0][2]==[], 'nao inventar sugestao sem nada em comum'
        print('   OK\n')

        print('=== B) os botoes de sugestao aparecem na tela ===')
        r=await page.evaluate("""()=>{
          // um nome que casa PARCIALMENTE: tem que virar botao de sugestao
          simColarLote.push({questao:'x',alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],
                             correta:'C',formato:'certoerrado',assunto:'Etica e sigilo profissional no exercicio',assuntoIdx:null});
          renderSimGeralScreen();
          const h=(document.getElementById('provas-content').innerHTML+document.getElementById('simgeral-content').innerHTML);
          const m=simColarMapa();
          const g=m.grupos.find(x=>!x.alvo&&x.nome.indexOf('sigilo')>=0);
          return {sug:g?simColarSugestoes(g.nome,m.ix,3).map(c=>c.sub.name):[],
                  botoes:(h.match(/simColarEscolher\\(/g)||[]).length,
                  outro:h.indexOf('— outro —')>=0};}""")
        print('   sugestões pro nome ambíguo: %s'%r['sug'])
        print('   %s botões/selects na tela · opção "outro": %s'%(r['botoes'],r['outro']))
        assert len(r['sug'])>=1 and 'Codigo de Etica' in r['sug'] and r['botoes']>=3 and r['outro']
        print('   OK\n')

        print('=== C) escolher grava o apelido no banco ===')
        r=await page.evaluate("""()=>{
          const m=simColarMapa();
          const pend=m.grupos.filter(g=>!g.alvo);
          // clique numa sugestao quando houver; no que nao tem, escolha pelo seletor
          pend.forEach(g=>{
            const s=simColarSugestoes(g.nome,m.ix,1)[0];
            simColarEscolher(g.nome,s?s.sub.id:'e0');
          });
          const m2=simColarMapa();
          return {apelidos:db.simColarApelidos,
                  pendAgora:m2.grupos.filter(g=>!g.alvo).length,
                  linhas:m2.grupos.length};}""")
        print('   apelidos gravados: %s'%json.dumps(r['apelidos'],ensure_ascii=False))
        print('   pendencias: %s · linhas na tela: %s'%(r['pendAgora'],r['linhas']))
        assert r['apelidos'] and r['pendAgora']==0
        print('   OK\n')

        print('=== D) na PROXIMA prova os mesmos nomes resolvem sozinhos ===')
        r=await page.evaluate("""(txt)=>{window.confirm=()=>true;
          simColarLimpar();                 // zera lote E escolhas da sessao
          document.getElementById('sg-colar-txt').value=txt;
          simColarAdicionar();
          const m=simColarMapa();
          return {escolhasNaSessao:Object.keys(simColarEscolhas).length,
                  pend:m.grupos.filter(g=>!g.alvo).length,
                  grupos:m.grupos.map(g=>[g.n,g.alvo?g.alvo.sub.name:g.nome])};}""",
          json.dumps(LOTE,ensure_ascii=False))
        print('   escolhas manuais desta sessao: %s (zeradas)'%r['escolhasNaSessao'])
        for n,alvo in r['grupos']: print('     %d× -> %s'%(n,alvo))
        assert r['escolhasNaSessao']==0 and r['pend']==0
        print('   OK\n')

        print('=== E) a tela conta quantos nomes ja foram aprendidos ===')
        r=await page.evaluate("""()=>{const t=(document.getElementById('provas-content').innerText+document.getElementById('simgeral-content').innerText);
          return (t.match(/Já aprendi \\d+ nome/)||[''])[0];}""")
        print('   %s'%r); assert 'aprendi' in r
        print('   OK\n')

        print('=== F) apelido apontando pra miniboss apagado nao quebra ===')
        r=await page.evaluate("""(txt)=>{
          db.simColarApelidos['assunto fantasma']='id_que_nao_existe';
          simColarLimpar();
          document.getElementById('sg-colar-txt').value=txt;
          simColarAdicionar();
          const m=simColarMapa();
          return {pend:m.grupos.filter(g=>!g.alvo).length,n:simColarLote.length};}""",
          json.dumps([item('Assunto fantasma','Item orfao.')],ensure_ascii=False))
        print('   lote %s · pendencias %s (cai no seletor, nao quebra)'%(r['n'],r['pend']))
        assert r['n']==1 and r['pend']==1
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
