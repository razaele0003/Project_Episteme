import React from 'react';
import {ArrowRight,CheckCircle2,Circle,Code2,Layers3,Map as MapIcon,ShieldCheck,Sparkles,Trophy} from 'lucide-react';

const PHASE_SKILLS={
  0:['Development environment','Git and GitHub','Configuration','Debugging'],
  1:['Functions','Decision logic','Validation','Batch processing'],
  2:['Software design','Testing','Packaging','Logging'],
  3:['CSV and JSON','Data cleaning','Pandas','File automation'],
  4:['HTTP','Requests','Status handling','Web architecture'],
  5:['REST APIs','Authentication','Pagination','Webhooks'],
  6:['SQL','Data modeling','Transactions','Persistent state'],
  7:['n8n workflows','Routing','Retries','Audit trails'],
  8:['Process analysis','Approvals','Operations','Business KPIs'],
  9:['CRM systems','GoHighLevel','Lead operations','Synchronization'],
  10:['JavaScript','TypeScript','Async programming','Code nodes'],
  11:['LLM prompting','Structured output','Classification','AI evaluation'],
  12:['AI workflows','Document extraction','AI operations','Human review'],
  13:['Embeddings','Vector search','RAG','Grounded citations'],
  14:['Tool calling','Agents','Memory','Agent evaluation'],
  15:['Message queues','State machines','Distributed workflows','Recovery'],
  16:['Unit tests','Integration tests','LLM evaluation','Chaos testing'],
  17:['Secrets','Access control','Injection defense','Data privacy'],
  18:['Docker','Deployment','Cloud infrastructure','Continuous delivery'],
  19:['Observability','Monitoring','Alerting','Reliability'],
  20:['Discovery','Architecture','ROI','Client delivery']
};

export function currentCurriculumProject(projects){
  return projects.find(project=>!project.historical&&project.status!=='completed')||projects.find(project=>!project.historical);
}

function phases(projects){
  const grouped=new globalThis.Map();
  projects.filter(project=>!project.historical&&Number.isInteger(project.phase)).forEach(project=>{
    if(!grouped.has(project.phase))grouped.set(project.phase,[]);
    grouped.get(project.phase).push(project);
  });
  return [...grouped].sort(([a],[b])=>a-b).map(([number,items])=>({number,items,title:items[0]?.phase_title||`Phase ${number}`,completed:items.filter(item=>item.status==='completed').length}));
}

export function ContinueLearning({projects,openProject}){
  const current=currentCurriculumProject(projects);
  if(!current)return null;
  const phaseProjects=projects.filter(project=>project.phase===current.phase&&!project.historical);
  const done=phaseProjects.filter(project=>project.status==='completed').length;
  const skills=PHASE_SKILLS[current.phase]||[current.concept];
  return <section className="continue-learning"><div className="continue-copy"><span className="eyebrow">WHAT YOU'RE LEARNING NOW</span><h2>{current.concept||current.title}</h2><p>{current.description||`Build the core skills for ${current.phase_title}.`}</p><div className="current-path"><span>{current.phase_title}</span><ArrowRight size={14}/><span>{skills[0]}</span><ArrowRight size={14}/><strong>{current.id} · You are here</strong></div></div><div className="continue-action"><small>CURRENT PROJECT</small><strong>{current.title}</strong><span>{done} of {phaseProjects.length} projects have repository evidence</span><button onClick={()=>openProject(current.id)}>Continue project <ArrowRight size={16}/></button></div></section>;
}

export function RoadmapPage({projects,openProject}){
  const rows=phases(projects);
  const active=rows.find(row=>row.completed<row.items.length)?.number;
  return <section className="learning-page"><div className="learning-intro"><MapIcon size={23}/><div><span className="eyebrow">AI AUTOMATION ENGINEER</span><h2>Your learning roadmap</h2><p>Each phase follows the same learning cycle and ends with work you can prove from your repository.</p></div></div><div className="learning-cycle">{['Learn','Practice','Build','Prove','Advance'].map((step,index)=><React.Fragment key={step}><span>{step}</span>{index<4&&<ArrowRight size={14}/>}</React.Fragment>)}</div><div className="phase-list">{rows.map(row=>{const percent=row.items.length?Math.round(row.completed/row.items.length*100):0;const first=row.items.find(item=>item.status!=='completed')||row.items[0];const destination=row.items[row.items.length-1];return <article className={'phase-card '+(row.number===active?'active':'')} key={row.number}><span className="phase-number">{row.completed===row.items.length?<CheckCircle2 size={20}/>:row.number===active?<Sparkles size={20}/>:<Circle size={20}/>}</span><div className="phase-content"><small>PHASE {row.number}</small><h3>{row.title.replace(/^Phase \d+:?\s*/,'')}</h3><p>{PHASE_SKILLS[row.number]?.join(' · ')}</p><div className="phase-destination"><strong>Phase destination</strong><span>{destination.id} · {destination.title}</span></div><progress max="100" value={percent}/><span>{row.completed} of {row.items.length} projects with complete evidence</span></div><button onClick={()=>openProject(first.id)}>{row.number===active?'Continue':'View phase'}<ArrowRight size={15}/></button></article>})}</div></section>;
}

export function SkillsPage({projects}){
  const rows=phases(projects);
  return <section className="learning-page"><div className="learning-intro"><Layers3 size={23}/><div><span className="eyebrow">SKILL EVIDENCE</span><h2>What your work demonstrates</h2><p>These bars summarize complete repository evidence by phase. They do not claim mastery or independent ability.</p></div></div><div className="skills-grid">{rows.map(row=>{const percent=row.items.length?Math.round(row.completed/row.items.length*100):0;return <article className="skill-card" key={row.number}><header><div><small>PHASE {row.number}</small><h3>{row.title.replace(/^Phase \d+:?\s*/,'')}</h3></div><strong>{percent}%</strong></header><progress max="100" value={percent}/><div className="skill-tags">{(PHASE_SKILLS[row.number]||[]).map(skill=><span key={skill}>{skill}</span>)}</div><p>{row.completed?`${row.completed} projects contain the required BRIEF, solution, and README evidence.`:'No complete project evidence recorded yet.'}</p></article>})}</div></section>;
}

export function PortfolioPage({projects,openProject}){
  const completed=projects.filter(project=>project.status==='completed'&&project.structure_ready);
  return <section className="learning-page"><div className="learning-intro"><Trophy size={23}/><div><span className="eyebrow">PORTFOLIO EVIDENCE</span><h2>Work ready to inspect</h2><p>Only projects with the complete folder structure appear here.</p></div></div>{completed.length?<div className="portfolio-grid">{completed.map(project=><button key={project.id} onClick={()=>openProject(project.id)}><ShieldCheck size={22}/><small>{project.category}</small><strong>{project.title}</strong><span>Open evidence <ArrowRight size={14}/></span></button>)}</div>:<div className="portfolio-empty"><Code2 size={30}/><h3>Your portfolio starts with complete evidence.</h3><p>Create a project folder containing <code>BRIEF.md</code>, <code>main.py</code>, and <code>README.md</code>, map it, push it, and sync.</p></div>}</section>;
}

