import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
seed=make_seed({'studyNickname':'Leo',
  'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'ok'}],
  'topics':{'k1':[{'id':'t1','name':'Saude Mental','subtopics':[{'id':'s1','name':'Esquizofrenia','priority':30}]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        # 1) IndexedDB esta sendo usado?
        r=await page.evaluate("""async()=>{
            db.notes=db.notes||{};
            db.notes.gigante='x'.repeat(2500000);   // ~2,5 milhoes de chars = ~5 MB em UTF-16
            gravarCacheLocal();
            await new Promise(r=>setTimeout(r,1200));
            const ls=(()=>{try{return localStorage.getItem(lsKey());}catch(e){return null;}})();
            const idb=await idbLer(lsKey());
            return {cacheIdbOk, desligado:cacheLocalDesligado,
                    noLocalStorage: ls?ls.length:0,
                    noIndexedDB: idb&&idb.notes&&idb.notes.gigante?idb.notes.gigante.length:0};
        }""")
        print('--- A) banco de ~5 MB (impossivel no localStorage)')
        print('   IndexedDB disponivel: %s | cache desligado: %s'%(r['cacheIdbOk'],r['desligado']))
        print('   guardado no localStorage: %d chars'%r['noLocalStorage'])
        print('   guardado no IndexedDB:    %d chars'%r['noIndexedDB'])
        print('   erros: %s\n'%[e for e in errs if 'selectedPixTier' not in e])

        # 2) le de volta apos "reabrir" (prepararCacheLocal + lerCacheLocal)
        r2=await page.evaluate("""async()=>{
            cacheIdbMem=null;cacheIdbLegadoMem=null;
            await prepararCacheLocal();
            const lido=lerCacheLocal();
            return {tem: !!(lido&&lido.notes&&lido.notes.gigante),
                    tam: lido&&lido.notes&&lido.notes.gigante?lido.notes.gigante.length:0,
                    dono: lido?lido._uid:null};
        }""")
        print('--- B) reabrir o app: le a copia de volta do IndexedDB')
        print('   recuperou: %s (%d chars) | carimbo de dono: %s\n'%(r2['tem'],r2['tam'],r2['dono']))

        # 3) migracao: quem ja tinha copia no localStorage
        r3=await page.evaluate("""async()=>{
            const k=lsKey();
            let antes=0;
            try{localStorage.setItem(k,JSON.stringify({_uid:(currentUser&&currentUser.uid)||'x',velho:true}));
                localStorage.setItem('vdn_local_v1_OUTRACONTA',JSON.stringify({_uid:'outro'}));
                antes=Object.keys(localStorage).filter(x=>x.indexOf('vdn_local_v1')===0).length;}catch(e){}
            db.notes.gigante='y'.repeat(1000);
            gravarCacheLocal();
            await new Promise(r=>setTimeout(r,1200));
            const depois=Object.keys(localStorage).filter(x=>x.indexOf('vdn_local_v1')===0).length;
            return {antes,depois};
        }""")
        print('--- C) migracao: copias antigas no localStorage saem do caminho')
        print('   chaves vdn_local_v1* antes: %d -> depois: %d'%(r3['antes'],r3['depois']))
        await b.close()
asyncio.run(main())
