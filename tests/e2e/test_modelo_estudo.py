import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

# conta do LEO: cheia de conteudo E de progresso/segredos
LEO=make_seed({'studyNickname':'Leo','accountEmail':'leo@ex.com','plan':'full','planType':'anual',
  'lastPaymentAt':1800000000000,'onboardingCompleted':True,'xp':31998,'lifetimeSeconds':360000,
  'examDate':'2026-11-01','longestStreak':42,
  'geminiApiKey':'AIzaSyMINHA_CHAVE_SECRETA_123','tavilyApiKey':'tvly-SEGREDO456',
  'times':{'s1':7200},'revisions':{'s1':[{'date':'2026-09-20','completed':False}]},
  'flashcards':{'f1':{'id':'f1','mbId':'t1','pergunta':'O que e SAE?','resposta':'Sistematizacao.',
                      'tags':'sae','dificuldade':3,'acertos':9,'erros':1,'lastConf':4,
                      'ultimaRevisao':'2026-09-10T10:00:00Z','dominado':True,
                      'sm2':{'ef':2.8,'reps':5,'interval':90},'criacao':'2026-01-01T00:00:00Z'}},
  'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#6c47ff'}],
  'topics':{'k1':[{'id':'t1','name':'Saúde Mental','icon':'🧠','priority':3,'subtopics':[
     {'id':'s1','name':'Esquizofrenia','priority':100,'studied':True,'studiedAt':'2026-09-01',
      'sm2':{'ef':2.7,'reps':3,'interval':45},'revMastered':True,'note':'minha anotacao',
      'resumo':{'texto':'Resumo completo da esquizofrenia.','grounded':True,'via':'tavily',
                'fontes':[{'url':'https://x.gov.br','titulo':'Fonte'}],'geradoEm':'2026-09-01T10:00:00Z'},
      'fluxograma':{'raizId':'a','nos':{'a':{'texto':'Início','tipo':'inicio','ramos':[]}},
                    'origem':'ia','fontes':[],'geradoEm':'2026-09-01T11:00:00Z'}}]}]},
  'editais':[{'id':'e1','nome':'SESAU-RO','cargo':'Enfermeiro','banca':'CEBRASPE','data':'2026-11-01',
              'icon':'🏥','color':'#6c47ff','status':'inscrito','createdAt':'2026-09-01',
              'disciplinas':[{'id':'d1','nome':'Enfermagem','questoes':40,
                              'assuntos':[{'id':'a1','nome':'SAE','subId':'s1','prev':2}]}]}]})

# conta da AMIGA: ja tem coisa propria, que nao pode sumir
AMIGA=make_seed({'studyNickname':'Bia','accountEmail':'bia@ex.com','plan':'trial','xp':120,
  'onboardingCompleted':True,
  'flashcards':{'fb':{'id':'fb','mbId':'tb','pergunta':'Card da Bia','resposta':'R','tags':'',
                      'dificuldade':2,'acertos':2,'erros':0,'lastConf':3,'criacao':'2026-09-01T00:00:00Z'}},
  'kingdoms':[{'id':'kb','name':'Reino da Bia','icon':'🌸'}],
  'topics':{'kb':[{'id':'tb','name':'Chefao da Bia','icon':'🌷','priority':1,'subtopics':[
      {'id':'sb','name':'Assunto da Bia','priority':70,'studied':True}]}]}})

PROIBIDO=['AIzaSyMINHA_CHAVE_SECRETA_123','tvly-SEGREDO456','leo@ex.com','31998','lastPaymentAt',
          'revMastered','longestStreak','lifetimeSeconds']

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,LEO)
        txt=await page.evaluate("""async()=>{
            // captura o Blob na origem: a URL e revogada logo depois do clique
            let blob=null; const _co=URL.createObjectURL.bind(URL);
            URL.createObjectURL=function(b){blob=b;return _co(b);};
            const _c=document.createElement.bind(document);
            document.createElement=function(t){const e=_c(t);
              if(t==='a')e.click=function(){};
              return e;};
            exportarModeloEstudo();
            document.createElement=_c; URL.createObjectURL=_co;
            return blob?await blob.text():null;}""")
        await b.close()

    m=json.loads(txt)
    print('--- ARQUIVO EXPORTADO (%d KB)'%(len(txt)//1024 or 1))
    print('    resumo:',m['resumo'])
    print()
    print('--- o que NAO pode estar no arquivo')
    vaz=[x for x in PROIBIDO if x in txt]
    for x in PROIBIDO:
        print('    %-32s %s'%(x, 'VAZOU!' if x in txt else 'ok, fora'))
    campos=set()
    def anda(o):
        if isinstance(o,dict):
            for k,v in o.items(): campos.add(k); anda(v)
        elif isinstance(o,list):
            for v in o: anda(v)
    anda(m)
    ruins=campos&{'sm2','acertos','erros','lastConf','ultimaRevisao','dominado','studied',
                  'studiedAt','revisions','times','xp','geminiApiKey','plan','revMastered'}
    print('    campos de progresso no arquivo: %s'%(sorted(ruins) or 'nenhum'))
    print()
    print('    conteúdo presente: resumo=%s fluxograma=%s note=%s flashcard=%s edital=%s'%(
        'resumo' in str(m['topics']), 'fluxograma' in str(m['topics']), 'note' in str(m['topics']),
        len(m['flashcards']), len(m['editais'])))

    # agora importa na conta da Bia
    async with async_playwright() as p2:
        b2,page2,errs2=await setup_page(p2,AMIGA)
        antes=await page2.evaluate("()=>({reinos:db.kingdoms.map(k=>k.name),cards:Object.keys(db.flashcards).length,xp:db.xp})")
        await page2.evaluate("""(txt)=>{
            window.confirm=()=>true;
            const f=new File([txt],'m.json',{type:'application/json'});
            const dt=new DataTransfer(); dt.items.add(f);
            const inp=document.createElement('input'); inp.type='file';
            Object.defineProperty(inp,'files',{value:dt.files});
            importarModeloArquivo(inp);}""",txt)
        await page2.wait_for_timeout(900)
        dep=await page2.evaluate("""()=>{
            const s1=simFindSub('s1');
            return {reinos:db.kingdoms.map(k=>k.name),cards:Object.keys(db.flashcards).length,
                    xp:db.xp, chave:db.geminiApiKey||null, plano:db.plan, nick:db.studyNickname,
                    prova:db.examDate||null,
                    s1:s1?{nome:s1.name,studied:!!s1.studied,temResumo:!!(s1.resumo&&s1.resumo.texto),
                           temFluxo:!!(s1.fluxograma),sm2:s1.sm2||null}:null,
                    revS1:(db.revisions&&db.revisions.s1)||null,
                    cardSAE:Object.values(db.flashcards).filter(c=>c.pergunta==='O que e SAE?')
                            .map(c=>({ac:c.acertos,dom:!!c.dominado,sm2:c.sm2||null}))[0]||null,
                    cardBia:!!Object.values(db.flashcards).find(c=>c.pergunta==='Card da Bia'),
                    editais:(db.editais||[]).map(e=>e.nome)};}""")
        print('\n--- IMPORTOU NA CONTA DA BIA')
        print('    reinos antes : %s'%antes['reinos'])
        print('    reinos depois: %s   (o dela tem que continuar)'%dep['reinos'])
        print('    card da Bia sobreviveu: %s'%dep['cardBia'])
        print('    cards: %d -> %d'%(antes['cards'],dep['cards']))
        print()
        print('    chave de IA do Leo veio junto? %s   (tem que ser None)'%dep['chave'])
        print('    plano da Bia: %s   (não pode ter virado full)'%dep['plano'])
        print('    XP da Bia: %s -> %s   (não pode ter virado 31998)'%(antes['xp'],dep['xp']))
        print('    apelido: %s   | data da prova: %s'%(dep['nick'],dep['prova']))
        print()
        print('    miniboss importado: %s'%dep['s1'])
        print('    revisões herdadas para s1: %s   (tem que ser None)'%dep['revS1'])
        print('    card SAE: %s   (acertos 0, sem sm2, não dominado)'%dep['cardSAE'])
        print('    editais: %s'%dep['editais'])
        print('\nerros: %s'%[e for e in errs2 if 'selectedPixTier' not in e])
        await b2.close()
asyncio.run(main())
