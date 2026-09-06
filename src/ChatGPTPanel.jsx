import React, {useEffect,useRef,useState} from 'react';
import {ExternalLink,MessageCircle,Minus} from 'lucide-react';

const KEY='episteme.chatgpt.url';
const DEFAULT='https://chatgpt.com/';
export function chatLink(value){
  try{
    const url=new URL(value.trim());
    if(url.protocol!=='https:'||url.hostname!=='chatgpt.com'||url.port||url.username||url.password)return null;
    return url.href;
  }catch{return null;}
}
export default function ChatGPTPanel(){
  const [open,setOpen]=useState(false),[url,setUrl]=useState(()=>{try{return chatLink(localStorage.getItem(KEY)||'')||DEFAULT;}catch{return DEFAULT;}}),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const trigger=useRef(null),input=useRef(null);
  useEffect(()=>{if(open)input.current?.focus();},[open]);
  function close(){setOpen(false);trigger.current?.focus();}
  function save(){
    const valid=chatLink(url);
    if(!valid){setError('Enter an HTTPS link on chatgpt.com, such as https://chatgpt.com/ or your conversation link.');input.current?.focus();return null;}
    setError('');setUrl(valid);
    try{localStorage.setItem(KEY,valid);setNotice('Link saved on this browser.');}catch{setNotice('Browser storage is unavailable. You can still open this link.');}
    return valid;
  }
  function launch(e){e.preventDefault();const valid=save();if(!valid)return;
    window.open(valid,'_blank','popup=yes,width=520,height=760,resizable=yes,scrollbars=yes,noopener,noreferrer');
    setNotice('Requested a ChatGPT window. If it did not open, use Open in new tab below.');
  }
  return <div className="chat-widget">
    {open&&<section className="chat-panel" id="chatgpt-panel" aria-label="ChatGPT companion" onKeyDown={e=>{if(e.key==='Escape'){e.stopPropagation();close();}}}>
      <header><div><MessageCircle size={20}/><strong>ChatGPT companion</strong></div><button type="button" onClick={close} aria-label="Minimize ChatGPT panel"><Minus size={20}/></button></header>
      <div className="chat-panel-body"><span className="eyebrow">YOUR LEARNING COMPANION</span><h2>Keep your tutor close.</h2><p>Open ChatGPT or return to your learning conversation. You control the chat.</p>
        <form onSubmit={launch}><label htmlFor="chatgpt-link">ChatGPT link</label><input ref={input} id="chatgpt-link" type="url" required value={url} onChange={e=>{setUrl(e.target.value);setError('');setNotice('');}} aria-invalid={!!error} aria-describedby={error?'chatgpt-error':'chatgpt-help'} placeholder="https://chatgpt.com/"/>
          <p id="chatgpt-help">Paste a conversation link, or use the homepage to start a new chat.</p>
          {error&&<p className="connection-error" id="chatgpt-error" role="alert">{error}</p>}
          <button className="chat-launch" type="submit">Open ChatGPT window <ExternalLink size={16}/></button>
          <div className="chat-actions"><button type="button" onClick={save}>Save link</button>{chatLink(url)&&<a href={chatLink(url)} target="_blank" rel="noopener noreferrer">Open in new tab <ExternalLink size={13}/></a>}</div>
        </form>
        <p role="status" className="chat-notice">{notice}</p><div className="chat-explanation">ChatGPT opens separately because its website cannot be embedded here. Your browser may open a tab instead of a window. Episteme does not read or send your messages.</div>
      </div>
    </section>}
    <button ref={trigger} type="button" className="chat-trigger" aria-expanded={open} aria-controls="chatgpt-panel" aria-label={open?'Minimize ChatGPT companion':'Open ChatGPT companion'} onClick={()=>open?close():setOpen(true)}><MessageCircle size={23}/><span>ChatGPT</span></button>
  </div>;
}
