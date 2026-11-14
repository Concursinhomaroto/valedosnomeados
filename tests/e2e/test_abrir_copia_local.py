# -*- coding: utf-8 -*-
# Abrir pela cópia local. Antes, toda abertura esperava o Firebase entregar o registro inteiro
# (~13 MB numa conta real: 4 a 5 s na tela de carregamento). Agora, com cópia local, o app abre
# com ela e pergunta ao servidor só o lastModified:
#   igual      -> não baixa nada (modo econômico: vigia só o lastModified e o plano);
#   diferente  -> liga o ouvinte completo de sempre, que decide quem vence.
# O mock do Firebase renasce a cada recarga; aqui o "servidor" é guardado no localStorage antes
# de recarregar e devolvido por um init script — é o que deixa simular servidor igual, mais
# novo ou mais velho que a cópia local.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

UID='TEST_UID_LEO'
V1='users/%s/vdn_v1'%UID

def seed():
    subs=[{'id':'s0','name':'Assunto 0','priority':70,'studied':True,'studiedAt':'2026-01-01'},
          {'id':'s1','name':'Assunto 1','priority':70,'studied':True,'studiedAt':'2026-01-01'}]
    return make_seed({'studyNickname':'Leo','xp':100,
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],
      'topics':{'k1':[{'id':'t1','name':'Urgência','icon':'⚔️','subtopics':subs}]},
      'flashcards':{'fc1':{'id':'fc1','mbId':'t1','subId':'s0','pergunta':'P','resposta':'R','tags':'','dificuldade':2,
                           'acertos':0,'erros':0,'lastConf':0,'criacao':'2026-01-01T10:00:00Z'}},
      'revisions':{'s0':[{'date':'2026-01-10','completed':False}]}})

# Roda antes do app em toda carga: devolve o "servidor" guardado e, se pedido, segura a
# primeira resposta do lastModified até o teste liberar (simula servidor lento/sem rede).
INIT=r"""
try{const r=localStorage.getItem('__mock_root');if(r)window.__root=JSON.parse(r);}catch(e){}
window.__leiturasCompletas=0;
(function(){
  const dbOrig=window.firebase.database;
  window.firebase.database=function(){
    const d=dbOrig();const refOrig=d.ref;
    return {ref:(p)=>{
      const r=refOrig(p);
      if(typeof p==='string'&&/\/vdn_v1$/.test(p)){
        const on0=r.on.bind(r),once0=r.once.bind(r);
        r.on=(ev,cb,err)=>{window.__leiturasCompletas++;return on0(ev,cb,err);};
        r.once=(ev)=>{window.__leiturasCompletas++;return once0(ev);};
      }
      if(localStorage.getItem('__mock_segurar')==='1'&&typeof p==='string'&&/\/vdn_v1\/lastModified$/.test(p)){
        const on0=r.on.bind(r);
        r.on=(ev,cb,err)=>{
          let liberado=false,ultimo=null;
          window.__liberarLM=()=>{liberado=true;if(ultimo){const u=ultimo;ultimo=null;cb(u);}};
          return on0(ev,(s)=>{if(liberado)cb(s);else ultimo=s;},err);
        };
      }
      return r;
    }};
  };
})();
"""

ESTADO="""()=>({abriuCedo,servidorVisto,aoVivo:ouvinteCompletoLigado,pronto:firebaseReady,nuvemPendente,
  leiturasCompletas:window.__leiturasCompletas,
  ouvintesNoRegistro:(window.__listeners['%s']||[]).length,
  vigias:Object.keys(window.__listeners).filter(k=>k.indexOf('%s/')===0).map(k=>k.split('/').pop()).sort(),
  xp:db.xp,overlay:getComputedStyle(document.getElementById('loading-overlay')).display,
  painel:document.getElementById('screen-dashboard').classList.contains('active')&&document.getElementById('dash-stats').children.length>0})"""%(V1,V1)

NUVEM="""(p)=>{let n=window.__root;p.split('/').forEach(s=>{n=n&&n[s];});return n?{xp:n.xp,lm:n.lastModified,nota:n.notaDeOutroAparelho||null}:null;}"""
GRAVACOES="""(p)=>window.__updateCalls.filter(x=>x.path===p).map(x=>({op:x.op,chaves:x.op==='update'?Object.keys(x.val).sort():['(registro inteiro)']}))"""

async def recarregar(page, ajuste='', segurar=False, espera=1800):
    # garante que o que está pendente foi pra cópia local e pro "servidor" antes de guardar
    await page.evaluate("()=>{if(typeof saveFlush==='function')saveFlush();}")
    await page.wait_for_timeout(400)
    await page.evaluate("""([ajuste,segurar])=>{
      const root=JSON.parse(JSON.stringify(window.__root));
      (new Function('root','reg',ajuste))(root,root.users.TEST_UID_LEO.vdn_v1);
      localStorage.setItem('__mock_root',JSON.stringify(root));
      localStorage.setItem('__mock_segurar',segurar?'1':'0');}""",[ajuste,segurar])
    await page.reload()
    await page.wait_for_timeout(espera)

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.add_init_script(INIT)
        await page.wait_for_timeout(1200)

        print('=== 0) primeira abertura, sem cópia local: carrega do servidor, como sempre ===')
        r=await page.evaluate(ESTADO)
        print('   %s'%r)
        assert not r['abriuCedo'] and r['aoVivo'] and r['pronto'] and r['ouvintesNoRegistro']==1 and r['painel']
        await page.evaluate("()=>{db.xp=150;saveDB();}")
        print('   OK\n')

        print('=== 1) servidor IGUAL à cópia: abre pela cópia e não baixa o registro ===')
        await recarregar(page)
        r=await page.evaluate(ESTADO)
        print('   %s'%r)
        assert r['abriuCedo'] and r['servidorVisto'] and r['pronto'] and not r['aoVivo']
        assert r['leiturasCompletas']==0 and r['ouvintesNoRegistro']==0, 'não era pra ler o registro inteiro'
        assert r['vigias']==['lastModified','lastPaymentAt','plan'] and r['xp']==150 and r['overlay']=='none' and r['painel']
        # gravar no modo econômico: sobe só o que mudou, e o eco não é confundido com outro aparelho
        await page.evaluate("()=>{window.__updateCalls=[];db.xp=151;saveDB();}")
        await page.wait_for_timeout(1100)
        g=await page.evaluate(GRAVACOES,V1); n=await page.evaluate(NUVEM,V1); r=await page.evaluate(ESTADO)
        print('   gravações: %s | nuvem: %s | ao vivo? %s'%(g,n,r['aoVivo']))
        assert g==[{'op':'update','chaves':['lastModified','xp']}] and n['xp']==151 and not r['aoVivo'] and r['leiturasCompletas']==0
        print('   OK\n')

        print('=== 2) servidor MAIS NOVO (estudou em outro aparelho): baixa e a tela passa a mostrar o dele ===')
        await recarregar(page,"reg.xp=900;reg.notaDeOutroAparelho='oi';reg.lastModified=reg.lastModified+60000;")
        r=await page.evaluate(ESTADO)
        nota=await page.evaluate("()=>db.notaDeOutroAparelho")
        print('   %s | nota: %s'%(r,nota))
        assert r['abriuCedo'] and r['aoVivo'] and r['pronto'] and r['xp']==900 and nota=='oi' and r['overlay']=='none'
        assert r['ouvintesNoRegistro']==1 and r['vigias']==[], 'ao vivo: só o ouvinte completo'
        tela=await page.evaluate("()=>document.getElementById('dash-stats').textContent")
        assert '900' in tela, 'a tela tinha de ser redesenhada com o XP do servidor: %s'%tela
        print('   OK\n')

        print('=== 3) cópia MAIS NOVA (estudou sem internet): a cópia vence e sobe só a diferença ===')
        await page.evaluate("()=>{db.xp=1000;saveDB();}")
        await recarregar(page,"reg.xp=900;reg.lastModified=reg.lastModified-60000;")
        await page.wait_for_timeout(1200)
        r=await page.evaluate(ESTADO); n=await page.evaluate(NUVEM,V1); g=await page.evaluate(GRAVACOES,V1)
        print('   %s | nuvem: %s | gravações: %s'%(r,n,g))
        assert r['abriuCedo'] and r['aoVivo'] and r['xp']==1000 and n['xp']==1000 and n['nota']=='oi'
        assert g and all(x['op']=='update' for x in g), 'tinha de subir a diferença, não o registro inteiro'
        print('   OK\n')

        print('=== 4) servidor demora a responder: dá pra usar, a cópia local guarda, a nuvem espera ===')
        await recarregar(page,'',segurar=True)
        r=await page.evaluate(ESTADO)
        print('   antes da resposta: %s'%r)
        assert r['abriuCedo'] and not r['servidorVisto'] and not r['pronto'] and r['painel'] and r['overlay']=='none' and r['leiturasCompletas']==0
        await page.evaluate("()=>{window.__updateCalls=[];db.xp=1001;saveDB();}")
        await page.wait_for_timeout(1100)
        g=await page.evaluate(GRAVACOES,V1); r=await page.evaluate(ESTADO)
        loc=await page.evaluate("async()=>{const c=await idbLer(lsKey());return c&&c.xp;}")
        print('   sem resposta: gravações na nuvem %s | cópia local xp=%s | pendente=%s'%(g,loc,r['nuvemPendente']))
        assert g==[] and loc==1001 and r['nuvemPendente']
        await page.evaluate("()=>window.__liberarLM()")
        await page.wait_for_timeout(300)
        g=await page.evaluate(GRAVACOES,V1); n=await page.evaluate(NUVEM,V1); r=await page.evaluate(ESTADO)
        print('   servidor respondeu (igual): gravações %s | nuvem %s | %s'%(g,n,r))
        assert g==[{'op':'update','chaves':['lastModified','xp']}] and n['xp']==1001
        assert r['servidorVisto'] and r['pronto'] and not r['aoVivo'] and not r['nuvemPendente'] and r['leiturasCompletas']==0
        print('   OK\n')

        print('=== 5) servidor demora E tinha coisa mais nova: o que é do servidor entra, sem virar conta em branco ===')
        await recarregar(page,"reg.xp=2000;reg.lastModified=reg.lastModified+60000;",segurar=True)
        await page.evaluate("()=>{db.xp=1002;saveDB();saveFlush();}")
        await page.evaluate("()=>window.__liberarLM()")
        await page.wait_for_timeout(1200)
        r=await page.evaluate(ESTADO); n=await page.evaluate(NUVEM,V1)
        print('   %s | nuvem: %s'%(r,n))
        assert r['aoVivo'] and r['xp']==2000 and n['xp']==2000 and r['overlay']=='none'
        est=await page.evaluate("()=>({reinos:db.kingdoms.length,cards:Object.keys(db.flashcards).length})")
        assert est=={'reinos':1,'cards':1}, est
        print('   OK\n')

        print('=== 6) outro aparelho grava com o app aberto no modo econômico: passa a ouvir tudo ===')
        await recarregar(page)
        r=await page.evaluate(ESTADO)
        assert r['abriuCedo'] and not r['aoVivo'] and r['leiturasCompletas']==0, r
        # aba escondida: não baixa nada até você voltar
        await page.evaluate("""(p)=>{Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});
          firebase.database().ref(p).update({xp:3000,lastModified:Date.now()+60000});}""",V1)
        await page.wait_for_timeout(200)
        r=await page.evaluate(ESTADO)
        print('   escondida: %s'%{k:r[k] for k in ('aoVivo','xp','leiturasCompletas')})
        assert not r['aoVivo'] and r['xp']!=3000
        await page.evaluate("()=>{delete document.hidden;document.dispatchEvent(new Event('visibilitychange'));}")
        await page.wait_for_timeout(300)
        r=await page.evaluate(ESTADO)
        print('   voltou: %s'%{k:r[k] for k in ('aoVivo','xp','ouvintesNoRegistro','vigias')})
        assert r['aoVivo'] and r['xp']==3000 and r['ouvintesNoRegistro']==1 and r['vigias']==[]
        # e a partir daí cada mudança de fora chega, como sempre
        await page.evaluate("(p)=>firebase.database().ref(p).update({xp:3001,lastModified:Date.now()+120000})",V1)
        await page.wait_for_timeout(200)
        assert (await page.evaluate("()=>db.xp"))==3001
        print('   OK\n')

        print('=== 7) plano mexido no servidor com o app aberto: também passa a ouvir tudo ===')
        await recarregar(page)
        r=await page.evaluate(ESTADO)
        assert r['abriuCedo'] and not r['aoVivo'], r
        await page.evaluate("(p)=>firebase.database().ref(p+'/lastPaymentAt').set('2026-11-11')",V1)
        await page.wait_for_timeout(300)
        r=await page.evaluate(ESTADO)
        pg=await page.evaluate("()=>db.lastPaymentAt")
        print('   ao vivo? %s | lastPaymentAt=%s'%(r['aoVivo'],pg))
        assert r['aoVivo'] and pg=='2026-11-11'
        print('   OK\n')

        e=real_errors(errs)
        print('erros de JS:',e or 'nenhum')
        assert not e
        await b.close()
    print('OK')

asyncio.run(main())
