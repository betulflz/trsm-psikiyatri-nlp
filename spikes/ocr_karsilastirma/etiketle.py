"""DENEME (spike): OCR denemesindeki sayfalar için tıklamayla ilaç/doz ve semptom teması etiketleme.

Kalıcı kod değildir. Yalnızca bu bilgisayarda (127.0.0.1) çalışan küçük bir
sunucu açar. Her sayfanın fotoğrafının yanında modellerin ve eski OCR'ın
bulduğu ilaçların ve semptom temalarının birleşimi listelenir; kullanıcı her
birini "var" / "yok" diye işaretler, eksikleri listeden seçerek ekler.
İşaretler cikti/etiketler.json dosyasına yazılır (hasta verisi; git'e eklenmez).
Yeni bir okuma yeni aday getirirse, yalnızca o adaylar sorulur.

Hangi adayı hangi modelin bulduğu ekranda gösterilmez (körleme).

Çalıştırma (proje kökünden):
    uv run python spikes/ocr_karsilastirma/etiketle.py
"""
import json
import re
import sys
import webbrowser
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from trsm.db import get_connection  # noqa: E402
from trsm.drug_matching import build_surface_form_index_from_db  # noqa: E402
from trsm.medication_pipeline import extract_medications_from_text  # noqa: E402
from trsm.model_loader import load_local_minilm  # noqa: E402
from trsm.symptom_categories import KATEGORILER  # noqa: E402
from trsm.transparent_symptom_query import build_category_seed_embeddings, classify_symptom_phrases  # noqa: E402

OUT = Path(__file__).parent / "cikti"
LABELS = OUT / "etiketler.json"
PORT = 8765


def page_themes(text, model, seeds):
    """Symptom themes of a whole page; the product splitter stops at 12 clauses, so split here."""
    text = (text or "").replace("[?]", " ")
    phrases = list(dict.fromkeys(p.strip() for p in re.split(r"[.;,\n]+", text) if len(p.strip()) >= 4))
    return {c["kategori"] for row in classify_symptom_phrases(phrases, model, seeds) for c in row["kategoriler"]}


def candidates(result, index):
    """Union of drugs found by every reading and by the old OCR, with a suggested dose."""
    doses = {}
    sources = [reading["ilaclar"] for reading in result["okumalar"].values()]
    sources.append(extract_medications_from_text(result["eski_ocr"], index))
    for meds in sources:
        for m in meds:
            doses.setdefault(m["ilac_adi_normalize"], []).append(m["doz"])
    return [
        {"ad": name, "doz": (Counter(d for d in ds if d).most_common(1) or [("", 0)])[0][0]}
        for name, ds in sorted(doses.items())
    ]


def theme_candidates(result, model, seeds):
    texts = [reading["metin"] for reading in result["okumalar"].values()] + [result["eski_ocr"]]
    return sorted(set().union(*(page_themes(t, model, seeds) for t in texts)))


def load_labels():
    return json.loads(LABELS.read_text(encoding="utf-8")) if LABELS.exists() else {}


PAGE = """<!doctype html><meta charset="utf-8"><title>OCR etiketleme</title>
<style>
body{font-family:-apple-system,sans-serif;margin:0;background:#f4f4f4;color:#222}
.ust{display:flex;align-items:center;gap:12px;padding:8px 16px;background:#fff;border-bottom:1px solid #ddd;position:sticky;top:0;z-index:2}
.ana{display:flex;gap:16px;padding:16px}
.foto{flex:3;overflow:auto;max-height:calc(100vh - 90px);background:#fff;border:1px solid #ccc}
.foto img{width:100%;cursor:zoom-in}.foto img.buyuk{width:200%;cursor:zoom-out}
.panel{flex:2;min-width:320px;max-height:calc(100vh - 90px);overflow:auto}
.aday{display:flex;align-items:center;gap:8px;background:#fff;border:1px solid #ddd;border-radius:8px;padding:8px;margin-bottom:8px}
.aday .ad{flex:1;font-weight:600}.aday input{width:90px}
.aday.var{border-color:#2e9d4a;background:#eaf7ee}.aday.yok{border-color:#c33;background:#fbeaea;opacity:.7}
.aday.yeni{outline:2px solid #f0b400}
button{font-size:15px;padding:6px 12px;border-radius:6px;border:1px solid #aaa;background:#fff;cursor:pointer}
button.secili.e{background:#2e9d4a;color:#fff}button.secili.h{background:#c33;color:#fff}
#sonraki{background:#2463c7;color:#fff;border-color:#2463c7}#sonraki:disabled{opacity:.4}
.ekle{display:flex;gap:6px;margin:12px 0}.ekle input,.ekle select{flex:1;font-size:15px;padding:6px}
h3{margin:18px 0 8px}small{color:#666}
</style>
<div class="ust"><button id="onceki">◀</button><b id="baslik"></b><span id="ilerleme"></span>
<small>Fotoğrafa tıklayınca büyür. Kısayol: E = var, H = yok (sıradaki boş aday için). Sarı çerçeve: yeni sorulan aday.</small></div>
<div class="ana"><div class="foto"><img id="img"></div>
<div class="panel">
<h3>İlaç: bu sayfada yazıyor mu? <button class="hepsiyok" data-t="adaylar" style="font-size:13px">Kalanların hepsi ❌</button></h3><div id="liste"></div>
<div class="ekle"><input id="yeni" list="sozluk" placeholder="listede olmayan ilaç: ilk harfler…"><input id="yenidoz" placeholder="doz" style="flex:0 0 90px"><button id="ekle">Ekle</button></div>
<div id="eklenen"></div>
<h3>Semptom teması: sayfada bu yakınma var mı? <button class="hepsiyok" data-t="temalar" style="font-size:13px">Kalanların hepsi ❌</button></h3>
<small>Tanı değil, geniş tema. Sayfada geçiyorsa ✅.</small><div id="tliste"></div>
<div class="ekle"><select id="yenitema"><option value="">listede olmayan tema seç…</option></select><button id="temaekle">Ekle</button></div>
<p><button id="sonraki" disabled>Kaydet ve sonraki ▶</button></p></div></div>
<datalist id="sozluk"></datalist>
<script>
let sayfalar=[],i=0,durum=null;
const $=id=>document.getElementById(id);
const eksik=s=>!s.etiket||s.adaylar.some(a=>(!s.etiket.adaylar||!s.etiket.adaylar[a.ad]||s.etiket.adaylar[a.ad].var===null)&&!(s.etiket.eklenen||[]).some(x=>x.ad===a.ad))
 ||s.temalar.some(t=>!s.etiket.temalar||!s.etiket.temalar[t]||s.etiket.temalar[t].var===null);
async function yukle(){const r=await (await fetch('/api/veri')).json();sayfalar=r.sayfalar;
 $('sozluk').innerHTML=r.sozluk.map(s=>`<option value="${s}">`).join('');
 $('yenitema').innerHTML+=r.temalar.map(t=>`<option>${t}</option>`).join('');
 i=sayfalar.findIndex(eksik);if(i<0)i=0;goster();}
function goster(){const s=sayfalar[i];const e=s.etiket||{};const eski=!!s.etiket;
 const al=(kayit,ad,varsayilan)=>kayit&&kayit[ad]?kayit[ad]:{...varsayilan,var:null,yeni:eski};
 durum={adaylar:Object.fromEntries(s.adaylar.map(a=>[a.ad,al(e.adaylar,a.ad,{doz:a.doz})])),eklenen:e.eklenen||[],
  temalar:Object.fromEntries(s.temalar.map(t=>[t,al(e.temalar,t,{})])),eklenen_temalar:e.eklenen_temalar||[]};
 for(const t of durum.eklenen_temalar)durum.temalar[t]={var:true};
 durum.eklenen=durum.eklenen.filter(x=>{const a=durum.adaylar[x.ad];if(!a)return true;a.var=true;if(x.doz)a.doz=x.doz;a.yeni=false;return false;});
 $('baslik').textContent=`Sayfa ${s.no}`;$('ilerleme').textContent=`(${sayfalar.filter(x=>!eksik(x)).length}/${sayfalar.length} tamam)`;
 $('img').src=`/gorsel/${s.no}`;$('img').className='';ciz();}
function satirlar(kap,kayitlar,dozlu){kap.innerHTML='';
 for(const [ad,d] of Object.entries(kayitlar)){const k=document.createElement('div');
  k.className='aday'+(d.var===true?' var':d.var===false?' yok':'')+(d.yeni&&d.var===null?' yeni':'');
  k.innerHTML=`<span class="ad"></span>${dozlu?'<input placeholder="doz">':''}<button class="e">✅ var</button><button class="h">❌ yok</button>`;
  k.querySelector('.ad').textContent=ad;
  if(dozlu){const inp=k.querySelector('input');inp.value=d.doz||'';inp.oninput=()=>d.doz=inp.value;}
  const be=k.querySelector('.e'),bh=k.querySelector('.h');if(d.var===true)be.classList.add('secili');if(d.var===false)bh.classList.add('secili');
  be.onclick=()=>{d.var=true;ciz()};bh.onclick=()=>{d.var=false;ciz()};kap.appendChild(k);}}
function ciz(){satirlar($('liste'),durum.adaylar,true);satirlar($('tliste'),durum.temalar,false);
 if(!Object.keys(durum.adaylar).length)$('liste').innerHTML='<p><small>Modeller bu sayfada ilaç bulmadı. Sayfada ilaç varsa aşağıdan ekleyin.</small></p>';
 if(!Object.keys(durum.temalar).length)$('tliste').innerHTML='<p><small>Modeller tema bulmadı. Sayfada varsa aşağıdan ekleyin.</small></p>';
 $('eklenen').innerHTML='';durum.eklenen.forEach((x,j)=>{const k=document.createElement('div');k.className='aday var';
  k.innerHTML='<span class="ad"></span><span></span><button>Sil</button>';k.querySelector('.ad').textContent=x.ad;k.children[1].textContent=x.doz||'';
  k.querySelector('button').onclick=()=>{durum.eklenen.splice(j,1);ciz()};$('eklenen').appendChild(k);});
 const bos=[...Object.values(durum.adaylar),...Object.values(durum.temalar)].some(d=>d.var===null);
 $('sonraki').disabled=bos;$('sonraki').textContent=i===sayfalar.length-1?'Kaydet ve bitir ✔':'Kaydet ve sonraki ▶';}
$('ekle').onclick=()=>{const ad=$('yeni').value.trim();if(!ad)return;
 if(!document.querySelector(`#sozluk option[value="${CSS.escape(ad)}"]`)&&!confirm(`"${ad}" sözlükte yok. Yine de eklensin mi?`))return;
 if(durum.adaylar[ad]){durum.adaylar[ad].var=true;}else{durum.eklenen.push({ad,doz:$('yenidoz').value.trim()});}
 $('yeni').value='';$('yenidoz').value='';ciz();};
$('yeni').onkeydown=e=>{if(e.key==='Enter')$('ekle').click()};
$('temaekle').onclick=()=>{const t=$('yenitema').value;if(!t)return;
 if(durum.temalar[t])durum.temalar[t].var=true;else{durum.temalar[t]={var:true};durum.eklenen_temalar.push(t);}
 $('yenitema').value='';ciz();};
$('sonraki').onclick=async()=>{const s=sayfalar[i];
 const sade=o=>Object.fromEntries(Object.entries(o).map(([k,{yeni,...v}])=>[k,v]));
 const temalar=sade(durum.temalar);
 const etiket={adaylar:sade(durum.adaylar),eklenen:durum.eklenen,temalar,eklenen_temalar:durum.eklenen_temalar,bitti:true};
 const r=await fetch('/api/kaydet',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({no:s.no,etiket})});
 if(!r.ok){alert('Kaydedilemedi');return;}s.etiket=etiket;
 const sonraki=sayfalar.findIndex(eksik);
 if(sonraki>=0){i=sonraki;goster();scrollTo(0,0);}else{goster();alert('Hepsi tamam, teşekkürler! Pencereyi kapatabilirsiniz.');}};
document.querySelectorAll('.hepsiyok').forEach(b=>b.onclick=()=>{for(const d of Object.values(durum[b.dataset.t]))if(d.var===null)d.var=false;ciz();});
$('onceki').onclick=()=>{if(i>0){i--;goster();}};
$('img').onclick=()=>$('img').classList.toggle('buyuk');
document.onkeydown=e=>{if(['INPUT','SELECT'].includes(e.target.tagName))return;const k=e.key.toLowerCase();if(k!=='e'&&k!=='h')return;
 const bos=[...Object.values(durum.adaylar),...Object.values(durum.temalar)].find(d=>d.var===null);if(bos){bos.var=k==='e';ciz();}};
yukle();
</script>"""


def main():
    results = json.loads((OUT / "sonuclar.json").read_text(encoding="utf-8"))
    with get_connection() as conn:
        index = build_surface_form_index_from_db(conn)
        drug_names = [r[0] for r in conn.execute("SELECT resmi_ad FROM ilac_sozluk ORDER BY resmi_ad")]
    model = load_local_minilm()
    seeds = build_category_seed_embeddings(model)
    pages = [
        {"no": r["no"], "adaylar": candidates(r, index), "temalar": theme_candidates(r, model, seeds), "gorsel": r["gorsel"]}
        for r in results
    ]
    images = {p["no"]: Path(p.pop("gorsel")) for p in pages}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # sessiz: terminale yol/veri yazma
            pass

        def send(self, body, content_type, status=200):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                self.send(PAGE.encode(), "text/html; charset=utf-8")
            elif self.path == "/api/veri":
                labels = load_labels()
                data = {
                    "sozluk": drug_names, "temalar": list(KATEGORILER),
                    "sayfalar": [{**p, "etiket": labels.get(str(p["no"]))} for p in pages],
                }
                self.send(json.dumps(data, ensure_ascii=False).encode(), "application/json")
            elif self.path.startswith("/gorsel/") and self.path[8:].isdigit() and int(self.path[8:]) in images:
                self.send(images[int(self.path[8:])].read_bytes(), "image/jpeg")
            else:
                self.send(b"", "text/plain", 404)

        def do_POST(self):
            if self.path != "/api/kaydet":
                return self.send(b"", "text/plain", 404)
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            labels = load_labels()
            labels[str(int(body["no"]))] = body["etiket"]
            LABELS.write_text(json.dumps(labels, ensure_ascii=False, indent=1), encoding="utf-8")
            self.send(b"{}", "application/json")

    labels = load_labels()

    def open_questions(p):
        lab = labels.get(str(p["no"])) or {}
        drugs = sum(1 for a in p["adaylar"] if (lab.get("adaylar") or {}).get(a["ad"], {}).get("var") is None)
        themes = sum(1 for t in p["temalar"] if (lab.get("temalar") or {}).get(t, {}).get("var") is None)
        return drugs, themes

    open_counts = [open_questions(p) for p in pages]
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"{len(pages)} sayfa. Yanıt bekleyen: {sum(d for d, _ in open_counts)} ilaç, {sum(t for _, t in open_counts)} tema sorusu.")
    print(f"Adres: http://127.0.0.1:{PORT}  ·  Bitince bu pencerede Ctrl+C ile kapatın.")
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
