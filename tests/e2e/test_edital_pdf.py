import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
seed=make_seed({'studyNickname':'Leo','plan':'full','geminiApiKey':'FAKE','onboardingCompleted':True,
  'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],'topics':{'k1':[]},
  'editais':[{'id':'e1','nome':'SESAU-RO','cargo':'Enfermeiro','banca':'CEBRASPE',
              'data':'2026-11-01','icon':'🏥','color':'#6c47ff','status':'inscrito',
              'createdAt':'2026-09-01','disciplinas':[]}]})

# texto como sai de um edital de verdade: sumario no comeco, regras, o anexo no fim
EDITAL = ("--- Página 1 ---\nEDITAL N. 1 SESAU/RO, DE 12 DE AGOSTO DE 2026\n"
 "1 DAS DISPOSICOES PRELIMINARES\n1.1 O concurso sera regido por este edital.\n"
 "1.9 O conteudo programatico consta do Anexo II deste edital.\n"
 + "\n".join("2.%d Requisito generico de inscricao numero %d, texto de preenchimento." % (i,i) for i in range(1,60))
 + "\n--- Página 8 ---\n3 DAS VAGAS\n" + "\n".join("3.%d Vaga reservada conforme a lei." % i for i in range(1,40))
 + "\n--- Página 22 ---\nANEXO II — CONTEUDO PROGRAMATICO\n"
 "CONHECIMENTOS BASICOS\nLINGUA PORTUGUESA: 1 Compreensao de texto. 2 Ortografia oficial. 3 Concordancia.\n"
 "CONHECIMENTOS ESPECIFICOS\nENFERMAGEM: 1 Sistematizacao da Assistencia de Enfermagem. "
 "2 Vacinacao: calendario e rede de frio. 3 Urgencia e emergencia. 4 Saude mental.\n"
 "SAUDE PUBLICA: 1 SUS: principios e diretrizes. 2 Vigilancia em saude.\n"
 "--- Página 30 ---\nDAS DISPOSICOES FINAIS\n9.1 Os casos omissos serao resolvidos pela banca.\n"
 + "\n".join("9.%d Disposicao final numero %d que nao interessa." % (i,i) for i in range(2,40)))

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        r=await page.evaluate("(t)=>{const c=edRecortarConteudo(t);return {achou:c.achou,tam:c.texto.length,ini:c.texto.slice(0,60),fim:c.texto.slice(-70)};}",EDITAL)
        print('--- recorte do conteúdo programático')
        print('    texto original      : %d caracteres'%len(EDITAL))
        print('    achou o cabeçalho   : %s'%r['achou'])
        print('    sobrou pra IA       : %d caracteres  (%.0f%% do original)'%(r['tam'],100*r['tam']/len(EDITAL)))
        print('    começa em           : %r'%r['ini'])
        print('    termina em          : %r'%r['fim'])
        print('    cortou as regras?   : %s'%('DAS DISPOSICOES PRELIMINARES' not in r['ini']))

        # sem cabecalho nenhum: nao pode explodir, manda o que tem
        r2=await page.evaluate("()=>{const c=edRecortarConteudo('Texto qualquer sem cabecalho de conteudo.');return {achou:c.achou,tam:c.texto.length};}")
        print('\n--- PDF sem cabeçalho reconhecível: achou=%s, mandou %d chars (não quebra)'%(r2['achou'],r2['tam']))

        # o botao existe na tela?
        ui=await page.evaluate("""()=>{showScreen('editais');edAbertos.add('e1');renderEditais();
            const lbl=[...document.querySelectorAll('label')].find(l=>l.textContent.includes('PDF do edital'));
            const inp=document.querySelector('input[type=file][accept*=pdf]');
            return {botao:!!lbl, input:!!inp, aceita:inp?inp.getAttribute('accept'):null};}""")
        print('\n--- na tela: botão=%s  input=%s  aceita=%r'%(ui['botao'],ui['input'],ui['aceita']))

        # arquivo que nao e PDF
        er=await page.evaluate("""async()=>{
            const f=new File(['x'],'foto.png',{type:'image/png'});
            const dt=new DataTransfer(); dt.items.add(f);
            const inp=document.querySelector('input[type=file][accept*=pdf]');
            inp.files=dt.files;
            await edLerPDF('e1',inp);
            const st=document.getElementById('ed-pdf-st-e1');
            return {msg:st?st.textContent.trim():null, erro:st?st.getAttribute('data-erro'):null};}""")
        print('--- enviou um PNG: %r (marcado como erro: %s)'%(er['msg'],er['erro']))
        print('\nerros de JS: %s'%[e for e in errs if 'selectedPixTier' not in e])
        await b.close()
asyncio.run(main())
