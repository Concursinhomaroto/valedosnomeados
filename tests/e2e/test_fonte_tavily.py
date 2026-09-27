# -*- coding: utf-8 -*-
# 1a versao: o Tavily buscava e o trecho ia direto pra tela. Na prova real saiu menu de
# portal, markdown de gif de "loading" e resumo de artigo sobre outro assunto — porque
# raw_content e a PAGINA inteira, nao o texto dela. Agora sao tres peneiras: limpar o
# que nao e paragrafo (de graca), jogar fora a pagina que nao fala do item (de graca) e
# so entao o modelo ESCOLHER qual dos poucos que sobraram serve. Escrever, ele nao
# escreve: o que aparece na tela continua sendo o texto da pagina.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
from test_banco_provas import LOTE

def seed():
    return make_seed({'studyNickname':'Leo','tavilyApiKey':'tvly-teste','geminiApiKey':'chave-de-teste',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
      'topics':{'k1':[{'id':'t1','name':'Urgencia','icon':'⚔️','subtopics':[
          {'id':'s1','name':'Choque septico','priority':70,'studied':True},
          {'id':'s2','name':'PCR','priority':70,'studied':True}]}]}})

# O lixo abaixo e copiado da tela que o usuario mandou: menu da BVS, gif de loading,
# linha de "Title:", consulta publica do Cofen. Nada disso pode chegar na tela de novo.
LIXO = "\n".join([
    r"![loading](/assets/regional/image/loading-pZGfrzW.gif) [Conteudo principal 1](#main_container) "
    r"[Busca 2](#pesquisa) [Rodape 3](#footer) [+A](#) [A](#) [-A](#) [Alto contraste](#) "
    r"[!](/assets/regional/image/pt/logo.svg)(http://bvsalud.org/) Portal Regional da BVS",
    r"Title: Brasil - A regulacao das relacoes de trabalho e o gerenciamento de recursos humanos",
    r"#### Consulta Encerrada A consulta publica do documento **REFERENCIAL TEORICO** "
    r"encontra-se fora do periodo de contribuicao! [Propor novo artigo](/cofen/30/propor)",
    r"* portugues * espanol * english * francais",
    ""])

BOM1 = ("O choque septico e definido como a sepse associada a disfuncao circulatoria e celular, "
        "em que o paciente persiste com hipotensao exigindo vasopressor para manter a pressao "
        "arterial media acima de 65 mmHg e apresenta lactato serico acima de 2 mmol por litro "
        "mesmo apos reposicao volemica adequada, condicao que eleva a mortalidade hospitalar.")
BOM2 = ("Na abordagem inicial do choque septico, recomenda-se a administracao de 30 mL por "
        "quilo de cristaloide nas primeiras tres horas, coleta de culturas antes do "
        "antimicrobiano e inicio do antibiotico de amplo espectro na primeira hora do "
        "reconhecimento do quadro, com reavaliacao frequente da perfusao tecidual.")
OUTRO = ("A negociacao integrativa no gerenciamento de recursos humanos em enfermagem busca "
         "ampliar os ganhos das partes envolvidas, diferentemente da negociacao distributiva, "
         "na qual o ganho de um lado corresponde a perda do outro lado da mesa de trabalho.")

MOCK = ("""()=>{
  window.__buscas=[]; window.__peneiras=[]; window.__escolha=[{i:0}];
  const LIXO=%s, BOM1=%s, BOM2=%s, OUTRO=%s;
  window.__paginas=[
    {url:'https://www.gov.br/saude/sepse',titulo:'Sepse e choque septico | Ministerio da Saude',
     corpo:LIXO+BOM1},
    {url:'https://bvsalud.org/portal',titulo:'Conflicts and resolution strategies | Nursing',
     corpo:LIXO},
    {url:'https://www.scielo.br/choque',titulo:'Manejo inicial do choque <b>septico</b>',
     corpo:BOM2},
    {url:'https://www.gov.br/saude/sepse',titulo:'duplicata',corpo:BOM1},
    {url:'https://exemplo.org/rh',titulo:'Negociacao em enfermagem',corpo:OUTRO}];
  window.tavilyBuscar=async(consulta,opts)=>{
    window.__buscas.push({consulta,opts});
    if(window.__falhar)throw new Error('432 cota estourada');
    const fs=window.__paginas.filter(p=>!(opts&&opts.oficial)||/gov\\.br|planalto/.test(p.url));
    return {fontes:fs.map(p=>({url:p.url,titulo:p.titulo})),
            texto:fs.map((p,i)=>`[FONTE ${i+1}] ${p.titulo}\\nURL: ${p.url}\\n${p.corpo}`)
                    .join('\\n\\n---\\n\\n')};
  };
  window.callGeminiJSON=async(key,prompt,useSearch,maxOut)=>{
    window.__peneiras.push({prompt,useSearch,maxOut});
    if(window.__peneiraFalha)throw new Error('503 sobrecarregado');
    return {json:window.__escolha};
  };
  window.confirm=()=>true;
  return true;}""" % (json.dumps(LIXO),json.dumps(BOM1),json.dumps(BOM2),json.dumps(OUTRO)))

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('provas');return true;}")
        await page.evaluate(MOCK)

        print('=== A) a consulta leva a norma na frente e palavra cheia, nao rodeio ===')
        r=await page.evaluate("""()=>{
          const q={subName:'Lei 8.080',questao:'De acordo com a Lei n.º 8.080/1990 e com a Resolução Cofen 564/2017, '
            +'julgue o item seguinte: a integralidade é entendida como conjunto articulado de ações '
            +'preventivas e curativas exigidas para cada caso em todos os níveis de complexidade.'};
          const c=fonteConsulta(q), t=fonteTermos(q);
          return {c,tam:c.length,termos:t,
                  leiAntes:c.indexOf('8.080')>-1&&c.indexOf('8.080')<c.indexOf('integralidade'),
                  semRodeio:!/acordo|julgue|seguinte/.test(c.split('Cofen 564/2017')[1]||c)};}""")
        print('   consulta: %s'%r['c'])
        print('   termos do item: %s'%(', '.join(r['termos'][:8])))
        assert r['leiAntes'] and r['tam']<=300
        assert 'julgue' not in r['termos'] and 'acordo' not in r['termos'] and 'seguinte' not in r['termos']
        assert 'integralidade' in r['termos'] and '8.080/1990' in r['termos']
        print('   "julgue", "de acordo", "seguinte" ficaram de fora; a lei e o conceito entraram')
        print('   OK\n')

        print('=== B) o lixo da pagina nao passa (a tela que voce mandou) ===')
        r=await page.evaluate("""(lixo)=>{
          const paras=fonteLimparCorpo(lixo);
          return {sobrou:paras, n:paras.length};}""", LIXO)
        print('   linhas que sobraram do menu da BVS: %s'%r['n'])
        assert r['n']==0, r['sobrou']
        print('   gif de loading, breadcrumb, "Title:", lista de idiomas, "Propor novo artigo": nada passou')
        print('   OK\n')

        print('=== C) pagina que nao fala do item e descartada inteira ===')
        r=await page.evaluate("""async(x)=>{
          (%s)(6);
          simColarIniciar(false);
          simGeralActive.questoes.forEach((q,i)=>{q.userAnswer=(i<3)?(q.correta==='C'?'E':'C'):q.correta;});
          simGeralActive.tempoGastoSec=200; simGeralCorrigir();
          await new Promise(r=>setTimeout(r,300));
          provaRevisar(db.provas[0].id);
          const q=simGeralActive.questoes[0];
          const termos=fonteTermos(q);
          const cands=await fonteCandidatos(q,termos,false);
          return {termos,minimo:fonteNotaMinima(termos),
                  urls:cands.map(c=>c.url), notas:cands.map(c=>c.nota),
                  trechos:cands.map(c=>c.trecho.slice(0,60))};}"""%LOTE,0)
        print('   termos: %s · nota mínima: %s'%(r['termos'],r['minimo']))
        for u,n in zip(r['urls'],r['notas']): print('   ficou: %s (nota %s)'%(u,n))
        assert 'https://bvsalud.org/portal' not in r['urls'], 'a página só de menu passou'
        assert 'https://exemplo.org/rh' not in r['urls'], 'página de outro assunto passou'
        assert len(r['urls'])==2 and len(set(r['urls']))==2
        print('   BVS (só menu) e a de negociação em RH: fora. Sobraram as 2 que falam do item')
        print('   OK\n')

        print('=== D) o modelo ESCOLHE, nao escreve ===')
        r=await page.evaluate("""async()=>{
          db.tavilySoOficial=false;      // no fixture, só-oficial deixa 1 candidato e a peneira nem roda
          window.__peneiras=[]; window.__escolha=[{i:1}];
          await fonteBuscar(0);
          const pe=window.__peneiras[0];
          const t=simGeralActive.questoes[0].apoioWeb[0];
          const pagina=window.__paginas.find(p=>p.url===t.url);
          return {chamadas:window.__peneiras.length, tamPrompt:pe.prompt.length, maxOut:pe.maxOut,
                  busca:pe.useSearch,
                  mandaEscolher:pe.prompt.includes('ESCOLHER, não escrever'),
                  proibeReescrever:pe.prompt.includes('não reescreva nem resuma'),
                  aceitaVazio:pe.prompt.includes('vazio é melhor do que trecho errado'),
                  indices:/\\[0\\][\\s\\S]*\\[1\\]/.test(pe.prompt),
                  semPaginaInteira:!pe.prompt.includes('loading-pZGfrzW'),
                  n:simGeralActive.questoes[0].apoioWeb.length,
                  literal:pagina.corpo.indexOf(t.trecho.replace(/…$/,''))>=0};}""")
        print('   1 chamada · prompt com %s chars · teto de saída: %s tokens · busca própria: %s'
              %(r['tamPrompt'],r['maxOut'],r['busca']))
        assert r['chamadas']==1 and r['tamPrompt']<3000 and r['maxOut']<=240 and not r['busca']
        assert r['mandaEscolher'] and r['proibeReescrever'] and r['aceitaVazio'] and r['indices']
        assert r['semPaginaInteira'], 'a página crua foi parar no prompt'
        print('   manda escolher, proíbe reescrever, aceita resposta vazia: ok')
        print('   página crua NÃO vai no prompt — só os candidatos já cortados: ok')
        print('   trecho que ficou na tela é literal, igual ao da página: %s'%r['literal'])
        assert r['literal'] and r['n']==1
        print('   OK\n')

        print('=== E) se nenhum trecho serve, ele devolve vazio — e a tela nao mente ===')
        r=await page.evaluate("""async()=>{
          fonteLimpar(0); window.__escolha=[];
          await fonteBuscar(0);
          return {n:(simGeralActive.questoes[0].apoioWeb||[]).length,
                  html:fonteApoioHTML(simGeralActive.questoes[0],0)};}""")
        print('   trechos na tela: %s · bloco renderizado: %s'
              %(r['n'],'nenhum' if not r['html'] else 'sim'))
        assert r['n']==0 and r['html']==''
        print('   nada na tela é melhor do que trecho errado na tela')
        print('   OK\n')

        print('=== F) peneira que falha nao derruba a busca: vale o ranking mecanico ===')
        r=await page.evaluate("""async()=>{
          window.__escolha=[{i:0}]; window.__peneiraFalha=true;
          await fonteBuscar(0);
          window.__peneiraFalha=false;
          const a=simGeralActive.questoes[0].apoioWeb||[];
          return {n:a.length, ordenado:a.length<2||true};}""")
        print('   Gemini fora do ar · trechos entregues mesmo assim: %s'%r['n'])
        assert r['n']==2
        print('   sem o modelo, entra o ranking por palavra do item — não fica sem nada')
        print('   OK\n')

        print('=== G) busca so em lote; sem Gemini so o mecanico; sem Tavily, nada ===')
        r=await page.evaluate("""async()=>{
          const g=db.geminiApiKey; db.geminiApiKey='';
          fonteLimpar(0); window.__peneiras=[];
          await fonteBuscar(0);
          const semGemini=(simGeralActive.questoes[0].apoioWeb||[]).length;
          const peneiras=window.__peneiras.length;
          db.geminiApiKey=g;
          const com=simGeralResultsHTML();
          const k=db.tavilyApiKey; db.tavilyApiKey='';
          const sem=simGeralResultsHTML();
          window.__buscas=[];
          await fonteBuscar(0);
          db.tavilyApiKey=k;
          return {semGemini,peneiras,
                  comBotao:(com.match(/fonteBuscar\\(/g)||[]).length,
                  comLote:com.includes('fonteBuscarErradas()'),
                  semBotao:(sem.match(/fonteBuscar\\(/g)||[]).length,
                  semLote:sem.includes('fonteBuscarErradas()'),
                  buscas:window.__buscas.length};}""")
        print('   sem Gemini: %s trechos, %s chamadas ao modelo'%(r['semGemini'],r['peneiras']))
        print('   botão por questão: %s (foi removido) · botão em lote: %s'
              %(r['comBotao'],r['comLote']))
        print('   sem Tavily: lote some (%s) · buscas disparadas: %s'%(r['semLote'],r['buscas']))
        assert r['semGemini']==2 and r['peneiras']==0
        assert r['comBotao']==0 and r['comLote'] and not r['semLote'] and r['buscas']==0
        print('   OK\n')

        print('=== H) so em site oficial nao achou? uma segunda passada, aberta ===')
        r=await page.evaluate("""async()=>{
          db.tavilySoOficial=true;
          window.__paginas=window.__paginas.map(p=>({...p,url:p.url.replace('www.gov.br','site.org')}));
          fonteLimpar(0); window.__buscas=[]; window.__escolha=[{i:0}];
          const res=await fonteDaQuestao(simGeralActive.questoes[0]);
          const so=window.__buscas.map(b=>!!(b.opts&&b.opts.oficial));
          db.tavilySoOficial=false;
          return {passadas:window.__buscas.length,oficial:so,ampliou:res.ampliou,
                  achados:res.achados.length};}""")
        print('   passadas: %s (só-oficial: %s) · ampliou: %s · achados: %s'
              %(r['passadas'],r['oficial'],r['ampliou'],r['achados']))
        assert r['passadas']==2 and r['oficial']==[True,False] and r['ampliou'] and r['achados']>=1
        print('   a 1ª restrita voltou vazia, a 2ª aberta achou — e o aviso diz que saiu do oficial')
        print('   OK\n')

        print('=== I) em lote, so nas erradas e so nas que ainda nao tem fonte ===')
        r=await page.evaluate("""async()=>{
          const q=simGeralActive.questoes;
          q.forEach(x=>{x.apoioWeb=[];});
          q[1].apoioWeb=[{titulo:'t',url:'u',trecho:'x'}];
          q[2].motivo='datado';
          window.__buscas=[];
          await fonteBuscarErradas();
          return {buscas:window.__buscas.length,
                  q0:(q[0].apoioWeb||[]).length,q1:(q[1].apoioWeb||[]).length,
                  q2:(q[2].apoioWeb||[]).length,
                  certas:q.slice(3).filter(x=>(x.apoioWeb||[]).length).length};}""")
        print('   3 erradas, %s busca: a 2ª já tinha fonte, a 3ª está fora da conta'%r['buscas'])
        assert r['buscas']==1 and r['q0']>=1 and r['q1']==1 and r['q2']==0 and r['certas']==0
        print('   OK\n')

        print('=== J) HTML da web entra escapado, link abre fora ===')
        r=await page.evaluate("""async()=>{
          const q=simGeralActive.questoes; q[2].motivo=''; fonteLimpar(0);
          window.__escolha=[{i:0},{i:1}];
          await fonteBuscar(0);
          const h=fonteApoioHTML(q[0],0);
          return {n:(q[0].apoioWeb||[]).length,
                  noopener:(h.match(/rel="noopener noreferrer"/g)||[]).length,
                  blank:(h.match(/target="_blank"/g)||[]).length,
                  bCru:h.includes('<b>septico</b>'),escapado:h.includes('&lt;b&gt;'),
                  limpar:h.includes('fonteLimpar(0)'),
                  aviso:h.includes('ninguém reescreveu')};}""")
        print('   %s trechos · target=_blank: %s · rel=noopener: %s'%(r['n'],r['blank'],r['noopener']))
        print('   <b> cru da web na página: %s · escapado: %s'%(r['bCru'],r['escapado']))
        assert r['n']==2 and r['noopener']==2 and r['blank']==2
        assert not r['bCru'] and r['escapado'] and r['limpar'] and r['aviso']
        print('   OK\n')

        print('=== K) o trecho sobrevive a fechar e reabrir a prova ===')
        r=await page.evaluate("""()=>{
          const antes=(provaQuestoes(db.provas[0])[0].apoioWeb||[]).length;
          simGeralActive=null; provaRevisar(db.provas[0].id);
          const h=document.getElementById('simgeral-content').innerHTML;
          return {antes,depois:(simGeralActive.questoes[0].apoioWeb||[]).length,
                  naTela:h.includes('fonte-web')};}""")
        print('   na prova: %s · ao reabrir: %s · na tela: %s'%(r['antes'],r['depois'],r['naTela']))
        assert r['antes']>=1 and r['depois']==r['antes'] and r['naTela']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
