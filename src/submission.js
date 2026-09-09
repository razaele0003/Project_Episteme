// Submission guidance is separate from the unchanged curriculum and source checks.
const visualProjects = new Set([
  ...Array.from({length:45},(_,index)=>`P${69+index}`),
  'P116','P193','P195','P196',
  ...Array.from({length:8},(_,index)=>`P${199+index}`)
]);

export function preferredSubmission(project){
  return !project.historical && visualProjects.has(project.id) ? 'screenshots' : 'github';
}

export function reviewPrompt(project, mode){
  if(mode==='screenshots')return `Review ${project.id} — ${project.title}. I will attach screenshots or photos of my workflow, configuration, document, or result here. Compare them with this brief: ${(project.instructions||[]).join(' ')} Ask for any missing evidence before deciding whether it is correct, then guide me through explaining my work.`;
  const repository=project.repository||'OWNER/REPOSITORY';
  const commit=project.sha?` at commit ${project.sha}`:'';
  return `Review ${project.id} — ${project.title} in my GitHub repository ${repository}${commit}. Verify my work and guide me through the next step.`;
}
