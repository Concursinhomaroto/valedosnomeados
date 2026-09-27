# Gerar simulado pela API custa cota. Com Gemini Pro da pra fazer prova ilimitada e com
# pesquisa — faltava a porta de entrada. Itens reais da prova que o usuario gerou.
# colar prova e o banco mudaram de painel (aba Minhas Provas); o teste olha os dois
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

K1='k1'; K2='k2'; T1='t1'; T2='t2'; T3='t3'

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':K1,'name':'Enfermagem','icon':'💉','color':'#e11d48'},
                  {'id':K2,'name':'Portugues','icon':'📖','color':'#3b82f6'}],
      'topics':{
        K1:[{'id':T1,'name':'Legislacao','icon':'⚔️','subtopics':[
              {'id':'lei','name':'Lei 7.498/1986','priority':70,'studied':True,'studiedAt':'2026-01-01'}]},
            {'id':T2,'name':'Biosseguranca','icon':'⚔️','subtopics':[
              {'id':'prec','name':'Precaucoes de contato','priority':70,'studied':True,'studiedAt':'2026-01-01'},
              {'id':'este','name':'Esterilizacao em autoclave','priority':70,'studied':True,'studiedAt':'2026-01-01'}]}],
        K2:[{'id':T3,'name':'Gramatica','icon':'⚔️','subtopics':[
              {'id':'crase','name':'Crase','priority':70,'studied':True,'studiedAt':'2026-01-01'}]}]}})

APOIO=("A consolidacao das redes de atencao as urgencias exige nao apenas aporte continuo "
       "de infraestrutura tecnologica, mas a revisao substantiva dos fluxos de trabalho.")

# itens reais do arquivo do usuario, no formato que o prompt pede
LOTE1=[
 {"assunto":"Crase","assuntoNome":"Crase","textoApoio":APOIO,
  "afirmacao":"A insercao do sinal indicativo de crase e obrigatoria no segmento: O enfermeiro dedicou sua jornada a coordenar a equipe do plantao noturno.",
  "gabarito":"E","explicacao":"E proibido crase antes de verbo no infinitivo."},
 {"assunto":"Crase","assuntoNome":"Crase","textoApoio":APOIO,
  "afirmacao":"Em A enfermeira prestou assistencia a paciente que apresentava dor intensa, o acento grave e obrigatorio.",
  "gabarito":"C","explicacao":"Regencia de prestar + artigo definido feminino."},
 {"assunto":"Precaucoes de contato","assuntoNome":"Precaucoes de contato","textoApoio":"",
  "afirmacao":"As precaucoes de contato envolvem avental limpo nao esteril e luvas de procedimento.",
  "gabarito":"C","explicacao":"Diretrizes ANVISA/CDC."},
 {"assunto":"Esterilizacao em autoclave","assuntoNome":"Esterilizacao em autoclave","textoApoio":"",
  "afirmacao":"O teste biologico diario com esporos de Geobacillus stearothermophilus monitora a autoclave a vapor.",
  "gabarito":"C","explicacao":"Indicador biologico padrao do vapor sob pressao."},
 {"assunto":"Sondagem vesical","assuntoNome":"Sondagem vesical","textoApoio":"",
  "afirmacao":"A sondagem vesical de demora e privativa do Enfermeiro.",
  "gabarito":"C","explicacao":"Lei 7.498/1986."},
 # gabarito que nao bate: tem que ser descartada, nao contar como erro do usuario
 {"assunto":"Crase","assuntoNome":"Crase","questao":"Qual alternativa esta correta?",
  "alternativas":[{"letra":"A","texto":"uma"},{"letra":"B","texto":"outra"},{"letra":"C","texto":"mais"}],
  "correta":"Z","explicacao":"..."},
]
LOTE2=[
 {"assunto":"Lei 7.498/1986","assuntoNome":"Lei 7.498/1986","textoApoio":"",
  "afirmacao":"Cabe privativamente ao Enfermeiro o cuidado direto a pacientes graves com risco de vida.",
  "gabarito":"C","explicacao":"Art. 11."},
]

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('simgeral');return true;}")

        print('=== A) o prompt sai pronto, com as regras que a gente combinou ===')
        r=await page.evaluate("""()=>{const t=simColarPromptTexto();
          return {n:t.length,
            algarismo:t.indexOf('Todo número em ALGARISMO')>=0,
            competencia:t.indexOf('competência privativa')>=0,
            sonda:t.indexOf('privativa do Enfermeiro')>=0,
            pesquisa:t.indexOf('PESQUISE NA INTERNET')>=0,
            assunto:t.indexOf('LISTA FECHADA')>=0,
            apoio:t.indexOf('textoApoio')>=0,
            json:t.indexOf('"gabarito":"C"')>=0,
            semMarkdown:t.indexOf('Sem markdown')>=0,
            entrega:t.indexOf('feche o array')>=0,
            naoCorte:t.indexOf('Nunca corte no meio de um item')>=0,
            aspas:t.indexOf('Aspas duplas sem escape')>=0};}""")
        print('   %s caracteres'%r['n'])
        for k,v in r.items():
            if k!='n': print('   %-12s %s'%(k,v))
        assert all(v for k,v in r.items() if k!='n')
        print('   OK\n')

        print('=== B) colagem suja (preambulo + cerca ```json) entra mesmo assim ===')
        sujo="Claro! Aqui esta o simulado:\n\n```json\n"+json.dumps(LOTE1,ensure_ascii=False)+"\n```\nBons estudos!"
        r=await page.evaluate("""(txt)=>{document.getElementById('sg-colar-txt').value=txt;
          simColarAdicionar();
          return {lote:simColarLote.length,
                  formatos:simColarLote.map(q=>q.formato),
                  apoio:simColarLote[0].textoApoio,
                  txtBox:document.getElementById('sg-colar-txt').value};}""",sujo)
        print('   no lote: %s (1 descartada por gabarito Z)'%r['lote'])
        print('   texto de apoio preservado: %s'%(r['apoio'][:40]+'...'))
        assert r['lote']==5 and set(r['formatos'])=={'certoerrado'}
        assert r['apoio'].startswith('A consolidacao') and r['txtBox']==''
        print('   OK\n')

        print('=== C) o mapa mostra onde cada assunto vai cair ===')
        r=await page.evaluate("""()=>{const m=simColarMapa();
          return m.grupos.map(g=>[g.nome,g.n,g.alvo?g.alvo.sub.name:null]);}""")
        for nome,n,alvo in r: print('   %2d× %-28s -> %s'%(n,nome,alvo))
        d=dict((x[0],x[2]) for x in r)
        assert d['Crase']=='Crase' and d['Precaucoes de contato']=='Precaucoes de contato'
        assert d['Esterilizacao em autoclave']=='Esterilizacao em autoclave'
        assert d['Sondagem vesical'] is None   # nao existe no cadastro
        print('   OK\n')

        print('=== D) assunto nao reconhecido trava a largada ===')
        r=await page.evaluate("""()=>{simColarIniciar();return simGeralActive;}""")
        print('   prova iniciada: %s'%(r is not None))
        assert r is None
        print('   OK\n')

        print('=== E) voce escolhe o miniboss a mao e destrava ===')
        r=await page.evaluate("""()=>{simColarEscolher('Sondagem vesical','lei');
          const m=simColarMapa();
          const g=m.grupos.find(x=>x.alvo&&x.alvo.sub.id==='lei');
          return {alvo:g?g.alvo.sub.name:null,nomesIA:g?g.nomesIA:[],
                  pend:m.grupos.filter(x=>!x.alvo).length};}""")
        print('   Sondagem vesical -> %s (agrupada em: %s) · pendentes: %s'
              %(r['alvo'],r['nomesIA'],r['pend']))
        assert r['alvo']=='Lei 7.498/1986' and 'Sondagem vesical' in r['nomesIA'] and r['pend']==0
        print('   OK\n')

        print('=== F) resposta cortada no meio de um item: resgata o que veio inteiro ===')
        inteiros=json.dumps(LOTE1[:3],ensure_ascii=False)
        cortado=inteiros[:inteiros.rindex('},')+2]+'{"assunto":"Crase","assuntoNome":"Crase","afirmacao":"Este item foi cor'
        r=await page.evaluate("""(txt)=>{const antes=simColarLote.length;
          document.getElementById('sg-colar-txt').value=txt;
          simColarAdicionar();
          return {antes,depois:simColarLote.length,
                  aviso:(document.body.innerText.match(/veio cortada[^\\n]*/)||[''])[0]};}""",cortado)
        print('   lote %s -> %s (aproveitou os 2 itens completos)'%(r['antes'],r['depois']))
        print('   aviso: %r'%r['aviso'][:80])
        assert r['depois']-r['antes']==2 and 'último item completo' in r['aviso']
        print('   OK\n')

        print('=== F2) lixo sem JSON nenhum nao entra ===')
        r=await page.evaluate("""()=>{const antes=simColarLote.length;
          document.getElementById('sg-colar-txt').value='Claro! Vou gerar o simulado agora.';
          simColarAdicionar();
          return {antes,depois:simColarLote.length};}""")
        print('   lote %s -> %s'%(r['antes'],r['depois']))
        assert r['antes']==r['depois']
        print('   OK\n')

        print('=== F3) barra de progresso e o pedido do resto ===')
        r=await page.evaluate("""()=>{
          document.getElementById('sg-colar-qtd').value='120';
          simColarCopiarPrompt();
          const html=(document.getElementById('provas-content').innerHTML+document.getElementById('simgeral-content').innerHTML);
          const txt=(document.getElementById('provas-content').innerText+document.getElementById('simgeral-content').innerText);
          return {meta:simColarMeta,lote:simColarLote.length,
                  progresso:(txt.match(/\\d+ de 120 itens/)||[''])[0],
                  faltando:(txt.match(/\\d+ faltando/)||[''])[0],
                  botao:html.indexOf('simColarCopiarContinuar')>=0,
                  cont:simColarPromptContinuar()};}""")
        print('   meta %s · %s · %s'%(r['meta'],r['progresso'],r['faltando']))
        print('   botao "Pedir o resto": %s'%r['botao'])
        assert r['meta']==120 and r['progresso'] and r['faltando'] and r['botao']
        assert 'NÃO repita nenhum item' in r['cont'] and str(120-r['lote']) in r['cont']
        print('   prompt de continuacao cita os ultimos enviados: %s'
              %('Precaucoes' in r['cont'] or 'enfermeiro' in r['cont'].lower()))
        print('   OK\n')

        print('=== G) segunda colagem SOMA no lote ===')
        r=await page.evaluate("""(txt)=>{document.getElementById('sg-colar-txt').value=txt;
          simColarAdicionar();return simColarLote.length;}""",json.dumps(LOTE2,ensure_ascii=False))
        print('   lote: %s (5 + 2 resgatados + 1)'%r); assert r==8
        print('   OK\n')

        print('=== H) a prova comeca como Simulado Geral, com reino/chefao certos ===')
        r=await page.evaluate("""()=>{
          document.getElementById('sg-colar-tempo').value='120';
          simColarIniciar();
          const a=simGeralActive;
          return {n:a.questoes.length,limite:a.limiteSec,fmt:a.formato,importado:a.importado,
                  lote:simColarLote.length,
                  amostra:a.questoes.map(q=>[q.subName,q.kingdomName,q.topicName]),
                  apoioNaTela:(document.getElementById('provas-content').innerHTML+document.getElementById('simgeral-content').innerHTML).indexOf('sim-apoio')>=0};}""")
        print('   %s questoes · limite %ss · formato %s · importado %s'
              %(r['n'],r['limite'],r['fmt'],r['importado']))
        for a in r['amostra']: print('     %-28s %s · %s'%tuple(a))
        print('   texto de apoio renderizado: %s'%r['apoioNaTela'])
        assert r['n']==8 and r['limite']==7200 and r['fmt']=='certoerrado' and r['lote']==0
        assert r['apoioNaTela']
        assert ['Lei 7.498/1986','Enfermagem','Legislacao'] in r['amostra']
        assert ['Crase','Portugues','Gramatica'] in r['amostra']
        print('   OK\n')

        print('=== I) corrigir distribui pros minibosses e alimenta o Banco de Erros ===')
        r=await page.evaluate("""async()=>{
          const qs=simGeralActive.questoes;
          qs.forEach((q,i)=>{q.userAnswer=(i===0)?(q.correta==='C'?'E':'C'):q.correta;});
          const erradaEm=qs[0].subName;
          simGeralCorrigir();
          await new Promise(r=>setTimeout(r,400));
          const st={};
          ['lei','crase','prec','este'].forEach(id=>{const s=simFindSub(id);
            if(s&&s.simStats)st[s.name]=s.simStats.questoesTotal+'/'+s.simStats.acertosTotal;});
          return {erradaEm,st,banco:getErrorBank().length,
                  cards:Object.values(db.flashcards||{}).filter(c=>c.tags==='banco-de-erros').length};}""")
        print('   errei de proposito 1 questao de: %s'%r['erradaEm'])
        print('   simStats (questoes/acertos): %s'%r['st'])
        print('   Banco de Erros: %s · flashcards criados: %s'%(r['banco'],r['cards']))
        assert sum(int(v.split('/')[0]) for v in r['st'].values())==8
        assert r['banco']==1 and r['cards']==1
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
