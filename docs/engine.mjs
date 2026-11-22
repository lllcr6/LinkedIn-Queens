/** Browser-native strategies. Coordinates and region IDs are zero-based. */
export const SOLVERS = new Map();
export const GENERATORS = new Map();
export class SearchLimit extends Error {}
export class Budget {
  constructor(maxNodes = 500000) { this.nodes = 0; this.maxNodes = maxNodes; }
  tick() { if (++this.nodes > this.maxNodes) throw new SearchLimit('Search node limit reached.'); }
}
export function neighbors(cell, n) {
  const i = Math.floor(cell / n), j = cell % n, out = [];
  if (i) out.push(cell-n); if (i<n-1) out.push(cell+n);
  if (j) out.push(cell-1); if (j<n-1) out.push(cell+1);
  return out;
}
export function connected(cells,n) {
  if (!cells.size) return false;
  const stack = [cells.values().next().value], seen = new Set(stack);
  while (stack.length) for (const v of neighbors(stack.pop(),n)) {
    if (cells.has(v) && !seen.has(v)) { seen.add(v); stack.push(v); }
  }
  return seen.size === cells.size;
}
export function regionCells(board) {
  const n = board.length, regions = Array.from({length:n},()=>new Set());
  board.forEach((row,i)=>row.forEach((r,j)=>regions[r].add(i*n+j)));
  return regions;
}
export function validate(board) {
  if (!Array.isArray(board) || board.length<1 || board.length>12) throw new Error('Board size must be 1–12.');
  const n=board.length;
  if (board.some(row=>!Array.isArray(row)||row.length!==n||row.some(r=>!Number.isInteger(r)||r<0||r>=n))) throw new Error('Use a square matrix with integer region labels 0 to N−1.');
  if (regionCells(board).some(cells=>!connected(cells,n))) throw new Error('All N regions must be nonempty and orthogonally connected.');
  return board;
}
export function generationValid(board) {
  const sizes=regionCells(board).map(c=>c.size);
  return sizes.filter(s=>s===1).length<=1 && Math.max(...sizes)<=Math.floor(board.length**2/2);
}
export function accepts(board,q) {
  const n=board.length;
  return q.length===n && q.every(c=>Number.isInteger(c)&&c>=0&&c<n) && new Set(q).size===n
    && q.every((c,i)=>!i||Math.abs(c-q[i-1])!==1) && new Set(q.map((c,i)=>board[i][c])).size===n;
}
function report(solutions,start,budget,before,limit,hits=0) {
  return {status:'success',solutions,classification:solutions.length===0?'none':solutions.length===1?'unique':'multiple',
    elapsed_ms:performance.now()-start,nodes:budget.nodes-before,cache_hits:hits,limit_reached:solutions.length===limit};
}
function backtrack(board,budget,limit,forward) {
  const start=performance.now(),before=budget.nodes,n=board.length,full=(1<<n)-1,solutions=[],q=[];
  function viable(row,cols,regions) {
    let pc=0,pr=0;
    for(let i=row;i<n;i++) {
      let found=false;
      for(let c=0;c<n;c++) {
        const r=board[i][c];
        if ((cols&(1<<c)) || (regions&(1<<r)) || (i===row&&q.length&&Math.abs(c-q.at(-1))===1)) continue;
        found=true;pc|=1<<c;pr|=1<<r;
      }
      if(!found)return false;
    }
    return (pc|cols)===full&&(pr|regions)===full;
  }
  function visit(row,cols,regions) {
    budget.tick();
    if(row===n){solutions.push([...q]);return;}
    if(forward&&!viable(row,cols,regions))return;
    for(let c=0;c<n;c++) {
      const r=board[row][c];
      if((cols&(1<<c))||(regions&(1<<r))||(q.length&&Math.abs(c-q.at(-1))===1))continue;
      q.push(c);visit(row+1,cols|(1<<c),regions|(1<<r));q.pop();
      if(solutions.length===limit)return;
    }
  }
  visit(0,0,0);return report(solutions,start,budget,before,limit);
}
function dp(board,budget,limit) {
  const start=performance.now(),before=budget.nodes,n=board.length,cache=new Map();let hits=0,states=0;
  function visit(cols,regions,prev,row) {
    const key=`${cols},${regions},${prev}`;
    if(cache.has(key)){hits++;return cache.get(key);}
    budget.tick();if(++states>100000)throw new SearchLimit('DP state limit reached.');
    if(row===n)return [[]];
    const answers=[];
    outer:for(let c=0;c<n;c++) {
      const r=board[row][c];
      if((cols&(1<<c))||(regions&(1<<r))||(prev>=0&&Math.abs(c-prev)===1))continue;
      for(const suffix of visit(cols|(1<<c),regions|(1<<r),c,row+1)) {
        answers.push([c,...suffix]);if(answers.length===limit)break outer;
      }
    }
    cache.set(key,answers);return answers;
  }
  return report(visit(0,0,-1,0),start,budget,before,limit,hits);
}
SOLVERS.set('backtracking',(b,budget,limit)=>backtrack(b,budget,limit,false));
SOLVERS.set('pruned',(b,budget,limit)=>backtrack(b,budget,limit,true));
SOLVERS.set('dp',dp);
export function solve(board,key='pruned',budget=new Budget(),limit=5) {
  validate(board);if(!SOLVERS.has(key))throw new Error('Unknown solver.');
  return SOLVERS.get(key)(board,budget,limit);
}
/** Mulberry32: stable within the JS edition, not Python's random sequence. */
export function random(seed) {
  let state=seed>>>0;
  return ()=>{let t=state+=0x6D2B79F5;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return ((t^(t>>>14))>>>0)/4294967296;};
}
function pick(items,rng){return items[Math.floor(rng()*items.length)];}
function shuffle(items,rng){for(let i=items.length-1;i>0;i--){const j=Math.floor(rng()*(i+1));[items[i],items[j]]=[items[j],items[i]];}return items;}
function seedPlacement(n,rng,budget) {
  const q=[];
  function visit(used) {
    budget.tick();if(q.length===n)return [...q];
    for(const c of shuffle(Array.from({length:n},(_,i)=>i),rng)) {
      if((used&(1<<c))||(q.length&&Math.abs(c-q.at(-1))===1))continue;
      q.push(c);const answer=visit(used|(1<<c));if(answer)return answer;q.pop();
    }
    return null;
  }
  return visit(0);
}
function grow(n,q,rng,budget) {
  const cells=q.map((c,i)=>new Set([i*n+c])),free=new Set(Array.from({length:n*n},(_,i)=>i)),cap=Math.floor(n*n/2);
  cells.forEach(c=>free.delete(c.values().next().value));
  while(free.size) {
    budget.tick();
    const fronts=cells.map(c=>c.size>=cap?[]:[...new Set([...c].flatMap(v=>neighbors(v,n)).filter(v=>free.has(v)))]);
    const singles=cells.map((c,r)=>c.size===1?r:-1).filter(r=>r>=0);
    if(singles.filter(r=>!fronts[r].length).length>1)return null;
    const options=fronts.map((f,r)=>f.length?r:-1).filter(r=>r>=0);if(!options.length)return null;
    const urgent=singles.length>1?singles.filter(r=>fronts[r].length):[];
    let r;
    if(urgent.length)r=pick(urgent,rng);
    else {let weight=rng()*options.reduce((s,r)=>s+1/cells[r].size,0);r=options.at(-1);for(const option of options){weight-=1/cells[option].size;if(weight<=0){r=option;break;}}}
    const cell=pick(fronts[r].sort((a,b)=>a-b),rng);cells[r].add(cell);free.delete(cell);
  }
  const board=Array.from({length:n},()=>Array(n).fill(-1));cells.forEach((c,r)=>c.forEach(v=>board[Math.floor(v/n)][v%n]=r));
  return generationValid(board)?board:null;
}
function repair(board,q,alt,rng,budget) {
  const n=board.length,cells=regionCells(board),seeds=new Set(q.map((c,i)=>i*n+c));
  const candidates=shuffle(alt.map((c,i)=>i*n+c).filter(v=>!seeds.has(v)),rng);
  for(const cell of candidates) {
    budget.tick();const i=Math.floor(cell/n),j=cell%n,source=board[i][j];
    const targets=shuffle([...new Set(neighbors(cell,n).map(v=>board[Math.floor(v/n)][v%n]))].filter(r=>r!==source),rng);
    for(const target of targets) {
      if(cells[target].size>=Math.floor(n*n/2))continue;
      const remaining=new Set(cells[source]);remaining.delete(cell);if(!connected(remaining,n))continue;
      const changed=board.map(row=>[...row]);changed[i][j]=target;
      if(generationValid(changed)&&!accepts(changed,alt))return changed;
    }
  }
  return null;
}
function generateWithRepair(data,steps,budget,maxAttempts=Infinity) {
  const {n,seed,unique=true,solver='pruned'}=data,start=performance.now(),rng=random(seed);
  let attempts=0,repairs=0,solverCalls=0;
  while(attempts<maxAttempts) {
    attempts++;const q=seedPlacement(n,rng,budget);if(!q)return {status:'infeasible'};
    let board=grow(n,q,rng,budget);if(!board)continue;
    const result=()=>({status:'success',regions:board,witness:q,uniqueness_verified:unique,attempts,repairs,solver_calls:solverCalls,elapsed_ms:performance.now()-start,seed});
    if(!unique)return result();
    const seen=new Set([JSON.stringify(board)]);
    for(let step=0;step<=steps;step++) {
      solverCalls++;const answer=solve(board,solver,budget,2);
      if(answer.classification==='unique')return result();
      if(!answer.solutions.length)throw new Error('Seed solution was lost.');
      if(step===steps)break;
      const alternate=answer.solutions.find(x=>x.some((c,i)=>c!==q[i]));
      const changed=repair(board,q,alternate,rng,budget);if(!changed)break;
      const key=JSON.stringify(changed);if(seen.has(key))break;
      seen.add(key);board=changed;repairs++;
    }
  }
  return {status:'not_found',attempts,repairs,solver_calls:solverCalls,elapsed_ms:performance.now()-start};
}
GENERATORS.set('growth',(d,b,m)=>generateWithRepair(d,0,b,m));
GENERATORS.set('repair',(d,b,m)=>generateWithRepair(d,30,b,m));
export function generate(data,budget=new Budget(Infinity),maxAttempts=Infinity) {
  if(!Number.isInteger(data.n)||data.n<4||data.n>12)throw new Error('Board size must be 4–12.');
  if(!Number.isInteger(data.seed)||data.seed<0||data.seed>4294967295)throw new Error('Seed must be an integer from 0 to 4294967295.');
  if(data.unique!==undefined&&typeof data.unique!=='boolean')throw new Error('unique must be a Boolean.');
  if(!SOLVERS.has(data.solver||'pruned'))throw new Error('Unknown solver.');
  const strategy=GENERATORS.get(data.generator||'repair');if(!strategy)throw new Error('Unknown generator.');
  return strategy(data,budget,maxAttempts);
}
