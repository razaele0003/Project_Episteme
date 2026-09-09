import {browserWorkspace} from './workspace.js';
import React, {useEffect,useState} from 'react';
import {Github} from 'lucide-react';

const headers={'X-Episteme-Client':'dashboard'};
async function api(path,method='GET'){
  const response=await fetch('/api/github/'+path,{method,headers});
  const body=await response.json();
  if(!response.ok)throw new Error(body.detail||'GitHub is unavailable. Please try again.');
  return body;
}
function LocalGitHubAccount({onSelect,disabled}){
  const [account,setAccount]=useState(null),[repos,setRepos]=useState([]),[page,setPage]=useState(0),[more,setMore]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[query,setQuery]=useState('');
  async function list(next=1){setBusy(true);setError('');try{const data=await api('repositories?page='+next);setRepos(old=>next===1?data.items:[...old,...data.items]);setPage(next);setMore(data.has_more);}catch(e){setError(e.message);}finally{setBusy(false);}}
  useEffect(()=>{api('status').then(a=>{setAccount(a);if(a.signed_in)list();}).catch(e=>setError(e.message));
    const result=new URLSearchParams(location.search).get('github');
    if(result==='failed'||result==='cancelled')setError(result==='cancelled'?'GitHub sign-in was cancelled.':'GitHub sign-in failed. Please try again.');
    if(result)history.replaceState(null,'',location.pathname+location.hash);
  },[]);
  async function login(){setBusy(true);setError('');try{const result=await api('login','POST');location.assign(result.url);}catch(e){setError(e.message);setBusy(false);}}
  async function logout(){setBusy(true);try{await api('logout','POST');setAccount(await api('status'));setRepos([]);setMore(false);}catch(e){setError(e.message);}finally{setBusy(false);}}
  return <section className="github-account" aria-label="GitHub account">
    <div className="account-heading"><Github size={20}/><div><strong>{account?.signed_in?'Signed in as '+account.login:'Connect your GitHub account'}</strong><p>{account?.signed_in?'Pick a public repository below, then connect and sync it.':'Sign in to choose a repository, or enter its URL below.'}</p></div></div>
    {error&&<p className="connection-error" role="alert">{error}</p>}
    {account?.signed_in?<><button type="button" className="sync-button" onClick={logout} disabled={busy||disabled}>Sign out of Episteme</button><label className="repo-search">Find a repository<input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Filter loaded repositories"/></label><div className="repo-options">{repos.filter(r=>r.full_name.toLowerCase().includes(query.toLowerCase())).map(r=><button type="button" disabled={disabled} key={r.full_name} onClick={()=>onSelect(r.full_name)}>{r.full_name}</button>)}{!busy&&!repos.some(r=>r.full_name.toLowerCase().includes(query.toLowerCase()))&&<p>No matching public repositories loaded.</p>}</div>{more&&<button className="sync-button" type="button" disabled={busy} onClick={()=>list(page+1)}>Load more repositories</button>}{busy&&<p role="status">Loading GitHub…</p>}</>:
      account?.configured?<button className="sync-button" type="button" disabled={busy||disabled} onClick={login}>{busy?'Opening GitHub…':'Sign in with GitHub'}</button>:
      account&&<details className="oauth-setup"><summary>Enable GitHub sign-in · one-time setup</summary><p>Episteme needs a registered GitHub OAuth app before sign-in can work. You can still sync any public repository using its URL.</p><p>Register the app with callback <code>{account.callback}</code>, then set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in the backend environment and restart. Keep the secret out of this form.</p><a href="https://github.com/settings/applications/new" target="_blank" rel="noreferrer">Register a GitHub OAuth app</a></details>}
  </section>;
}

export default function GitHubAccount(props){
  return browserWorkspace?<section className="github-account"><div className="account-heading"><Github size={20}/><div><strong>Connect a public repository</strong><p>Paste its GitHub URL below. No login or token is needed. Private repositories are not supported in this free browser workspace.</p></div></div></section>:<LocalGitHubAccount {...props}/>;
}
