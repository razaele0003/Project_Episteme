import React, {useEffect,useRef,useState} from 'react';
import {ArrowLeft,ArrowRight,ExternalLink,Globe2,Minus,RotateCw} from 'lucide-react';

const KEY='episteme.browser.url';
const DEFAULT='https://example.com/';

export function browserLink(value){
  try{
    const raw=value.trim();
    if(!raw)return null;
    const url=new URL(/^[a-z][a-z\d+.-]*:/i.test(raw)?raw:`https://${raw}`);
    const host=url.hostname.toLowerCase();
    const localHost=host==='localhost'||host.endsWith('.localhost')||host.endsWith('.local')||host.includes(':')||/^\d+(\.\d+){3}$/.test(host);
    if(url.protocol!=='https:'||!host||localHost||url.port||url.username||url.password)return null;
    return url.href;
  }catch{return null;}
}

export default function MiniBrowser(){
  const saved=()=>{try{return browserLink(localStorage.getItem(KEY)||'')||DEFAULT;}catch{return DEFAULT;}};
  const initial=useRef(saved()).current;
  const [open,setOpen]=useState(false),[draft,setDraft]=useState(initial),[history,setHistory]=useState([initial]),[index,setIndex]=useState(0),[frameKey,setFrameKey]=useState(0),[error,setError]=useState('');
  const trigger=useRef(null),address=useRef(null);
  const current=history[index];

  useEffect(()=>{if(open)address.current?.select();},[open]);
  function close(){setOpen(false);trigger.current?.focus();}
  function visit(e){
    e?.preventDefault();
    const valid=browserLink(draft);
    if(!valid){setError('Enter a public website such as example.com. HTTPS is added automatically.');address.current?.focus();return;}
    const next=[...history.slice(0,index+1),valid];
    setHistory(next);setIndex(next.length-1);setDraft(valid);setFrameKey(key=>key+1);setError('');
    try{localStorage.setItem(KEY,valid);}catch{/* Browsing still works without local storage. */}
  }
  function move(nextIndex){setIndex(nextIndex);setDraft(history[nextIndex]);setFrameKey(key=>key+1);setError('');}

  const host=new URL(current).hostname.toLowerCase();
  const embeddingBlocked=host==='chatgpt.com'||host.endsWith('.chatgpt.com')||host==='facebook.com'||host.endsWith('.facebook.com');

  return <div className="chat-widget">
    {open&&<section className="chat-panel mini-browser-panel" id="mini-browser-panel" aria-label="Mini browser" onKeyDown={e=>{if(e.key==='Escape'){e.stopPropagation();close();}}}>
      <header><div><Globe2 size={20}/><strong>Mini browser</strong></div><button type="button" onClick={close} aria-label="Minimize mini browser"><Minus size={20}/></button></header>
      <form className="browser-toolbar" onSubmit={visit}>
        <button type="button" onClick={()=>move(index-1)} disabled={index===0} aria-label="Go back"><ArrowLeft size={17}/></button>
        <button type="button" onClick={()=>move(index+1)} disabled={index===history.length-1} aria-label="Go forward"><ArrowRight size={17}/></button>
        <button type="button" onClick={()=>setFrameKey(key=>key+1)} aria-label="Reload page"><RotateCw size={16}/></button>
        <label className="sr-only" htmlFor="browser-address">Website address</label>
        <input ref={address} id="browser-address" value={draft} onChange={e=>{setDraft(e.target.value);setError('');}} aria-invalid={!!error} aria-describedby={error?'browser-address-error':'browser-note'} spellCheck="false" inputMode="url"/>
        <a href={browserLink(draft)||current} target="_blank" rel="noopener noreferrer" aria-label="Open current page in a new tab"><ExternalLink size={16}/></a>
      </form>
      {error&&<p className="browser-error" id="browser-address-error" role="alert">{error}</p>}
      <div className="browser-frame-wrap">{embeddingBlocked?<div className="browser-blocked"><Globe2 size={30}/><strong>{host} blocks embedded viewing</strong><p>This website only allows its pages in a full browser tab.</p><a href={current} target="_blank" rel="noopener noreferrer">Open website <ExternalLink size={15}/></a></div>:<iframe key={`${current}-${frameKey}`} title="Mini browser page" src={current} sandbox="allow-forms allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox" referrerPolicy="no-referrer"/>}</div>
      <p className="browser-note" id="browser-note">Type example.com or a full HTTPS address. Some websites prohibit embedded viewing.</p>
    </section>}
    <button ref={trigger} type="button" className="chat-trigger" aria-expanded={open} aria-controls="mini-browser-panel" aria-label={open?'Minimize mini browser':'Open mini browser'} onClick={()=>open?close():setOpen(true)}><Globe2 size={23}/><span>Browser</span></button>
  </div>;
}
