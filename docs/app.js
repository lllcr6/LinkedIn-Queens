import {api} from './client.mjs';
'use strict';
const $ = id => document.getElementById(id);
const colors = ['#b9d8c7','#d7c6e8','#f2ceac','#adcfe3','#e8b8c4','#e4de9f','#bed2eb','#d3d8b8','#e8c5b1','#c3c4e3','#b6dedc','#e1badc'];
let regions = null, solutions = [], busy = false, catalog = null, generationJob = null;
function message(text, error = false) { $('message').textContent = text; $('message').classList.toggle('error', error); }
function refreshControls() {
  for (const id of ['generate','randomize','import','size','seed','generator','solver','unique']) $(id).disabled = busy;
  $('solve').disabled = busy || !regions; $('export').disabled = busy || !regions;
  $('show').disabled = busy || !solutions.length; $('solution').disabled = busy || solutions.length < 2;
}
function options() { return {solver:$('solver').value}; }
function clearSolutions() { solutions = []; $('show').checked = false; $('solution').replaceChildren(new Option('Solution 1','0')); }
function setSolutions(values) {
  solutions = values; $('solution').replaceChildren(...values.map((_,i) => new Option(`Solution ${i+1}`,String(i))));
  if (!values.length) $('solution').add(new Option('No solution','0'));
  $('show').checked = !!values.length;
}
function draw() {
  if (!regions) return;
  const n = regions.length, q = $('show').checked ? solutions[Number($('solution').value)] : null;
  const board = $('board'); board.classList.remove('empty'); board.style.gridTemplateColumns = `repeat(${n},1fr)`;
  board.replaceChildren();
  regions.forEach((row,i) => row.forEach((r,j) => {
    const cell = document.createElement('div'); cell.className = 'cell'; cell.style.background = colors[r % colors.length];
    const queen = q && q[i] === j;
    cell.setAttribute('aria-label',`Row ${i+1}, column ${j+1}, region ${r}${queen?', queen':''}`);
    cell.title = cell.getAttribute('aria-label');
    const label = document.createElement('span'); label.className = 'region'; label.textContent = r; cell.append(label);
    if (queen) { const icon = document.createElement('span'); icon.className = 'queen'; icon.textContent = '♛'; cell.append(icon); }
    if (j < n-1 && r !== row[j+1]) cell.style.borderRight = '2px solid #283e42';
    if (i < n-1 && r !== regions[i+1][j]) cell.style.borderBottom = '2px solid #283e42';
    board.append(cell);
  }));
  $('board-title').textContent = `${n} × ${n} Queens`;
}
async function run(task) {
  busy = true; refreshControls();
  try { await task(); } catch(error) { message(error.message, true); }
  finally { busy = false; refreshControls(); }
}
function showSolve(data) {
  if (data.status === 'limit') {
    clearSolutions(); $('classification').textContent = 'Unknown';
    for (const id of ['time','metric','extra']) $(id).textContent = '—';
    $('details').textContent = ''; draw();
    message('Search limit reached. Try another solver.',true); return;
  }
  setSolutions(data.solutions); draw();
  const labels = {none:'No solution',unique:'Unique solution',multiple:'Multiple solutions'};
  $('classification').textContent = labels[data.classification];
  $('time').textContent = data.elapsed_ms.toFixed(1)+' ms'; $('metric-label').textContent = 'Nodes / states'; $('metric').textContent = data.nodes.toLocaleString();
  $('extra-label').textContent = 'Cache hits'; $('extra').textContent = data.cache_hits.toLocaleString();
  $('details').textContent = data.classification === 'multiple' ? `${data.limit_reached ? 'At least ' : ''}${data.solutions.length} solutions found. Showing ${data.solutions.length}.` : '';
  message(`Result: ${labels[data.classification]}.`);
}
function formatTime(ms) { return ms < 1000 ? ms.toFixed(1) + ' ms' : (ms / 1000).toFixed(2) + ' s'; }
$('generate').onclick = () => run(async () => {
  const started = performance.now();
  $('generation-time').textContent = '0.00 s';
  const timer = setInterval(() => { $('generation-time').textContent = formatTime(performance.now() - started); }, 50);
  message($('unique').checked ? 'Generating and verifying uniqueness…' : 'Generating…');
  let finalElapsed = null;
  try {
    const job = await api('generation/start', {...options(),n:Number($('size').value),seed:Number($('seed').value),generator:$('generator').value,unique:$('unique').checked});
    generationJob = job.job_id;
    $('stop').hidden = false; $('stop').disabled = false; $('stop').textContent = 'Stop generation';
    let data;
    do {
      data = await api('generation/status', {job_id:generationJob});
      if (data.status === 'running') await new Promise(resolve => setTimeout(resolve, 100));
    } while (data.status === 'running');
    finalElapsed = data.elapsed_ms;
    if (data.status === 'cancelled') { message('Generation stopped.'); return; }
    if (data.status === 'error') throw new Error(data.message);
    if (data.status !== 'success') { message('No board found. Try another seed or generator.',true); return; }
    regions = data.regions; clearSolutions(); draw(); $('matrix').value = JSON.stringify(regions,null,2);
    $('classification').textContent = data.uniqueness_verified ? 'Uniqueness verified' : 'Solvable · uniqueness unchecked';
    $('time').textContent = '—'; $('metric-label').textContent = 'Attempts'; $('metric').textContent = data.attempts;
    $('extra-label').textContent = 'Repairs'; $('extra').textContent = data.repairs;
    $('details').textContent = `Seed ${data.seed} · ${data.solver_calls} solver calls`;
    message('Board generated. Select Solve board to find a solution.');
  } finally {
    clearInterval(timer);
    $('generation-time').textContent = formatTime(finalElapsed ?? performance.now() - started);
    // Also stop server work if polling failed or the connection was interrupted.
    if (generationJob) api('generation/cancel', {job_id:generationJob}).catch(() => {});
    generationJob = null; $('stop').hidden = true;
  }
});
$('stop').onclick = async () => {
  if (!generationJob) return;
  $('stop').disabled = true; $('stop').textContent = 'Stopping…';
  try { await api('generation/cancel', {job_id:generationJob}); }
  catch(error) { message(error.message, true); $('stop').disabled = false; $('stop').textContent = 'Stop generation'; }
};
window.addEventListener('pagehide', () => {
  if (generationJob) api('generation/cancel', {job_id:generationJob}).catch(() => {});
});
$('solve').onclick = () => run(async () => { message('Solving…'); showSolve(await api('solve',{...options(),regions})); });
$('import').onclick = () => run(async () => {
  const parsed = JSON.parse($('matrix').value);
  const input = Array.isArray(parsed) ? parsed : parsed?.regions;
  message('Validating and solving…');
  const data = await api('solve',{...options(),regions:input});
  regions = input; clearSolutions(); draw(); showSolve(data);
});
$('randomize').onclick = () => { const value = new Uint32Array(1); crypto.getRandomValues(value); $('seed').value = value[0]; };
$('show').onchange = draw; $('solution').onchange = draw;
$('export').onclick = () => {
  const blob = new Blob([JSON.stringify({regions,solutions},null,2)],{type:'application/json'});
  const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href=url; a.download='queens-puzzle.json'; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
};
function hints() {
  $('generator-hint').textContent = catalog.generators.find(x => x.key === $('generator').value).description;
  $('solver-hint').textContent = catalog.solvers.find(x => x.key === $('solver').value).description;
}
$('generator').onchange = hints; $('solver').onchange = hints;
(async () => {
  busy=true; refreshControls();
  try {
    catalog = {"solvers": [{"key": "backtracking", "name": "Backtracking", "description": "Row-by-row search; returns up to five solutions."}, {"key": "pruned", "name": "Forward-checking backtracking", "description": "Bitmasks with forward checking."}, {"key": "dp", "name": "Memoized DP", "description": "Memoizes column, region, and previous-column states."}], "generators": [{"key": "growth", "name": "Random growth + rejection", "description": "Grows connected regions; retries if uniqueness fails."}, {"key": "repair", "name": "Growth + counterexample repair", "description": "Adjusts boundaries to eliminate alternative solutions."}]};
    for (const [id,list] of [['solver',catalog.solvers],['generator',catalog.generators]]) $(id).replaceChildren(...list.map(x=>new Option(x.name,x.key)));
    $('solver').value='pruned'; $('generator').value='repair'; hints(); busy=false; refreshControls();
  } catch(error) { message('Could not initialize the browser app: '+error.message,true); }
})();
