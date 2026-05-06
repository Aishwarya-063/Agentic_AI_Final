import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Check, Compass, Home, Image, MessageSquare, Send, ShieldAlert, Sparkles, PawPrint, Coffee, Clock, ClipboardList } from 'lucide-react';
import './styles.css';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8002';

const DEFAULT_AGENT_STATES = {
  profile_parser: { id: 'profile_parser', name: 'Profile Parser Agent', status: 'Waiting to start', progress: 0, done: false },
  neighborhood_fit: { id: 'neighborhood_fit', name: 'Neighborhood Fit Agent', status: 'Waiting to start', progress: 0, done: false },
  vibe_analyst: { id: 'vibe_analyst', name: 'Vibe Analyst Agent', status: 'Waiting to start', progress: 0, done: false },
  apartment_scout: { id: 'apartment_scout', name: 'Apartment Scout Agent', status: 'Waiting to start', progress: 0, done: false },
  checklist: { id: 'checklist', name: 'Moving Checklist Agent', status: 'Waiting to start', progress: 0, done: false },
};

const fallbackQuestions = [
  { id: 'profile_type', question: 'Which relocation profile best matches you?', helper: 'Remote worker, young family, career relocator, or empty nester' },
  { id: 'destination', question: 'Where are you moving?', helper: 'Example: Chicago, Austin, New York' },
  { id: 'budget', question: 'What is your monthly rent budget?', helper: 'Example: 1800' },
  { id: 'move_timeline', question: 'When are you moving?', helper: 'Example: in 6 weeks, next month, August 1' },
  { id: 'work_style', question: 'What is your work situation?', helper: 'Remote, hybrid, or in-office?' },
  { id: 'pets', question: 'Any pets coming with you?', helper: 'Example: one dog, two cats, no pets' },
  { id: 'lifestyle', question: 'What kind of lifestyle do you want nearby?', helper: 'Example: coffee shops, parks, quiet streets, nightlife, walkability' },
  { id: 'dealbreakers', question: 'What are your dealbreakers?', helper: 'Example: noise, long commute, unsafe at night, no parking' },
];

function App() {
  const [screen, setScreen] = useState('onboarding');
  const [sessionId, setSessionId] = useState(null);
  const [results, setResults] = useState(null);

  return <div className="app-shell">
    <Texture />
    {screen === 'onboarding' && <Onboarding onComplete={(id) => { setSessionId(id); setScreen('atlas'); }} />}
    {screen === 'atlas' && <Atlas sessionId={sessionId} results={results} setResults={setResults} />}
  </div>
}

function Texture(){ return <div className="texture" /> }

function Onboarding({ onComplete }) {
  const [questions, setQuestions] = useState(fallbackQuestions);
  const [step, setStep] = useState(0);
  const [input, setInput] = useState('');
  const [answers, setAnswers] = useState({});
  const [messages, setMessages] = useState([{ role: 'agent', text: 'Welcome to NestIQ. I’ll ask a few questions, then the agents will build your relocation atlas.' }]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API}/api/onboarding/questions`)
      .then(r => {
        if (!r.ok) throw new Error(`Failed to load onboarding questions: ${r.status}`);
        return r.json();
      })
      .then(d => {
        if (d?.questions?.length) {
          setQuestions(d.questions);
        }
      })
      .catch(() => {
        setQuestions(fallbackQuestions);
      });
  }, []);
  useEffect(() => {
    const q = questions?.[step];
    if (!q) return;
    if (messages[messages.length - 1]?.text !== q.question) {
      setMessages(m => [...m, { role: 'agent', text: q.question, helper: q.helper }]);
    }
  }, [step, questions, messages]);

  const tags = useMemo(() => Object.entries(answers).map(([k,v]) => ({ k: k.replaceAll('_',' '), v })), [answers]);

  async function submitAnswer(e) {
    e.preventDefault();
    if (!input.trim()) return;
    const q = questions[step];
    let value = input.trim();
    if (q.id === 'budget') {
      const num = Number(value.replace(/[^0-9]/g, ''));
      value = num || 1800;
    }
    const nextAnswers = { ...answers, [q.id]: value };
    setAnswers(nextAnswers);
    setMessages(m => [...m, { role: 'user', text: input.trim() }]);
    setInput('');
    if (step < questions.length - 1) {
      setStep(s => s + 1);
    } else {
      setLoading(true);
      setError(null);
      setMessages(m => [...m, { role: 'agent', text: 'Great. I have enough to send this to the relocation agents.' }]);
      try {
        const res = await fetch(`${API}/api/profile`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(nextAnswers) });
        if (!res.ok) throw new Error(`Backend error ${res.status}`);
        const data = await res.json();
        onComplete(data.session_id);
      } catch (err) {
        setLoading(false);
        setError('Unable to start the atlas. Please refresh and try again.');
        setMessages(m => [...m, { role: 'agent', text: 'Oops. I could not connect to the relocation agents. Please try again.' }]);
      }
    }
  }

  return <main className="landing grid-two">
    <section className="hero-copy">
      <p className="label">NESTIQ LITE</p>
      <h1>The relocation concierge that works like a small team.</h1>
      <p className="lead">Answer one question at a time. Then watch specialized agents build a neighborhood shortlist, vibe analysis, apartment scout, and moving checklist.</p>
      <div className="tag-strip">{tags.map(t => <span key={t.k}><b>{t.k}</b>: {String(t.v)}</span>)}</div>
      {error && <div className="error-banner">{error}</div>}
    </section>
    <section className="chat-panel">
      <div className="chat-window">
        {messages.map((m,i) => <motion.div initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} key={i} className={`msg ${m.role}`}>
          <p>{m.text}</p>{m.helper && <small>{m.helper}</small>}
        </motion.div>)}
      </div>
      <form onSubmit={submitAnswer} className="chat-input">
        <input value={input} onChange={e => setInput(e.target.value)} disabled={loading} placeholder={loading ? 'Preparing atlas...' : 'Type your answer...'} />
        <button disabled={loading}><Send size={18}/></button>
      </form>
    </section>
  </main>
}

function Atlas({ sessionId, results, setResults }) {
  const [agents, setAgents] = useState(DEFAULT_AGENT_STATES);
  const [complete, setComplete] = useState(false);
  const [error, setError] = useState(null);
  const [chat, setChat] = useState([{ role:'agent', text:'Ask me about a neighborhood, safety, best fit, or landlord emails.' }]);
  const [chatInput, setChatInput] = useState('');

  function downloadReport() {
    if (!results) return;
    const lines = [];
    const profile = results.profile;
    lines.push(`NestIQ Move Report`);
    lines.push(`Profile: ${profile.profile_type}`);
    lines.push(`Destination: ${profile.destination_city}`);
    lines.push(`Budget: $${profile.monthly_budget}`);
    lines.push(`Work style: ${profile.work_style}`);
    lines.push(`Pets: ${profile.pets}`);
    lines.push(`Timeline: ${profile.move_timeline}`);
    lines.push(`Lifestyle priorities: ${profile.lifestyle_priorities.join(', ')}`);
    lines.push(`Dealbreakers: ${profile.dealbreakers.join(', ')}`);
    lines.push('');
    lines.push('Neighborhoods:');
    results.neighborhoods.forEach(n => {
      lines.push(`- ${n.name}: Fit ${n.score}/100`);
      lines.push(`  ${n.justification}`);
      lines.push(`  Vibe: ${n.vibe}`);
      lines.push('');
    });
    lines.push('Listings:');
    results.listings.forEach(l => {
      lines.push(`- ${l.title} (${l.neighborhood})`);
      lines.push(`  Cost: $${l.true_monthly_cost} (${l.cost_breakdown.rent} rent + ${l.cost_breakdown.utilities} utilities + ${l.cost_breakdown.pet_fee} pet + $18 insurance)`);
      if (l.red_flags.length) lines.push(`  Red flags: ${l.red_flags.join(', ')}`);
      lines.push(`  Outreach: ${l.outreach}`);
      lines.push('');
    });
    lines.push('Checklist:');
    results.checklist.forEach(t => {
      lines.push(`- ${t.when}: ${t.title}`);
      lines.push(`  ${t.detail}`);
      if (t.link) lines.push(`  Link: ${t.link}`);
      lines.push('');
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'nestiq-report.txt';
    a.click();
    URL.revokeObjectURL(url);
  }

  useEffect(() => {
    const es = new EventSource(`${API}/api/orchestrate/${sessionId}`);
    es.addEventListener('start', e => {
      const d = JSON.parse(e.data);
      const map = {}; d.agents.forEach(a => map[a.id] = { ...a, status:'Waiting', progress: 0, done:false });
      setAgents(prev => ({ ...prev, ...map }));
    });
    es.addEventListener('agent_status', e => {
      const d = JSON.parse(e.data);
      setAgents(prev => ({...prev, [d.agent_id]: {...prev[d.agent_id], ...d, done:false}}));
    });
    es.addEventListener('agent_done', e => {
      const d = JSON.parse(e.data);
      setAgents(prev => ({...prev, [d.agent_id]: {...prev[d.agent_id], done:true, progress:100, status:'Complete'}}));
    });
    es.addEventListener('results', e => setResults(JSON.parse(e.data).results));
    es.addEventListener('complete', () => { setComplete(true); es.close(); });
    es.onerror = () => { setError('Agent stream disconnected. Refresh the page to retry.'); es.close(); };
    return () => es.close();
  }, [sessionId]);

  async function ask(e){
    e.preventDefault(); if(!chatInput.trim()) return;
    const q = chatInput; setChatInput('');
    setChat(c => [...c, {role:'user', text:q}]);
    const res = await fetch(`${API}/api/chat/${sessionId}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:q})});
    const data = await res.json();
    setChat(c => [...c, {role:'agent', text:data.answer}]);
  }

  return <main className="atlas">
    <aside className="left-rail">
      <div className="brand"><Home size={18}/> NestIQ</div>
      <a className="active">ATLAS</a><a>LISTINGS</a><a>CONCIERGE</a><a>TIMELINE</a>
    </aside>
    <section className="content">
      <div className="topline"><p className="label">AGENTIC RELOCATION ATLAS</p><h1>{results?.profile?.destination_city || 'Building'} move plan</h1></div>
      {error && <div className="error-banner">{error}</div>}
      <AgentRail agents={Object.values(agents)} complete={complete}/>
      {!results && <div className="working-state"><Compass className="spin-slow" size={36}/><p>Agents are building the atlas. No spinner, just work in motion.</p></div>}
      <AnimatePresence>{results && <motion.div initial={{opacity:0}} animate={{opacity:1}} className="dashboard">
        <ProfileStrip profile={results.profile}/>
        <ReportBar profile={results.profile} downloadReport={downloadReport} />
        <Neighborhoods neighborhoods={results.neighborhoods}/>
        <Listings listings={results.listings}/>
        <Checklist tasks={results.checklist}/>
        <Concierge chat={chat} chatInput={chatInput} setChatInput={setChatInput} ask={ask}/>
      </motion.div>}</AnimatePresence>
    </section>
  </main>
}

function AgentRail({agents, complete}){
  return <aside className="agent-rail">
    <p className="label">AGENT ACTIVITY</p>
    {agents.map(a => <div className="agent-row" key={a.id}>
      <div className="agent-head"><span>{a.name}</span>{a.done && <Check size={14}/>}</div>
      <div className="line"><motion.div animate={{width:`${a.progress || 0}%`}} /></div>
      <em>{a.status}</em>
    </div>)}
    {complete && <div className="complete-note"><Sparkles size={15}/> Atlas ready</div>}
  </aside>
}

function ProfileStrip({profile}){
  return <div className="profile-strip">
    <span><b>PROFILE</b> {profile.profile_type}</span><span><b>CITY</b> {profile.destination_city}</span><span><b>BUDGET</b> ${profile.monthly_budget}</span><span><b>WORK</b> {profile.work_style}</span><span><b>PETS</b> {profile.pets}</span>
  </div>
}

function ReportBar({profile, downloadReport}){
  return <div className="report-bar">
    <div><strong>Report ready for:</strong> {profile.profile_type} moving to {profile.destination_city} on {profile.move_timeline}</div>
    <button className="report-button" onClick={downloadReport}>Download report</button>
  </div>
}

function Neighborhoods({neighborhoods}){
  return <section className="section"><h2>Neighborhood fit</h2><div className="neighborhood-grid">
    {neighborhoods.map((n,i) => <motion.article initial={{opacity:0,y:15}} animate={{opacity:1,y:0}} transition={{delay:i*.08}} className="n-card" key={n.slug}>
      <Score score={n.score}/><div><h3>{n.name}</h3><p>{n.justification}</p><div className="mini"><b>Pros</b> {n.pros.join(' · ')}</div><div className="mini warn"><b>Watch out</b> {n.watchout}</div></div>
      <div className="vibe"><p>“{n.vibe}”</p><div>{n.tags.map(t => <span key={t}>{t}</span>)}</div></div>
    </motion.article>)}
  </div></section>
}

function Score({score}){
  const deg = Math.round(score * 3.6);
  return <div className="score" style={{background:`conic-gradient(var(--moss) ${deg}deg, var(--paper-deep) 0deg)`}}><div>{score}</div></div>
}

function Listings({listings}){
  return <section className="section"><h2>Apartment scout</h2><div className="listing-grid">{listings.map(l => <article className="listing" key={l.id}>
    <div className="fake-img">
      {l.image_url ? <img className="listing-img" src={l.image_url} alt={l.title} /> : <div className="image-preview"><Image size={42}/><p>No photo available</p></div>}
      {l.red_flags.length > 0 && <span className="red-flag">red flag</span>}
    </div>
    <div><h3>{l.title}</h3><p>{l.neighborhood} · Fit {l.fit_score}/100</p><p className="cost">${l.cost_breakdown.rent} + ${l.cost_breakdown.utilities} utilities + ${l.cost_breakdown.pet_fee} pet + $18 insurance = <b>${l.true_monthly_cost}</b></p>
    {l.red_flags.map(r => <div className="red" key={r}>{r}</div>)}<details><summary>Draft outreach email</summary><p>{l.outreach}</p></details></div>
  </article>)}</div></section>
}

function Checklist({tasks}){
  return <section className="section"><h2>Moving timeline</h2><div className="timeline">{tasks.map((t,i) => <div className="task" key={i}><span>{t.when}</span><h3>{t.title}</h3><p>{t.detail}</p>{t.link && <a href={t.link} target="_blank" rel="noreferrer">Action link</a>}</div>)}</div></section>
}

function Concierge({chat, chatInput, setChatInput, ask}){
  return <section className="section concierge"><h2>Concierge</h2><div className="letter-chat">{chat.map((m,i) => <p key={i} className={m.role}>{m.text}</p>)}</div><form onSubmit={ask} className="chat-input"><input value={chatInput} onChange={e=>setChatInput(e.target.value)} placeholder="Ask: Is Logan Square safe at night?"/><button><Send size={18}/></button></form></section>
}

createRoot(document.getElementById('root')).render(<App/>);
