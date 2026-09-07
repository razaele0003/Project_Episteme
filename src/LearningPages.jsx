import React from 'react';
import {ArrowLeft,ArrowRight,CheckCircle2,Circle,Code2,FolderGit2,Github,Layers3,Map as MapIcon,PackageCheck,ShieldCheck,Sparkles,Terminal,Trophy} from 'lucide-react';

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
  const buildProjects=projects.filter(project=>!project.historical&&project.phase!==0);
  return buildProjects.find(project=>project.status!=='completed')||buildProjects[0];
}

function phases(projects){
  const grouped=new globalThis.Map();
  projects.filter(project=>!project.historical&&Number.isInteger(project.phase)&&project.phase!==0).forEach(project=>{
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

export function SetupBanner({openSetup}){
  return <section className="setup-banner"><div><span className="setup-number">0</span><div><span className="eyebrow">BEFORE YOUR FIRST PROJECT</span><h2>Prepare your practice repository</h2><p>Install the tools, create the repository, connect GitHub, and learn the submission commands. This setup does not count as a project.</p></div></div><button onClick={openSetup}>Open setup guide <ArrowRight size={15}/></button></section>;
}

const SETUP_STEPS=[
  {icon:Terminal,title:'1. Check Python and Git',body:'Open PowerShell and confirm that both tools are available.',commands:['python --version','git --version']},
  {icon:FolderGit2,title:'2. Create the practice repository',body:'Create one workspace, initialize Git, and add the folders Episteme will use.',commands:['mkdir Practice','cd Practice','git init','mkdir projects','mkdir .episteme','New-Item .gitignore -ItemType File']},
  {icon:PackageCheck,title:'3. Prepare the Python environment',body:'Create an isolated environment, activate it, and install the basic quality tools.',commands:['python -m venv .venv','.\\.venv\\Scripts\\Activate.ps1','python -m pip install --upgrade pip','python -m pip install pytest ruff flake8']},
  {icon:Github,title:'4. Connect and push to GitHub',body:'Create an empty GitHub repository named python-practice, then connect and submit the setup.',commands:['git add .','git commit -m "chore: initialize practice repository"','git branch -M main','git remote add origin https://github.com/YOUR-USERNAME/python-practice.git','git push -u origin main']},
];

export function SetupGuide({repository,onBack}){
  return <section className="setup-guide"><button className="back-button" onClick={onBack}><ArrowLeft size={16}/>Back to roadmap</button><div className="setup-hero"><span className="setup-number">0</span><div><span className="eyebrow">PREPARATION · NO PROJECT SUBMISSION</span><h1>Get ready to build</h1><p>Complete these steps once before starting the curriculum. Phase 0 is a guide, so it never changes your project percentage.</p></div></div><div className="setup-steps">{SETUP_STEPS.map(({icon:Icon,title,body,commands})=><article key={title}><Icon size={21}/><div><h2>{title}</h2><p>{body}</p><pre>{commands.join('\n')}</pre></div></article>)}</div><article className="submission-guide"><span className="eyebrow">HOW TO SUBMIT EVERY PROJECT</span><h2>Build, test, push, then sync</h2><div>{[['1','Create',<>Make <code>projects/&lt;project-id&gt;/</code> with <code>BRIEF.md</code>, <code>main.py</code>, and <code>README.md</code>, then map that folder in <code>.episteme/projects.json</code>.</>],['2','Test',<>Run <code>python projects/&lt;project-id&gt;/main.py</code> and <code>python -m pytest</code>.</>],['3','Push',<>Run <code>git add .</code>, <code>git commit -m "feat: complete &lt;project-id&gt;"</code>, then <code>git push</code>.</>],['4','Sync',<>Return to Episteme and select <strong>Sync repository</strong>. The project bar moves only after all required files are on GitHub.</>]].map(([n,title,text])=><section key={n}><span>{n}</span><div><strong>{title}</strong><p>{text}</p></div></section>)}</div><p className="connected-repo">Connected repository: <strong>{repository||'Choose one in Settings'}</strong></p></article></section>;
}

export function RoadmapPage({projects,openProject,openSetup}){
  const rows=phases(projects);
  const active=rows.find(row=>row.completed<row.items.length)?.number;
  return <section className="learning-page"><div className="learning-intro"><MapIcon size={23}/><div><span className="eyebrow">AI AUTOMATION ENGINEER</span><h2>Your learning roadmap</h2><p>Start with repository preparation, then complete each learning phase through work you can prove.</p></div></div><SetupBanner openSetup={openSetup}/><div className="learning-cycle">{['Learn','Practice','Build','Prove','Advance'].map((step,index)=><React.Fragment key={step}><span>{step}</span>{index<4&&<ArrowRight size={14}/>}</React.Fragment>)}</div><div className="phase-list">{rows.map(row=>{const percent=row.items.length?Math.round(row.completed/row.items.length*100):0;const first=row.items.find(item=>item.status!=='completed')||row.items[0];const destination=row.items[row.items.length-1];return <article className={'phase-card '+(row.number===active?'active':'')} key={row.number}><span className="phase-number">{row.completed===row.items.length?<CheckCircle2 size={20}/>:row.number===active?<Sparkles size={20}/>:<Circle size={20}/>}</span><div className="phase-content"><small>PHASE {row.number}</small><h3>{row.title.replace(/^Phase \d+:?\s*/,'')}</h3><p>{PHASE_SKILLS[row.number]?.join(' · ')}</p><div className="phase-destination"><strong>Phase destination</strong><span>{destination.id} · {destination.title}</span></div><progress max="100" value={percent}/><span>{row.completed} of {row.items.length} projects with complete evidence</span></div><button onClick={()=>openProject(first.id)}>{row.number===active?'Continue':'View phase'}<ArrowRight size={15}/></button></article>})}</div></section>;
}

export function SkillsPage({projects}){
  const rows=phases(projects);
  return <section className="learning-page"><div className="learning-intro"><Layers3 size={23}/><div><span className="eyebrow">SKILL EVIDENCE</span><h2>What your work demonstrates</h2><p>These bars summarize complete repository evidence by phase. They do not claim mastery or independent ability.</p></div></div><div className="skills-grid">{rows.map(row=>{const percent=row.items.length?Math.round(row.completed/row.items.length*100):0;return <article className="skill-card" key={row.number}><header><div><small>PHASE {row.number}</small><h3>{row.title.replace(/^Phase \d+:?\s*/,'')}</h3></div><strong>{percent}%</strong></header><progress max="100" value={percent}/><div className="skill-tags">{(PHASE_SKILLS[row.number]||[]).map(skill=><span key={skill}>{skill}</span>)}</div><p>{row.completed?`${row.completed} projects contain the required BRIEF, solution, and README evidence.`:'No complete project evidence recorded yet.'}</p></article>})}</div></section>;
}

export function PortfolioPage({projects,openProject}){
  const completed=projects.filter(project=>!project.historical&&project.phase!==0&&project.status==='completed'&&project.structure_ready);
  return <section className="learning-page"><div className="learning-intro"><Trophy size={23}/><div><span className="eyebrow">PORTFOLIO EVIDENCE</span><h2>Work ready to inspect</h2><p>Only projects with the complete folder structure appear here.</p></div></div>{completed.length?<div className="portfolio-grid">{completed.map(project=><button key={project.id} onClick={()=>openProject(project.id)}><ShieldCheck size={22}/><small>{project.category}</small><strong>{project.title}</strong><span>Open evidence <ArrowRight size={14}/></span></button>)}</div>:<div className="portfolio-empty"><Code2 size={30}/><h3>Your portfolio starts with complete evidence.</h3><p>Create a project folder containing <code>BRIEF.md</code>, <code>main.py</code>, and <code>README.md</code>, map it, push it, and sync.</p></div>}</section>;
}
